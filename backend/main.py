from fastapi import FastAPI
from backend.db import check_connection

app = FastAPI(title="NL to SQL Analytics Tool")

@app.get("/health")
def health():
    db_ok = check_connection()
    return {"status": "ok" if db_ok else "db_unreachable", "database_connected": db_ok}
