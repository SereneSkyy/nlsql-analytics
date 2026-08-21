from fastapi import FastAPI
from pydantic import BaseModel
from backend.db import check_connection
from backend.nl2sql.generate_then_validate import question_to_sql
from backend.execution.runner import run_sql

app = FastAPI(title="NL-to-SQL Analytics Tool")

class AskRequest(BaseModel):
    question: str

@app.get("/health")
def health():
    db_ok = check_connection()
    return {"status": "ok" if db_ok else "db_unreachable", "database_connected": db_ok}

@app.post("/ask")
def ask(request: AskRequest):
    sql = question_to_sql(request.question)
    df = run_sql(sql)
    return {
        "question": request.question,
        "sql": sql,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }
