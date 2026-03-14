from pathlib import Path
from sqlalchemy import text
from app.core.database import engine

sql_file = Path(__file__).resolve().parent.parent / "sql" / "app_db_data.sql"

with engine.begin() as conn:
    with open(sql_file) as f:
        conn.execute(text(f.read()))