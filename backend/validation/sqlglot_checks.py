import sqlglot
from sqlglot import exp
from dataclasses import dataclass, field
from backend.schema.introspect import get_schema_map

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list = field(default_factory=list)

def validate_sql_against_schema(sql: str) -> ValidationResult:
    """Parse the SQL into an AST and check that every table and column it
    references actually exists in the real, live schema -- before we ever
    run it against Postgres. This is what stops a hallucinated table/column
    name from reaching the database as a runtime error."""
    schema = get_schema_map()
    errors = []

    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[f"SQL failed to parse: {e}"])

    tables_used = {t.name.lower() for t in parsed.find_all(exp.Table)}
    unknown_tables = tables_used - set(schema.keys())
    if unknown_tables:
        errors.append(f"Unknown table(s): {', '.join(sorted(unknown_tables))}")

    known_tables = tables_used & set(schema.keys())
    all_known_columns = set()
    for t in known_tables:
        all_known_columns |= schema[t]

    # SELECT-clause aliases (e.g. SUM(p.amount) AS total_spent) are valid to
    # reference elsewhere in the query (ORDER BY, HAVING) per Postgres rules,
    # but they aren't real table columns. Without this, a query that legally
    # reuses its own alias gets misflagged as referencing an unknown column --
    # a false positive we hit in real testing (see README known limitations).
    select_aliases = {
        a.alias.lower() for a in parsed.find_all(exp.Alias) if a.alias
    }

    for col in parsed.find_all(exp.Column):
        col_name = col.name.lower()
        table_ref = col.table.lower() if col.table else None
        if col_name == "*":
            continue
        if not table_ref and col_name in select_aliases:
            continue
        if table_ref and table_ref in schema:
            if col_name not in schema[table_ref]:
                errors.append(f"Unknown column '{col_name}' on table '{table_ref}'")
        elif not table_ref:
            if col_name not in all_known_columns:
                errors.append(f"Unknown column '{col_name}' (no table specified)")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)
