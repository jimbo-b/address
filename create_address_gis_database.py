from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from config import admin_engine, create_db_engine, POSTGRES_CREATE_DB

with admin_engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
        {"db_name": POSTGRES_CREATE_DB},
    ).scalar()

    if not exists:
        conn.execute(text(f'CREATE DATABASE "{POSTGRES_CREATE_DB}"'))
        print(f"Created database: {POSTGRES_CREATE_DB}")
    else:
        print(f"Database already exists: {POSTGRES_CREATE_DB}")

# Connect to the new/existing database
with create_db_engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
    print("PostGIS extensions enabled")
