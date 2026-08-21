from backend.nl2sql.llm_client import generate_text
from backend.nl2sql.prompts import NAIVE_SQL_PROMPT
from backend.schema.introspect import get_full_schema_text

def question_to_sql(question: str) -> str:
    """Naive baseline: dump the full schema into the prompt, ask Gemini for SQL.
    No validation yet -- this is the Phase 2 baseline to measure improvement against."""
    schema = get_full_schema_text()
    prompt = NAIVE_SQL_PROMPT.format(schema=schema, question=question)
    sql = generate_text(prompt)
    return sql
