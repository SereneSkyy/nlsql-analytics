from sqlalchemy import inspect
from backend.db import engine
import re

_PARTITION_PATTERN = re.compile(r"_p\d{4}_\d{2}$")
_EXCLUDED_TABLES = {"film_embedding"}

def get_full_schema_text() -> str:
    """Pull table and column info from Postgres, excluding physical partition
    tables (e.g. payment_p2023_05, implementation detail not meaningful to
    query directly) and tables outside this tool's scope (e.g. film_embedding,
    which belongs to a separate vector-similarity feature)."""
    inspector = inspect(engine)
    lines = []
    for table_name in inspector.get_table_names(schema="public"):
        if _PARTITION_PATTERN.search(table_name):
            continue
        if table_name in _EXCLUDED_TABLES:
            continue
        columns = inspector.get_columns(table_name, schema="public")
        col_descriptions = ", ".join(f"{col['name']} ({col['type']})" for col in columns)
        lines.append(f"Table: {table_name}\nColumns: {col_descriptions}\n")
    return "\n".join(lines)
