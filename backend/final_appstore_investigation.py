"""
Final Apple App Store investigation.
Tests multiple App IDs and endpoint variants to determine if any reliable path exists.
"""
import requests
import json

session = requests.Session()
session.headers.update({
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
})

# Known Blinkit App IDs to try
APP_IDS = [
    "968384028",   # Previously identified as incorrect
    "1479554720",  # Blinkit (post-rebrand from Grofers)
    "1629383236",  # Another candidate
]

print("=== Apple App Store Investigation ===\n")

for app_id in APP_IDS:
    print(f"--- Testing App ID: {app_id} ---")

    # 1. RSS feed endpoint (the one we use)
    url = f"https://itunes.apple.com/in/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json"
    try:
        r = session.get(url, timeout=10)
        print(f"  RSS page 1: HTTP {r.status_code}")
        if r.status_code == 200:
            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])
            print(f"  Entries: {len(entries) if isinstance(entries, list) else 'N/A (dict=app meta only?)'}")
            if isinstance(entries, list) and len(entries) > 0:
                # Check if first entry is review or app metadata
                first = entries[0]
                if "im:rating" in first:
                    title = first.get("title", {}).get("label", "?")
                    rating = first.get("im:rating", {}).get("label", "?")
                    print(f"  First review: [{rating}*] {title[:60]}")
                else:
                    print(f"  First entry has no rating — probably app metadata only")
                    # Check if there's a second entry
                    if len(entries) > 1 and "im:rating" in entries[1]:
                        title = entries[1].get("title", {}).get("label", "?")
                        print(f"  Second entry (review): {title[:60]}")
        elif r.status_code == 400:
            print(f"  400 = likely invalid app ID or page out of range")
        else:
            print(f"  Body: {r.text[:200]}")
    except Exception as e:
        print(f"  RSS error: {e}")

    # 2. iTunes lookup to verify app exists
    lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country=in"
    try:
        r2 = session.get(lookup_url, timeout=10)
        if r2.status_code == 200:
            data = r2.json()
            results = data.get("results", [])
            if results:
                app = results[0]
                print(f"  iTunes lookup: '{app.get('trackName', '?')}' by {app.get('artistName', '?')}")
                print(f"  bundleId: {app.get('bundleId', '?')}")
                print(f"  userRatingCount: {app.get('userRatingCount', '?')}")
            else:
                print(f"  iTunes lookup: No results (invalid ID)")
    except Exception as e:
        print(f"  iTunes lookup error: {e}")

    print()

# 3. Try the new App Store Connect API approach (no auth needed for public reviews)
print("--- Alternative: App Store scrape via web URL ---")
web_url = "https://apps.apple.com/in/app/blinkit-grocery-in-minutes/id1479554720"
try:
    session2 = requests.Session()
    session2.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    r3 = session2.get(web_url, timeout=10)
    print(f"  Web page HTTP: {r3.status_code}")
    if r3.status_code == 200:
        content = r3.text
        if "customer-review" in content.lower() or "rating" in content.lower():
            print("  Reviews/ratings present in HTML")
        # Check for JSON-LD
        if "application/ld+json" in content:
            print("  JSON-LD schema found")
    else:
        print(f"  Body: {r3.text[:200]}")
except Exception as e:
    print(f"  Web error: {e}")

# 4. Try app-store-scraper library (if installed)
print()
print("--- Checking app-store-scraper library ---")
try:
    from app_store_scraper import AppStore
    print("  app-store-scraper: AVAILABLE")
    try:
        app = AppStore(country="in", app_name="blinkit", app_id="1479554720")
        app.review(how_many=5)
        print(f"  Reviews fetched: {len(app.reviews)}")
        if app.reviews:
            print(f"  Sample: {app.reviews[0].get('review','?')[:80]}")
    except Exception as e:
        print(f"  Fetch error: {e}")
except ImportError:
    print("  app-store-scraper: NOT installed")

print()
print("--- Checking itunes-app-scraper library ---")
try:
    import itunes_app_scraper
    print("  itunes-app-scraper: AVAILABLE")
except ImportError:
    print("  itunes-app-scraper: NOT installed")
