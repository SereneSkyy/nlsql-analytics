from sqlalchemy import inspect
from backend.db import engine
import re

_PARTITION_PATTERN = re.compile(r"_p\d{4}_\d{2}$")
_EXCLUDED_TABLES = {"film_embedding"}

def _relevant_table_names(inspector) -> list[str]:
    return [
        t for t in inspector.get_table_names(schema="public")
        if not _PARTITION_PATTERN.search(t) and t not in _EXCLUDED_TABLES
    ]

def get_schema_text_for_tables(table_names) -> str:
    """Render schema text for a specific set of tables only. Shared by both
    the full-schema and pruned-schema code paths."""
    inspector = inspect(engine)
    lines = []
    for table_name in sorted(table_names):
        columns = inspector.get_columns(table_name, schema="public")
        col_descriptions = ", ".join(f"{col['name']} ({col['type']})" for col in columns)
        lines.append(f"Table: {table_name}\nColumns: {col_descriptions}\n")
    return "\n".join(lines)

def get_full_schema_text() -> str:
    """Pull table and column info for every in-scope table (excludes
    partitions and film_embedding -- see _relevant_table_names)."""
    inspector = inspect(engine)
    return get_schema_text_for_tables(_relevant_table_names(inspector))

def get_schema_map() -> dict[str, set[str]]:
    """Same filtered table set as get_full_schema_text, but structured as
    {table_name: {column_names}} for programmatic validation."""
    inspector = inspect(engine)
    schema = {}
    for table_name in _relevant_table_names(inspector):
        columns = inspector.get_columns(table_name, schema="public")
        schema[table_name] = {col["name"].lower() for col in columns}
    return schema
