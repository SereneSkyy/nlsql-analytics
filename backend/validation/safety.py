import sqlglot
from sqlglot import exp

class UnsafeSQLError(Exception):
    """Raised when generated SQL is anything other than a read-only SELECT."""
    pass

_ALLOWED_ROOT_TYPES = (exp.Select, exp.Union)
_FORBIDDEN_TYPES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.TruncateTable)

def enforce_read_only(sql: str) -> None:
    """Hard safety rail: only SELECT (or UNION of SELECTs) is ever allowed to
    reach the database. Raises UnsafeSQLError otherwise. This check is
    independent of schema validation -- it must pass no matter what."""
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        raise UnsafeSQLError(f"Could not parse SQL: {e}")

    if not isinstance(parsed, _ALLOWED_ROOT_TYPES):
        raise UnsafeSQLError(f"Only SELECT statements are allowed. Got: {type(parsed).__name__}")

    forbidden_found = list(parsed.find_all(*_FORBIDDEN_TYPES))
    if forbidden_found:
        raise UnsafeSQLError(f"Forbidden statement type found: {type(forbidden_found[0]).__name__}")
