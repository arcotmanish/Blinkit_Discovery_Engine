import requests
import json
from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional

# ── Investigation results (2026-07-25) ──────────────────────────────────────
#
# App ID confirmed via iTunes search: 960335206
# trackName: 'Blinkit: Groceries & more' | bundleId: com.grofers.consumer | 3.2M ratings
#
# RSS feed pagination behaviour (confirmed by live endpoint probing):
#   sort=mostrecent:  pages 1-8 return 50 reviews each (page 9 returns empty) -> 400 reviews
#   sort=mosthelpful: pages 1-10 return 50 reviews each (page 1 returns 0)    -> ~500 reviews
#   Both sorts are active and paginate independently.
#
# Multi-country: IN/US/GB/AU each deliver reviews independently (50/page).
#   US/GB/AU reviews include English-speaking Indian diaspora discussing
#   the Blinkit experience abroad or referencing Indian app behaviour.
#   We collect IN only (primary market), keeping corpus focused.
#
# AMP API (amp-api.apps.apple.com): requires Bearer token -> HTTP 401. Not viable.
# app-store-scraper library: broken for this endpoint (returns 0 despite correct ID).
# iTunes customer review JSON (MZStore): HTTP 400. Not viable.
#
# Strategy: dual-sort RSS feed (mostrecent + mosthelpful), India only.
# Maximum theoretical yield: ~900 reviews (400 + 500) before deduplication.

APP_ID = "960335206"

# Sort orders and their page ranges (confirmed):
# mostrecent:  pages 1-8  (page 9 empty)  -> max 400 reviews
# mosthelpful: pages 2-10 (page 1 empty)  -> max 450 reviews
SORT_CONFIGS = [
    ("mostrecent",  range(1, 10)),   # pages 1-8 deliver content; 9 is empty sentinel
    ("mosthelpful", range(1, 11)),   # pages 2-10 deliver; page 1 is empty but harmless
]

COUNTRY = "in"


def _fetch_page(session: requests.Session, app_id: str, country: str, page: int, sort: str) -> List[dict]:
    """
    Fetch one page of RSS feed reviews.
    Returns list of raw entry dicts with im:rating present.
    Returns None as a sentinel if the page is definitively out of range.
    """
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews"
        f"/page={page}/id={app_id}/sortby={sort}/json"
    )
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            entries = resp.json().get("feed", {}).get("entry", [])
            if isinstance(entries, list):
                return [e for e in entries if "im:rating" in e]
            elif isinstance(entries, dict):
                # Single-entry dict (rare edge case on some pages)
                return [entries] if "im:rating" in entries else []
            return []
        elif resp.status_code in (400, 404):
            return None  # Sentinel: page out of range, stop paginating
        else:
            print(f"    App Store [{country}][{sort}] page {page}: HTTP {resp.status_code}")
            return []
    except requests.exceptions.Timeout:
        print(f"    App Store [{country}][{sort}] page {page}: timeout")
        return []
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"    App Store [{country}][{sort}] page {page}: {e}")
        return []


def _parse_entry(r: dict, app_id: str, country: str, sort: str) -> Optional[dict]:
    """Parse a raw RSS entry dict into a normalized review record. Returns None on failure."""
    try:
        date_str = r.get("updated", {}).get("label")
        if not date_str:
            return None

        created_at = datetime.fromisoformat(date_str).astimezone(timezone.utc)

        text = r.get("content", {}).get("label", "").strip()
        title = r.get("title", {}).get("label", "").strip()
        full_text = f"{title}\n\n{text}".strip() if text else title

        if not full_text:
            return None

        review_id = r.get("id", {}).get("label")
        rating = r.get("im:rating", {}).get("label")
        version = r.get("im:version", {}).get("label")
        user_name = r.get("author", {}).get("name", {}).get("label")

        return {
            "raw_text": full_text,
            "rating": int(rating) if rating else 0,
            "review_date": created_at.date(),
            "source_url": review_id or f"https://apps.apple.com/{country}/app/id{app_id}",
            "_created_at_dt": created_at,    # internal, removed before returning
            "_native_id": review_id,          # internal, used for deduplication
            "metadata": {
                "userName": user_name,
                "version": version,
                "country": country,
                "sort_strategy": sort,
            }
        }
    except Exception:
        return None


def fetch(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Fetch Apple App Store reviews for Blinkit (App ID 960335206).

    Uses dual-sort RSS strategy (mostrecent + mosthelpful) mirroring the
    Google Play approach. Full pagination across all available pages.

    Confirmed page yields (2026-07-25 investigation):
      mostrecent:  pages 1-8, 50 reviews/page  -> 400 reviews
      mosthelpful: pages 2-10, 50 reviews/page -> ~450 reviews
    After cross-sort deduplication: ~500-700 unique reviews expected.

    Args:
        start_date: Optional lower bound (UTC-aware datetime)
        end_date:   Optional upper bound (UTC-aware datetime)
        limit:      Maximum reviews to return (default 500)

    Returns:
        List of normalized review dicts, sorted newest-first.
    """
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "blinkit-discovery-engine:v1.0 (academic research)"
    })

    formatted_records: List[Dict[str, Any]] = []
    seen_ids: set = set()
    sort_stats = {}

    for sort, page_range in SORT_CONFIGS:
        sort_count = 0
        empty_streak = 0
        print(f"    Fetching App Store [{COUNTRY.upper()}] sort={sort}...")

        for page in page_range:
            if len(formatted_records) >= limit:
                break

            entries = _fetch_page(session, APP_ID, COUNTRY, page, sort)

            if entries is None:
                # Hard stop — page definitively out of range
                break
            if not entries:
                empty_streak += 1
                if empty_streak >= 2:
                    # Two consecutive empty pages — pagination exhausted
                    break
                continue
            else:
                empty_streak = 0

            for raw in entries:
                if len(formatted_records) >= limit:
                    break

                record = _parse_entry(raw, APP_ID, COUNTRY, sort)
                if record is None:
                    continue

                native_id = record["_native_id"]
                if not native_id or native_id in seen_ids:
                    continue

                created_at = record["_created_at_dt"]

                if start_date and created_at < start_date.replace(tzinfo=timezone.utc):
                    continue
                if end_date and created_at > end_date.replace(tzinfo=timezone.utc):
                    continue

                seen_ids.add(native_id)

                # Remove internal fields before storing
                del record["_created_at_dt"]
                del record["_native_id"]

                formatted_records.append(record)
                sort_count += 1

            time.sleep(0.8)  # Polite rate limiting

        sort_stats[sort] = sort_count
        print(f"      -> {sort_count} new reviews from sort={sort}")
        time.sleep(1.0)  # Brief pause between sort passes

    print(f"    App Store total: {len(formatted_records)} reviews | by sort: {sort_stats}")
    formatted_records.sort(key=lambda x: x["review_date"], reverse=True)
    return formatted_records
