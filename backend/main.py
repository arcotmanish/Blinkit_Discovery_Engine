from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Blinkit Discovery Engine API")

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "ok"})
