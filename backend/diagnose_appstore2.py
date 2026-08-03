import requests
from app_store_scraper import AppStore

print('=== Testing app-store-scraper library ===')
# app_store_scraper uses a different approach - it hits the web endpoint directly
try:
    app = AppStore(country='in', app_name='blinkit', app_id='968384028')
    app.review(how_many=10)
    print(f'Reviews fetched: {len(app.reviews)}')
    for r in app.reviews[:3]:
        print('---')
        print(str(r))
except Exception as e:
    print(f'Error with app_store_scraper (in): {e}')

print()
# Try finding the correct app ID via search
print('=== Searching for Blinkit in Apple App Store ===')
search_url = 'https://itunes.apple.com/search?term=blinkit&country=in&media=software&limit=5'
r = requests.get(search_url, timeout=10)
data = r.json()
print(f'Search HTTP: {r.status_code}')
for result in data.get('results', []):
    print(f"  App: {result.get('trackName')} | ID: {result.get('trackId')} | BundleID: {result.get('bundleId')}")
