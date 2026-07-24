import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.reddit import fetch

def verify_reddit():
    print("Testing reddit scraper...")
    records = fetch(limit=3)
    print(f"Fetched {len(records)} records")
    for r in records:
        print(f"\n--- RECORD ---")
        print(f"URL: {r['source_url']}")
        print(f"Date: {r['review_date']}")
        print(f"Text snippet: {r['raw_text'][:100]}...")
        print(f"Metadata: {r['metadata']}")

if __name__ == '__main__':
    verify_reddit()
