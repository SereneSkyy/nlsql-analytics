from backend.nl2sql.llm_client import generate_text
from backend.nl2sql.prompts import NAIVE_SQL_PROMPT
from backend.schema.introspect import get_schema_text_for_tables
from backend.schema.context_builder import select_relevant_tables
from backend.validation.safety import enforce_read_only, UnsafeSQLError
from backend.validation.sqlglot_checks import validate_sql_against_schema

def question_to_sql(question: str, max_retries: int = 1) -> dict:
    """Pipeline B: constrain-then-generate.
    Prunes the schema down to only tables relevant to the question BEFORE
    calling the LLM, rather than validating after the fact. Still runs the
    same safety/schema validation as Pipeline A as a backstop -- pruning
    reduces the chance of errors, it doesn't replace checking for them."""
    relevant_tables = select_relevant_tables(question)
    schema = get_schema_text_for_tables(relevant_tables)
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
                "pipeline": "constrain_then_generate",
                "tables_used": sorted(relevant_tables),
            }

        if attempt_num == max_retries:
            return {
                "sql": sql,
                "is_valid": False,
                "errors": validation.errors + ([safety_error] if safety_error else []),
                "attempts": attempts,
                "pipeline": "constrain_then_generate",
                "tables_used": sorted(relevant_tables),
            }

        error_summary = "; ".join(validation.errors + ([safety_error] if safety_error else []))
        retry_prompt = prompt + f"\n\nYour previous answer was:\n{sql}\n\nThat query had this problem: {error_summary}\nPlease fix it and return only the corrected SQL."
        sql = generate_text(retry_prompt)
        attempts.append(sql)
