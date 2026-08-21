from backend.nl2sql.llm_client import generate_text
from backend.nl2sql.prompts import NAIVE_SQL_PROMPT
from backend.schema.introspect import get_full_schema_text
from backend.validation.safety import enforce_read_only, UnsafeSQLError
from backend.validation.sqlglot_checks import validate_sql_against_schema

def question_to_sql(question: str, max_retries: int = 1) -> dict:
    """Pipeline A: generate-then-validate.
    Dumps the full schema into the prompt, asks Gemini for SQL, then checks
    the result against the real schema and against read-only safety rules.
    If validation fails, retries once with the specific error fed back to
    the model. Returns a dict describing what happened, not just the SQL --
    so callers (and the eval harness) can see validation/retry outcomes."""
    schema = get_full_schema_text()
    prompt = NAIVE_SQL_PROMPT.format(schema=schema, question=question)

    attempts = []
    sql = generate_text(prompt)
    attempts.append(sql)

    for attempt_num in range(max_retries + 1):
        validation = validate_sql_against_schema(sql)
        safety_error = None
        try:
            enforce_read_only(sql)
        except UnsafeSQLError as e:
            safety_error = str(e)

        if validation.is_valid and not safety_error:
            return {
                "sql": sql,
                "is_valid": True,
                "attempts": attempts,
                "pipeline": "generate_then_validate",
            }

        if attempt_num == max_retries:
            return {
                "sql": sql,
                "is_valid": False,
                "errors": validation.errors + ([safety_error] if safety_error else []),
                "attempts": attempts,
                "pipeline": "generate_then_validate",
            }

        error_summary = "; ".join(validation.errors + ([safety_error] if safety_error else []))
        retry_prompt = prompt + f"\n\nYour previous answer was:\n{sql}\n\nThat query had this problem: {error_summary}\nPlease fix it and return only the corrected SQL."
        sql = generate_text(retry_prompt)
        attempts.append(sql)
