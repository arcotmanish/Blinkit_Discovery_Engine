import requests
import json

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "blinkit-discovery-engine:v1.0 (academic research)"
})

APP_ID = "960335206"
COUNTRY = "in"

print(f"=== Testing correct Blinkit App ID: {APP_ID} ===")
print()

# Test pages 1-3 to confirm review delivery
for page in range(1, 4):
    url = f"https://itunes.apple.com/{COUNTRY}/rss/customerreviews/page={page}/id={APP_ID}/sortby=mostrecent/json"
    try:
        r = session.get(url, timeout=15)
        print(f"Page {page}: HTTP {r.status_code}")
        if r.status_code == 200:
            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])
            if isinstance(entries, list):
                # Filter out app metadata (first entry on page 1 has no im:rating)
                reviews = [e for e in entries if "im:rating" in e]
                print(f"  Entries: {len(entries)} total, {len(reviews)} with ratings (reviews)")
                if reviews:
                    sample = reviews[0]
                    title = sample.get("title", {}).get("label", "?")
                    rating = sample.get("im:rating", {}).get("label", "?")
                    content = sample.get("content", {}).get("label", "?")
                    wc = len(content.split())
                    print(f"  Sample [{rating}*] wc={wc}: {title[:60]}")
                    print(f"  Text: {content[:100]}")
            elif isinstance(entries, dict):
                print(f"  Entries is dict (single entry / app metadata only)")
        elif r.status_code == 400:
            print(f"  400 = page out of range, stopping")
            break
        else:
            print(f"  Unexpected: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

# Also test app-store-scraper with correct ID
print("=== app-store-scraper with correct ID ===")
try:
    from app_store_scraper import AppStore
    app = AppStore(country="in", app_name="blinkit-groceries-more", app_id=int(APP_ID))
    app.review(how_many=5)
    print(f"Reviews fetched: {len(app.reviews)}")
    if app.reviews:
        print(f"Sample: {str(app.reviews[0])[:200]}")
except Exception as e:
    print(f"app-store-scraper error: {e}")
