from sqlalchemy import create_engine, text
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

def check_connection() -> bool:
    """Quick sanity check that we can actually reach Postgres."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1
