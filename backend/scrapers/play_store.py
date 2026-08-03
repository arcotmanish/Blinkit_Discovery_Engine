from google_play_scraper import Sort, reviews
from datetime import datetime
from typing import List, Dict, Any, Optional

APP_ID = "com.grofers.customerapp"

def fetch(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch Play Store reviews for Blinkit.
    Returns a list of normalized reviews using both MOST_RELEVANT and NEWEST sorts.
    """
    formatted_records = []
    seen_ids = set()
    
    # Prioritize MOST_RELEVANT (70%) and NEWEST (30%)
    sort_targets = [
        (Sort.MOST_RELEVANT, max(1, int(limit * 0.7))),
        (Sort.NEWEST, max(1, int(limit * 0.3)))
    ]
    
    for sort_type, target_limit in sort_targets:
        continuation_token = None
        fetched_for_sort = 0
        sort_str = "MOST_RELEVANT" if sort_type == Sort.MOST_RELEVANT else "NEWEST"
        
        while fetched_for_sort < target_limit:
            batch_size = min(200, target_limit - fetched_for_sort)
            try:
                result, continuation_token = reviews(
                    APP_ID,
                    lang='en',
                    country='in',
                    sort=sort_type,
                    count=batch_size,
                    continuation_token=continuation_token
                )
            except Exception as e:
                print(f"Error fetching Play Store ({sort_str}): {e}")
                break
                
            if not result:
                break
                
            for r in result:
                if r['reviewId'] in seen_ids:
                    continue
                seen_ids.add(r['reviewId'])
                
                created_at = r['at']
                
                # Apply date filters if provided
                if start_date and created_at < start_date:
                    continue
                if end_date and created_at > end_date:
                    continue
                    
                record = {
                    "raw_text": r['content'],
                    "rating": r['score'],
                    "review_date": created_at.date(),
                    "source_url": f"https://play.google.com/store/apps/details?id={APP_ID}&reviewId={r['reviewId']}",
                    "metadata": {
                        "userName": r.get('userName'),
                        "thumbsUpCount": r.get('thumbsUpCount'),
                        "reviewCreatedVersion": r.get('reviewCreatedVersion'),
                        "sort_strategy": sort_str
                    }
                }
                formatted_records.append(record)
                fetched_for_sort += 1
                
                if len(formatted_records) >= limit or fetched_for_sort >= target_limit:
                    break
                    
            if not continuation_token or len(formatted_records) >= limit:
                break
                
    return formatted_records
