import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

run_id = "4a58551b-b5fd-469e-803f-b8871cab3a42"

response = supabase.table("chunk_annotations").select("chunk_id", count="exact").eq("run_id", run_id).execute()
count = response.count
print(f"Total annotated chunks currently in database: {count}")
print(f"Remaining chunks out of 445 filtered chunks: {445 - count}")
