import requests
from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional

PULLPUSH_URLS = [
    "https://api.pullpush.io/reddit/search/submission/",
    "https://api.pullpush.io/reddit/search/comment/",
]
ARCTIC_SHIFT_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

DEFAULT_SUBREDDITS = [
    "india",
    "bangalore",
    "delhi",
    "mumbai",
    "blinkit",
    "zepto",
    "quickcommerce"
]

DEFAULT_SEARCH_TERMS = [
    "Blinkit",
    "blinkit"
]

USER_AGENT = "blinkit-discovery-engine:v1.0 (academic research)"

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    return session

def _pullpush_request(session: requests.Session, params: Dict[str, Any], max_retries: int = 4):
    for url in PULLPUSH_URLS[:1]:
        for attempt in range(max_retries):
            try:
                resp = session.get(url, params=params, timeout=(3, 10))
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        return data.get('data', []), url
                    return data, url
                elif resp.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"    [Pullpush] Rate-limited. Waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait)
                elif resp.status_code in (502, 503, 504):
                    wait = 5 * (2 ** attempt)
                    print(f"    [Pullpush] {resp.status_code} gateway error. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    [Pullpush] HTTP {resp.status_code} on attempt {attempt+1}. Skipping.")
                    break
            except requests.exceptions.Timeout:
                wait = 5 * (2 ** attempt)
                print(f"    [Pullpush] Timeout attempt {attempt+1}/{max_retries}. Retrying in {wait}s...")
                time.sleep(wait)
            except requests.exceptions.ConnectionError as e:
                print(f"    [Pullpush] Connection error: {e}. Attempt {attempt+1}/{max_retries}.")
                time.sleep(5)
            except Exception as e:
                print(f"    [Pullpush] Unexpected error: {e}")
                break
    return [], None

def _arctic_shift_request(session: requests.Session, subreddit: str, query: str, max_retries: int = 3):
    params = {
        "subreddit": subreddit,
        "q": query,
        "limit": 100,
        "sort": "desc",
        "fields": "id,title,selftext,created_utc,score,num_comments,author,subreddit"
    }
    for attempt in range(max_retries):
        try:
            resp = session.get(ARCTIC_SHIFT_URL, params=params, timeout=(3, 15))
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                return data.get('data', [])
            elif resp.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"    [ArcticShift] Rate-limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [ArcticShift] HTTP {resp.status_code} on attempt {attempt+1}.")
                time.sleep(5)
        except requests.exceptions.Timeout:
            wait = 10 * (2 ** attempt)
            print(f"    [ArcticShift] Timeout attempt {attempt+1}/{max_retries}. Retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"    [ArcticShift] Error: {e}")
            break
    return []

def _reddit_rss_fallback(session: requests.Session, subreddit: str, query: str, max_retries: int = 3):
    params = {
        "q": f"{query} subreddit:{subreddit}",
        "sort": "new",
        "type": "link",
        "limit": 100,
        "restrict_sr": "on",
        "t": "all"
    }
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    for attempt in range(max_retries):
        try:
            resp = session.get(url, params=params, timeout=(5, 20))
            if resp.status_code == 200:
                children = resp.json().get('data', {}).get('children', [])
                return [child.get('data', {}) for child in children]
            elif resp.status_code == 429:
                time.sleep(30)
            else:
                break
        except Exception as e:
            print(f"    [RedditJSON] Error: {e}")
            time.sleep(5)
    return []

def _normalize_submission(submission: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': submission.get('id'),
        'title': submission.get('title', ''),
        'selftext': submission.get('selftext', '') or submission.get('body', ''),
        'created_utc': submission.get('created_utc', 0),
        'score': submission.get('score', 0),
        'num_comments': submission.get('num_comments', 0),
        'author': submission.get('author', '[deleted]'),
        'subreddit': submission.get('subreddit', '')
    }

def fetch(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    formatted_records = []
    seen_ids = set()
    source_stats = {'pullpush': 0, 'arctic_shift': 0, 'reddit_json': 0}

    session = _make_session()

    for sub in DEFAULT_SUBREDDITS:
        for query in DEFAULT_SEARCH_TERMS:
            if len(formatted_records) >= limit:
                break
                
            print(f"  Fetching r/{sub} | query: '{query}'")
            params = {
                "subreddit": sub,
                "q": query,
                "sort": "desc",
                "size": min(100, limit - len(formatted_records))
            }

            raw_data, endpoint = _pullpush_request(session, params)

            if raw_data:
                source_stats['pullpush'] += len(raw_data)
                print(f"    [Pullpush] Got {len(raw_data)} results.")
            else:
                print(f"    [Pullpush] No results - trying Arctic Shift fallback...")
                raw_data = _arctic_shift_request(session, sub, query)
                if raw_data:
                    source_stats['arctic_shift'] += len(raw_data)
                    print(f"    [ArcticShift] Got {len(raw_data)} results.")
                else:
                    print(f"    [ArcticShift] No results - trying Reddit JSON fallback...")
                    raw_data = _reddit_rss_fallback(session, sub, query)
                    if raw_data:
                        source_stats['reddit_json'] += len(raw_data)
                        print(f"    [RedditJSON] Got {len(raw_data)} results.")

            for submission in raw_data:
                if len(formatted_records) >= limit:
                    break
                    
                s = _normalize_submission(submission)
                sub_id = s['id']
                if not sub_id or sub_id in seen_ids:
                    continue

                created_utc = s['created_utc']
                if isinstance(created_utc, str):
                    try:
                        created_utc = float(created_utc)
                    except (ValueError, TypeError):
                        created_utc = 0

                try:
                    created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                except (OSError, ValueError, OverflowError):
                    continue

                if start_date and created_at < start_date:
                    continue
                if end_date and created_at > end_date:
                    continue

                seen_ids.add(sub_id)

                text = s['selftext'].strip()
                title = s['title'].strip()

                if text in ('[removed]', '[deleted]'):
                    text = ''
                full_text = f"{title}\n\n{text}".strip() if text else title

                if not full_text:
                    continue

                record = {
                    "raw_text": full_text,
                    "rating": None,
                    "review_date": created_at.date(),
                    "source_url": f"https://reddit.com/r/{sub}/comments/{sub_id}",
                    "metadata": {
                        "subreddit": s['subreddit'] or sub,
                        "score": s['score'],
                        "num_comments": s['num_comments'],
                        "author": s['author'],
                        "created_utc": created_utc
                    }
                }
                formatted_records.append(record)

            time.sleep(1.0)
            
        if len(formatted_records) >= limit:
            break

    print(f"  Reddit source breakdown: {source_stats}")
    formatted_records.sort(key=lambda x: x['review_date'], reverse=True)
    return formatted_records
