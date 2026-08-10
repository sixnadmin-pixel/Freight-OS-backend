import os
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool

load_dotenv()

POSTGRES_CONN_STR = os.getenv("POSTGRES_CONN_STR")

if not POSTGRES_CONN_STR:
    raise RuntimeError("POSTGRES_CONN_STR is not set in .env")

# Create a connection pool (min 1, max 10 connections)
pool = AsyncConnectionPool(
    conninfo=POSTGRES_CONN_STR,
    min_size=1,
    max_size=10,
    open=False,
    check=AsyncConnectionPool.check_connection,
    max_idle=300,
)
