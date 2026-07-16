import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.rates.rates.api import IRatesModule
from modules.rates.rates.rate_types import VesselByVesselRateNew, VesselByVesselRatePatch, FAKRatesNew, FAKRatesPatch, SpecialRateNew, SpecialRatePatch


class RatesModule(IRatesModule):
    async def add_vessel_rate(self, payload: VesselByVesselRateNew) -> dict:
        data = payload.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("vessel_by_vessel_rate", data, "srid"), data)
                    sr_id = (await cur.fetchone())['srid']
            return {'sr_id': sr_id}

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

    async def patch_vessel_rate(self, srid: int, payload: VesselByVesselRatePatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE vessel_by_vessel_rate SET {} WHERE srid = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("srid"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "srid": srid})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"Vessel rate {srid} not found")
        return row

    async def delete_vessel_rate(self, srid: int) -> dict:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "DELETE FROM vessel_by_vessel_rate WHERE srid = %s RETURNING srid", (srid,)
                )
                row = await cur.fetchone()

        if row is None:
            raise HTTPException(404, f"Vessel rate {srid} not found")
        return row

    async def add_fak_rate(self, payload: FAKRatesNew) -> dict:
        data = payload.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("fak_rates", data, "fak_id"), data)
                    fak_id = (await cur.fetchone())['fak_id']
            return {'fak_id': fak_id}

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

    async def patch_fak_rates(self, fak_id: int, payload: FAKRatesPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE fak_rates SET {} WHERE fak_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("fak_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "fak_id": fak_id})
                    row = await cur.fetchone()

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"FAK rate {fak_id} not found")
        return row

    async def delete_fak_rate(self, fak_id: int) -> dict:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "DELETE FROM fak_rates WHERE fak_id = %s RETURNING fak_id", (fak_id,)
                )
                row = await cur.fetchone()

        if row is None:
            raise HTTPException(404, f"FAK rate {fak_id} not found")
        return row

    async def add_special_rate(self, payload: SpecialRateNew) -> dict:
        data = payload.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("special_rate", data, "sprid"), data)
                    sprid = (await cur.fetchone())['sprid']
            return {'sprid': sprid}

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

    async def patch_special_rate(self, sprid: int, payload: SpecialRatePatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE special_rate SET {} WHERE sprid = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("sprid"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "sprid": sprid})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"Special rate {sprid} not found")
        return row

    async def delete_special_rate(self, sprid: int) -> dict:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "DELETE FROM special_rate WHERE sprid = %s RETURNING sprid", (sprid,)
                )
                row = await cur.fetchone()

        if row is None:
            raise HTTPException(404, f"Special rate {sprid} not found")
        return row
