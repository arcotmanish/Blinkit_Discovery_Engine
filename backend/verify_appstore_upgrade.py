"""
Quick verification of the upgraded Apple App Store scraper.
Fetches the first 2 pages of each sort to confirm pagination works,
then runs a full fetch with limit=100 to measure yield and deduplication.
"""
import sys
sys.path.insert(0, '.')

from scrapers.app_store import fetch, _fetch_page, APP_ID, COUNTRY, SORT_CONFIGS
import requests

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "blinkit-discovery-engine:v1.0 (academic research)"
})

print("=== 1. Pagination spot-check (first 2 pages per sort) ===")
for sort, page_range in SORT_CONFIGS:
    for page in list(page_range)[:2]:
        entries = _fetch_page(session, APP_ID, COUNTRY, page, sort)
        count = len(entries) if entries is not None else "SENTINEL (stop)"
        print(f"  sort={sort} page={page}: {count} reviews")

print()
print("=== 2. Full fetch with limit=150 ===")
records = fetch(limit=150)
print(f"Total returned: {len(records)}")
if records:
    print(f"Date range: {records[-1]['review_date']} -> {records[0]['review_date']}")
    from collections import Counter
    sorts = Counter(r.get("metadata", {}).get("sort_strategy", "?") for r in records)
    ratings = Counter(r.get("rating", 0) for r in records)
    print(f"Sort distribution: {dict(sorts)}")
    print(f"Rating distribution: {dict(sorted(ratings.items()))}")
    wcs = [len(r.get("raw_text", "").split()) for r in records]
    import statistics
    print(f"Word count: mean={statistics.mean(wcs):.1f} median={statistics.median(wcs):.1f} min={min(wcs)} max={max(wcs)}")
    print()
    print("Sample reviews (first 3):")
    for r in records[:3]:
        print(f"  [{r['rating']}*] [{r['review_date']}] [{r['metadata']['sort_strategy']}] {r['raw_text'][:100]}")
