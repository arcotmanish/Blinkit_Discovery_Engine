import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.play_store import fetch

def verify_play_store():
    print("Testing Play Store scraper...")
    records = fetch(limit=3)
    print(f"Fetched {len(records)} records")
    for r in records:
        print(f"\n--- RECORD ---")
        print(f"URL: {r['source_url']}")
        print(f"Rating: {r['rating']}")
        print(f"Date: {r['review_date']}")
        print(f"Text snippet: {r['raw_text'][:100].encode('ascii', 'ignore').decode('ascii')}...")

if __name__ == '__main__':
    verify_play_store()
