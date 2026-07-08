import os
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

load_dotenv()

POSTGRES_CONN_STR = os.getenv("POSTGRES_CONN_STR")

if not POSTGRES_CONN_STR:
    raise RuntimeError("POSTGRES_CONN_STR is not set in .env")

# Create a connection pool (min 1, max 10 connections)
try:
    pool = AsyncConnectionPool(
        conninfo=POSTGRES_CONN_STR,
        min_size=1,
        max_size=10,
        open=True,
    )
except Exception as e:
    print(f"[db_conn] Failed to connect to PostgreSQL: {e}")
    raise
