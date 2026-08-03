import requests
import json

session = requests.Session()
session.headers.update({'User-Agent': 'blinkit-discovery-engine:v1.0 (academic research)'})

ARCTIC_SHIFT_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

print("=== 1. Test Arctic Shift with correct 'query' param ===")
params = {
    "subreddit": "india",
    "query": "Blinkit",
    "limit": 5,
    "sort": "desc",
    "fields": "id,title,selftext,created_utc,score,num_comments,author,subreddit"
}
r = session.get(ARCTIC_SHIFT_URL, params=params, timeout=15)
print(f"HTTP: {r.status_code}")
data = r.json()
results = data.get("data", [])
print(f"Results: {len(results)}")
for post in results[:3]:
    title = post.get("title", "")[:80]
    score = post.get("score", 0)
    comments = post.get("num_comments", 0)
    print(f"  Title: {title}")
    print(f"  Score: {score} | Comments: {comments}")

print()
print("=== 2. Test r/blinkit subreddit ===")
params2 = {
    "subreddit": "blinkit",
    "query": "delivery",
    "limit": 5,
    "sort": "desc",
    "fields": "id,title,created_utc,score"
}
r2 = session.get(ARCTIC_SHIFT_URL, params=params2, timeout=15)
print(f"r/blinkit query=delivery HTTP: {r2.status_code}")
data2 = r2.json()
results2 = data2.get("data", [])
print(f"Results: {len(results2)}")
for p in results2[:3]:
    print(f"  {p.get('title', '')[:80]}")

print()
print("=== 3. Test PullPush.io ===")
import time
PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"
params3 = {"subreddit": "india", "q": "Blinkit", "sort": "desc", "size": 5}
try:
    r3 = session.get(PULLPUSH_URL, params=params3, timeout=12)
    print(f"PullPush HTTP: {r3.status_code}")
    if r3.status_code == 200:
        data3 = r3.json()
        results3 = data3.get("data", [])
        print(f"Results: {len(results3)}")
        if results3:
            print(f"Sample title: {results3[0].get('title', '')[:80]}")
    else:
        print(f"Body: {r3.text[:300]}")
except Exception as e:
    print(f"PullPush ERROR: {e}")
