import requests
import time

session = requests.Session()
session.headers.update({'User-Agent': 'blinkit-discovery-engine:v1.0 (academic research)'})

PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"
ARCTIC_SHIFT_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

print("=== 1. Testing Pullpush.io ===")
try:
    params = {"subreddit": "india", "q": "Blinkit", "sort": "desc", "size": 5}
    r = session.get(PULLPUSH_URL, params=params, timeout=10)
    print(f"Pullpush HTTP: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        results = data.get('data', [])
        print(f"Results: {len(results)}")
        if results:
            print("Sample title: " + str(results[0].get('title', ''))[:100])
    else:
        print("Body: " + r.text[:300])
except Exception as e:
    print(f"Pullpush ERROR: {e}")

print()
print("=== 2. Testing Arctic Shift ===")
try:
    params = {"subreddit": "india", "q": "Blinkit", "limit": 5, "sort": "desc"}
    r = session.get(ARCTIC_SHIFT_URL, params=params, timeout=10)
    print(f"ArcticShift HTTP: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        results = data if isinstance(data, list) else data.get('data', [])
        print(f"Results: {len(results)}")
    else:
        print("Body: " + r.text[:300])
except Exception as e:
    print(f"ArcticShift ERROR: {e}")

print()
print("=== 3. Testing Reddit Official JSON (no auth) ===")
try:
    url = "https://www.reddit.com/r/india/search.json"
    params = {"q": "Blinkit", "sort": "new", "limit": 10, "restrict_sr": "on", "t": "all"}
    r = session.get(url, params=params, timeout=15)
    print(f"Reddit JSON HTTP: {r.status_code}")
    if r.status_code == 200:
        children = r.json().get('data', {}).get('children', [])
        print(f"Results: {len(children)}")
        if children:
            print("Sample title: " + str(children[0]['data'].get('title', ''))[:100])
    else:
        print("Body: " + r.text[:300])
except Exception as e:
    print(f"Reddit JSON ERROR: {e}")

print()
print("=== 4. Testing RedditSearch / Sublinks (alternative search) ===")
try:
    url = "https://www.reddit.com/search.json"
    params = {"q": "Blinkit site:reddit.com", "sort": "relevance", "limit": 10, "type": "link", "t": "all"}
    r = session.get(url, params=params, timeout=15)
    print(f"Reddit Global Search HTTP: {r.status_code}")
    if r.status_code == 200:
        children = r.json().get('data', {}).get('children', [])
        print(f"Results: {len(children)}")
    else:
        print("Body: " + r.text[:200])
except Exception as e:
    print(f"Global search ERROR: {e}")

print()
print("=== 5. Checking if PRAW is available ===")
try:
    import praw
    print("PRAW available: True")
except ImportError:
    print("PRAW NOT installed")
