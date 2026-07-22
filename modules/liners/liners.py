import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.liners.api import ILinersModule
from modules.authen.api import IAuthnModule
from modules.liners.liner_types import LinerNew


class LinersModule(ILinersModule):
    def __init__(self, authentication: IAuthnModule):
        self.authn = authentication

    async def add_liner(self, payload: LinerNew) -> dict:
        self.authn.get_current_user()  # establishes caller identity for audit
        data = payload.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("liner", data, "lin_id"), data)
                    row = await cur.fetchone()
            return row

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation) as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "constraint_violation",
                    "constraint": e.diag.constraint_name,
                    "message": e.diag.message_primary,
                },
            ) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_all_liners(self) -> list[dict]:
        self.authn.get_current_user()  # establishes caller identity for audit

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM liner ORDER BY name")
                    return await cur.fetchall()

        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
