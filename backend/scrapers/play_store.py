from google_play_scraper import Sort, reviews
from datetime import datetime
from typing import List, Dict, Any, Optional

APP_ID = "com.grofers.customerapp"

def fetch(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch Play Store reviews for Blinkit.
    Returns a list of normalized reviews.
    """
    result, _ = reviews(
        APP_ID,
        lang='en',
        country='in',
        sort=Sort.NEWEST,
        count=limit
    )
    
    formatted_records = []
    for r in result:
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
                "reviewCreatedVersion": r.get('reviewCreatedVersion')
            }
        }
        formatted_records.append(record)
        
        if len(formatted_records) >= limit:
            break
            
    return formatted_records
