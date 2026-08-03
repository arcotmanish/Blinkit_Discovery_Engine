"""
Time-boxed Apple App Store pagination investigation.
Goal: determine if pages 2+ can be unlocked for App ID 960335206 (Blinkit IN).

Tests:
  A. RSS feed - all pages 1-10, different sort orders
  B. App Store Connect API (no-auth public endpoint)
  C. iTunes Customer Reviews API (undocumented but historically stable)
  D. Different country markets (US/GB/AU for diaspora reviews)
  E. Different User-Agent strings
  F. app-store-scraper internals inspection
"""
import requests
import json
import time

APP_ID = "960335206"
BASE_TIMEOUT = 10

def make_session(ua=None):
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-IN,en;q=0.9",
        "User-Agent": ua or "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    })
    return s

# ── A. RSS feed all pages + sort orders ─────────────────────────────────────
print("=== A. RSS Feed Pagination (all pages, all sort orders) ===")
session = make_session()
for sort in ["mostrecent", "mosthelpful"]:
    print(f"\n  Sort: {sort}")
    for page in range(1, 11):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={APP_ID}/sortby={sort}/json"
        try:
            r = session.get(url, timeout=BASE_TIMEOUT)
            feed = r.json().get("feed", {}) if r.status_code == 200 else {}
            entries = feed.get("entry", [])
            if isinstance(entries, list):
                reviews = [e for e in entries if "im:rating" in e]
                status = f"{len(reviews)} reviews"
            elif isinstance(entries, dict):
                reviews = [entries] if "im:rating" in entries else []
                status = f"{len(reviews)} review (dict)"
            else:
                status = "0 (no entry key)"
                reviews = []
            print(f"    Page {page:2d}: HTTP {r.status_code} -> {status}")
            if not reviews and page > 1:
                print(f"           Pagination stops at page {page-1} for sort={sort}")
                break
        except Exception as e:
            print(f"    Page {page}: ERROR {e}")
            break
        time.sleep(0.3)

print()

# ── B. App Store Connect public endpoint (no auth) ───────────────────────────
print("=== B. App Store Connect API (public, no auth) ===")
# This endpoint exists for storefronts - used by App Store app internally
endpoints = [
    f"https://amp-api.apps.apple.com/v1/catalog/IN/apps/{APP_ID}/reviews?l=en-IN&offset=0&limit=20&platform=web&additionalPlatforms=appletv%2Cipad%2Ciphone%2Cmac",
    f"https://itunes.apple.com/WebObjects/MZStore.woa/wa/userReviewsRow?id={APP_ID}&displayable-kind=11&startIndex=0&endIndex=19&sort=4&appVersion=23.06.0",
]
session2 = make_session("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
session2.headers.update({
    "Origin": "https://apps.apple.com",
    "Referer": f"https://apps.apple.com/in/app/blinkit/id{APP_ID}",
    "X-Apple-Store-Front": "143467-1,29"  # India storefront code
})

for ep in endpoints:
    try:
        r = session2.get(ep, timeout=BASE_TIMEOUT)
        print(f"  {ep[:80]}...")
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response keys: {list(data.keys())[:5]}")
                reviews = data.get("data", []) or data.get("userReviewList", [])
                print(f"  Reviews found: {len(reviews)}")
            except Exception:
                print(f"  Body (non-JSON): {r.text[:200]}")
        else:
            print(f"  Body: {r.text[:200]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
    time.sleep(0.5)

# ── C. amp-api.apps.apple.com (used by App Store web) ──────────────────────
print("=== C. AMP API (App Store web internal API) ===")
# This is what apps.apple.com/in/app/* pages use to load reviews
for offset in [0, 20, 40]:
    amp_url = (
        f"https://amp-api.apps.apple.com/v1/catalog/IN/apps/{APP_ID}/reviews"
        f"?l=en-IN&offset={offset}&limit=20"
    )
    s3 = make_session()
    s3.headers.update({
        "Authorization": "Bearer ",  # Public token needed - will get 401 without
        "Origin": "https://apps.apple.com",
    })
    try:
        r = s3.get(amp_url, timeout=BASE_TIMEOUT)
        print(f"  offset={offset}: HTTP {r.status_code} -> {r.text[:200]}")
    except Exception as e:
        print(f"  offset={offset}: ERROR {e}")
    time.sleep(0.3)

print()

# ── D. Different countries ───────────────────────────────────────────────────
print("=== D. Alternative Country Markets (page 1 + page 2 test) ===")
countries = ["in", "us", "gb", "au", "sg", "ca"]
session4 = make_session()
total_across_countries = 0
for country in countries:
    country_total = 0
    for page in [1, 2]:
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={APP_ID}/sortby=mostrecent/json"
        try:
            r = session4.get(url, timeout=BASE_TIMEOUT)
            if r.status_code == 200:
                entries = r.json().get("feed", {}).get("entry", [])
                reviews = [e for e in entries if isinstance(entries, list) and "im:rating" in e]
                print(f"  [{country.upper()}] page {page}: {len(reviews)} reviews")
                country_total += len(reviews)
            else:
                print(f"  [{country.upper()}] page {page}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  [{country.upper()}] page {page}: ERROR {e}")
        time.sleep(0.4)
    total_across_countries += country_total
    print(f"  [{country.upper()}] subtotal: {country_total}")
    print()

print(f"  Total across all countries (pages 1-2): {total_across_countries}")

# ── E. app-store-scraper library internals ───────────────────────────────────
print()
print("=== E. app-store-scraper Library Internals ===")
try:
    from app_store_scraper import AppStore
    import inspect
    # Read the actual request it makes
    app = AppStore(country="in", app_name="blinkit", app_id=int(APP_ID))
    # Get the URL it builds
    src = inspect.getsource(app.review)
    print(f"  review() source snippet:")
    for line in src.split("\n")[:20]:
        print(f"    {line}")
except Exception as e:
    print(f"  Inspection error: {e}")

print()
print("=== SUMMARY ===")
print("Investigation complete. See results above.")
print(f"Multi-country total (pages 1-2): {total_across_countries} reviews")
