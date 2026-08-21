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
    result = question_to_sql(request.question)

    if not result["is_valid"]:
        return {
            "question": request.question,
            "sql": result["sql"],
            "is_valid": False,
            "errors": result.get("errors", []),
            "attempts": result["attempts"],
        }

    df = run_sql(result["sql"])
    return {
        "question": request.question,
        "sql": result["sql"],
        "is_valid": True,
        "attempts": result["attempts"],
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
    }
