import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

run_id = "4a58551b-b5fd-469e-803f-b8871cab3a42"

print(f"Deleting failed annotations for run {run_id}...")
response = supabase.table("chunk_annotations").delete().eq("run_id", run_id).eq("annotation_failed", True).execute()
print(f"Deleted rows: {len(response.data) if response.data else 0}")
