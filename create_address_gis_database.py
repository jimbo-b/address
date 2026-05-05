from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

USERNAME = postgres
PASSWORD = password
HOST = localhost
PORT = 5432
DB_NAME = "address_gis"

POSTGRES_ADMIN_URL = "postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/postgres"

admin_engine = create_engine(POSTGRES_ADMIN_URL, isolation_level="AUTOCOMMIT")

with admin_engine.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
        {"db_name": DB_NAME},
    ).scalar()

    if not exists:
        conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
        print(f"Created database: {DB_NAME}")
    else:
        print(f"Database already exists: {DB_NAME}")

# Connect to the new/existing database
DB_URL = f"postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
db_engine = create_engine(DB_URL, isolation_level="AUTOCOMMIT")

with db_engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
    print("PostGIS extensions enabled")
