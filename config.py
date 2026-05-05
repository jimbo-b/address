from sqlalchemy import create_engine

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "password"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433
POSTGRES_ADMIN_DB = "postgres"
POSTGRES_CREATE_DB = "address_gis"

POSTGRES_ADMIN_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:"
    f"{POSTGRES_PASSWORD}@{POSTGRES_HOST}:"
    f"{POSTGRES_PORT}/{POSTGRES_ADMIN_DB}"
)

admin_engine = create_engine(POSTGRES_ADMIN_URL, isolation_level="AUTOCOMMIT")

CREATE_DB_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:"
    f"{POSTGRES_PASSWORD}@{POSTGRES_HOST}:"
    f"{POSTGRES_PORT}/{POSTGRES_CREATE_DB}"
)

create_db_engine = create_engine(POSTGRES_ADMIN_URL, isolation_level="AUTOCOMMIT")

db_engine = create_engine(POSTGRES_ADMIN_URL)
