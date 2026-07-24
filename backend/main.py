from fastapi import FastAPI
from fastapi.responses import JSONResponse
from db.client import supabase

app = FastAPI(title="Blinkit Discovery Engine API")

@app.get("/health")
async def health_check():
    status = {"status": "ok"}
    if supabase is not None:
        try:
            # simple ping query
            supabase.table("pipeline_runs").select("id").limit(1).execute()
            status["db"] = "connected"
        except Exception as e:
            status["db"] = "error"
            status["error"] = str(e)
    else:
        status["db"] = "not_configured"
    
    return JSONResponse(content=status)
