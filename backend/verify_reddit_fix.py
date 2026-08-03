"""
Reddit ingestion verification — tests the corrected scraper end-to-end.
Runs a small fetch (limit=10) to confirm Arctic Shift path works.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.reddit import fetch, _arctic_shift_request, _make_session

print("=== 1. Unit test: Arctic Shift with corrected 'query' param ===")
session = _make_session()
results = _arctic_shift_request(session, subreddit="india", query="Blinkit")
print(f"Arctic Shift returned {len(results)} posts")
if results:
    post = results[0]
    print(f"  Sample title: {post.get('title','')[:80]}")
    print(f"  Score: {post.get('score',0)} | Subreddit: {post.get('subreddit','')}")
else:
    print("  WARNING: No results returned — check connectivity")

print()
print("=== 2. Integration test: fetch() with limit=15 ===")
records = fetch(limit=15)
print(f"fetch() returned {len(records)} records")
if records:
    print("Sample records:")
    for rec in records[:3]:
        wc = len(rec.get('raw_text','').split())
        print(f"  [{rec.get('review_date')}] {rec.get('raw_text','')[:60]}... (wc={wc})")
    print()
    print("Metadata check (first record):")
    meta = records[0].get('metadata', {})
    print(f"  subreddit: {meta.get('subreddit')}")
    print(f"  score:     {meta.get('score')}")
    print(f"  query:     {meta.get('query')}")
else:
    print("  WARNING: No records returned")
