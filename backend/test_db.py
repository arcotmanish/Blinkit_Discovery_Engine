from db.client import supabase

def test_insert_and_query():
    print("Testing Supabase connection...")
    if not supabase:
        print("Supabase client not configured")
        return
    
    # 1. Insert a row
    try:
        run_data = {"mode": "demo", "status": "running"}
        res = supabase.table("pipeline_runs").insert(run_data).execute()
        print(f"Insert successful: {res.data}")
        
        inserted_id = res.data[0]['id']
        
        # 2. Query it back
        res2 = supabase.table("pipeline_runs").select("*").eq("id", inserted_id).execute()
        print(f"Query successful: {res2.data}")
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    test_insert_and_query()
