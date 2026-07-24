import requests
import json
from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional

# Apple's RSS feed returns at most 10 pages x 50 reviews = 500 per country.
APP_STORE_COUNTRIES = [
    'in',   # Blinkit primary market
]

APP_ID = "968384028"

def _fetch_country_page(session, app_id, country, page):
    """
    Fetch a single page of App Store reviews for a given country.
    Returns list of raw entry dicts, or [] on failure.
    """
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews"
        f"/page={page}/id={app_id}/sortby=mostrecent/json"
    )
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            entries = data.get('feed', {}).get('entry', [])
            if isinstance(entries, list):
                # First entry on page 1 is sometimes app metadata (has 'im:name' but no 'im:rating')
                return [e for e in entries if 'im:rating' in e]
            return []
        elif resp.status_code == 400:
            # 400 often means "page out of range" - stop pagination
            return None  # Sentinel: stop paginating
        else:
            print(f"    App Store [{country}] page {page}: HTTP {resp.status_code}")
            return []
    except requests.exceptions.Timeout:
        print(f"    App Store [{country}] page {page}: timeout.")
        return []
    except requests.RequestException as e:
        print(f"    App Store [{country}] page {page}: {e}")
        return []
    except (json.JSONDecodeError, KeyError):
        return []


def _parse_entry(r, app_id, country):
    """Parse a raw App Store review entry dict. Returns normalized record dict or None."""
    try:
        date_str = r.get('updated', {}).get('label')
        if not date_str:
            return None

        created_at = datetime.fromisoformat(date_str).astimezone(timezone.utc)

        text = r.get('content', {}).get('label', '').strip()
        title = r.get('title', {}).get('label', '').strip()
        full_text = f"{title}\n\n{text}".strip() if text else title

        if not full_text:
            return None

        review_id = r.get('id', {}).get('label')
        rating = r.get('im:rating', {}).get('label')
        version = r.get('im:version', {}).get('label')
        user_name = r.get('author', {}).get('name', {}).get('label')

        return {
            "raw_text": full_text,
            "rating": int(rating) if rating else 0,
            "review_date": created_at.date(),
            "source_url": review_id or f"https://apps.apple.com/{country}/app/id{app_id}",
            "created_at_dt": created_at, # internal use for filtering
            "source_native_id": review_id,
            "metadata": {
                "userName": user_name,
                "version": version,
                "country": country
            }
        }
    except Exception:
        return None


def fetch(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch reviews from the Apple App Store RSS feed using the Spotify-proven strategy.
    Returns a list of normalized reviews for Stage 1.
    """
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'blinkit-discovery-engine:v1.0 (academic research)'
    })

    formatted_records = []
    seen_ids = set()
    country_stats = {}
    max_pages = 10

    for country in APP_STORE_COUNTRIES:
        country_count = 0
        print(f"    Fetching App Store [{country.upper()}]...")

        for page in range(1, max_pages + 1):
            if len(formatted_records) >= limit:
                break
                
            entries = _fetch_country_page(session, APP_ID, country, page)

            if entries is None:
                break
            if not entries:
                break

            for r in entries:
                if len(formatted_records) >= limit:
                    break
                    
                record = _parse_entry(r, APP_ID, country)
                if record is None:
                    continue

                review_id = record['source_native_id']
                if not review_id or review_id in seen_ids:
                    continue

                created_at = record['created_at_dt']
                
                # Apply date filters
                if start_date and created_at < start_date.replace(tzinfo=timezone.utc):
                    continue
                if end_date and created_at > end_date.replace(tzinfo=timezone.utc):
                    continue

                seen_ids.add(review_id)
                
                # Cleanup internal fields
                del record['created_at_dt']
                del record['source_native_id']
                
                formatted_records.append(record)
                country_count += 1

            time.sleep(0.8)  # Polite rate limiting per page

        country_stats[country] = country_count
        print(f"      -> {country_count} new reviews from {country.upper()}")
        time.sleep(1.5)  # Extra pause between countries

    print(f"    App Store total by country: {country_stats}")
    formatted_records.sort(key=lambda x: x['review_date'], reverse=True)
    return formatted_records
