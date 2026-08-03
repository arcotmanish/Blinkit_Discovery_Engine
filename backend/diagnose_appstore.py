import requests
import json

app_id = '968384028'
session = requests.Session()
session.headers.update({'User-Agent': 'blinkit-discovery-engine:v1.0 (academic research)', 'Accept': 'application/json'})

print('=== Testing iTunes RSS Feed (pages 1-3, IN) ===')
for page in range(1, 4):
    url = f'https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json'
    r = session.get(url, timeout=15)
    data = r.json()
    entries = data.get('feed', {}).get('entry', [])
    print(f'Page {page}: HTTP {r.status_code}, entries={len(entries)}')
    if entries:
        # Show first entry keys
        print('  Sample entry keys:', list(entries[0].keys()))

print()
print('=== Testing mostHelpful sort ===')
url = f'https://itunes.apple.com/in/rss/customerreviews/page=1/id={app_id}/sortby=mosthelpful/json'
r = session.get(url, timeout=15)
data = r.json()
entries = data.get('feed', {}).get('entry', [])
print(f'mostHelpful page 1: HTTP {r.status_code}, entries={len(entries)}')

print()
print('=== Testing different country codes ===')
for country in ['us', 'gb', 'au', 'sg', 'ae']:
    url = f'https://itunes.apple.com/{country}/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json'
    try:
        r = session.get(url, timeout=10)
        data = r.json()
        entries = data.get('feed', {}).get('entry', [])
        print(f'  Country {country.upper()}: HTTP {r.status_code}, entries={len(entries)}')
    except Exception as e:
        print(f'  Country {country.upper()}: ERROR {e}')

print()
print('=== App Lookup to verify App ID and ratings ===')
lookup = requests.get(f'https://itunes.apple.com/lookup?id={app_id}&country=in', timeout=10)
print(f'Lookup HTTP: {lookup.status_code}')
ldata = lookup.json()
results = ldata.get('results', [])
if results:
    app = results[0]
    print('App name: ' + str(app.get('trackName')))
    print('App ID: ' + str(app.get('trackId')))
    print('Bundle ID: ' + str(app.get('bundleId')))
    print('Rating Count: ' + str(app.get('userRatingCount')))
    print('Current Version Rating Count: ' + str(app.get('userRatingCountForCurrentVersion')))
else:
    print('No results found for App ID ' + app_id + ' in India storefront.')

print()
print('=== Testing app-store-scraper package if available ===')
try:
    import app_store_scraper
    print('app_store_scraper available: True')
except ImportError:
    print('app_store_scraper NOT installed')

try:
    import itunes
    print('itunes package available: True')
except ImportError:
    print('itunes package NOT installed')
