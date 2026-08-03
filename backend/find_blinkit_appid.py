import requests
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})

r = s.get("https://itunes.apple.com/search?term=blinkit&country=in&entity=software&limit=5", timeout=10)
print("Search HTTP:", r.status_code)
if r.status_code == 200:
    data = r.json()
    for app in data.get("results", []):
        print("  trackName:", app.get("trackName"))
        print("  bundleId:", app.get("bundleId"))
        print("  trackId:", app.get("trackId"))
        print("  ratings:", app.get("userRatingCount"))
        print("  ratingValue:", app.get("averageUserRating"))
        print()
