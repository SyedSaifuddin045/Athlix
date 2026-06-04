from pathlib import Path
from sqlalchemy import text
from app.core.database import engine

sql_file = Path(__file__).resolve().parent.parent / "sql" / "app_db_data.sql"

with engine.begin() as conn:
    with open(sql_file) as f:
        raw_sql = f.read()
    for stmt in raw_sql.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        if stmt.lstrip().upper().startswith("INSERT"):
            stmt += ' ON CONFLICT ("id") DO NOTHING'
        conn.execute(text(stmt + ";"))