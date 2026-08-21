import pandas as pd
from sqlalchemy import text
from backend.db import engine

def run_sql(sql: str) -> pd.DataFrame:
    """Execute a SQL string against Postgres and return results as a DataFrame."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()
    return pd.DataFrame(rows, columns=columns)
