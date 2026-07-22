"""
One-time script to seed the port table from ports.json.
Format: { "UNLOCODE": "Port Name/Country Name", ... }
"""

import json
import os
import sys
from dotenv import load_dotenv
import psycopg

load_dotenv()

PORTS_JSON = r"C:\Users\tharu\Downloads\ports.json"
CONN_STR = os.getenv("POSTGRES_CONN_STR")

if not CONN_STR:
    sys.exit("POSTGRES_CONN_STR is not set in .env")


def parse_ports(path: str) -> list[tuple[str, str, str]]:
    with open(path, encoding="utf-8") as f:
        data: dict[str, str] = json.load(f)

    rows = []
    for unlocode, value in data.items():
        # value is "Port Name/Country" — split on last "/" to handle names with slashes
        parts = value.rsplit("/", 1)
        name = parts[0].strip()
        country = parts[1].strip() if len(parts) == 2 else ""
        rows.append((unlocode.strip(), name, country))
    return rows


def seed():
    rows = parse_ports(PORTS_JSON)
    print(f"Parsed {len(rows)} ports. Inserting...")

    with psycopg.connect(CONN_STR) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO port (unlocode, name, country)
                VALUES (%s, %s, %s)
                ON CONFLICT (unlocode) DO NOTHING
                """,
                rows,
            )
        conn.commit()

    print(f"Done. {len(rows)} rows processed (duplicates skipped).")


if __name__ == "__main__":
    seed()
