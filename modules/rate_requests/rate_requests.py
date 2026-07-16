import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.rate_requests.api import IRateRequestModule
from modules.rate_requests.rate_request_types import RateRequestNew, RateRequestOptionNew, RateRequestOptionPatch

class RateRequestModule(IRateRequestModule):
    async def add_rate_request(
            self,
            payload: RateRequestNew
    )->dict:
        request_data=payload.model_dump()

        try:

            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:

                    await cur.execute(build_insert('rate_request', request_data, "request_id"), request_data)
                    request_id=(await cur.fetchone())['request_id']

                    return {"request_id":request_id}
                
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
        
    async def delete_rate_request(
            self,
            request_id: int
    )->dict:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "DELETE FROM rate_request WHERE request_id = %s RETURNING request_id", (request_id,)
                )
                row = await cur.fetchone()

        if row is None:
            raise HTTPException(404, f"Rate request {request_id} not found")
        return row

    async def add_request_option(
            self,
            request_id: int,
            payload: RateRequestOptionNew
    )->dict:
        data = payload.model_dump()
        data['request_id'] = request_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('rate_request_option', data, 'option_id'), data)
                    option_id=(await cur.fetchone())['option_id']

                    return {'option_id':option_id}
                
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
        
    async def delete_rate_request_option(
            self,
            request_id: int,
            option_id: int
    )->dict:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    DELETE FROM rate_request_option
                    WHERE request_id=%(request_id)s AND option_id=%(option_id)s
                    RETURNING option_id
                    """,
                    {'request_id': request_id, 'option_id': option_id}
                )
                row = await cur.fetchone()

        if row is None:
            raise HTTPException(404, f"Option {option_id} not found for request {request_id}")
        return row
        
    async def patch_rate_request_option(
            self,
            option_id: int,
            request_id: int,
            payload: RateRequestOptionPatch
    )->dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE rate_request_option SET {} WHERE option_id = {} AND request_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("option_id"), sql.Placeholder("request_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "option_id": option_id, "request_id": request_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"Option {option_id} not found for request {request_id}")
        return row
