import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.rates.rates.api import IRatesModule
from modules.authen.api import IAuthnModule
from modules.rates.rates.rate_types import VesselByVesselRateNew, VesselByVesselRatePatch, FAKRatesNew, FAKRatesPatch, SpecialRateNew, SpecialRatePatch


class RatesModule(IRatesModule):
    def __init__(self, authentication: IAuthnModule):
        self.authn = authentication

    async def add_vessel_rate(self, payload: VesselByVesselRateNew) -> dict:
        data = payload.model_dump()
        emp_id = self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("vessel_by_vessel_rate", {**data, "emp_id":emp_id}, "srid"), {**data, "emp_id":emp_id})
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
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_vessel_rate(self, srid: int, payload: VesselByVesselRatePatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by = self.authn.get_current_user().emp_id

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
                    await cur.execute(query, {**changes, "srid": srid, "updated_by":updated_by})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Vessel rate {srid} not found")
        return row

    async def delete_vessel_rate(self, srid: int) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM vessel_by_vessel_rate WHERE srid = %s RETURNING srid", (srid,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Vessel rate {srid} not found")
        return row

    async def add_fak_rate(self, payload: FAKRatesNew) -> dict:
        data = payload.model_dump()
        emp_id = self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("fak_rates", {**data, "emp_id":emp_id}, "fak_id"), {**data, "emp_id":emp_id})
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
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_fak_rates(self, fak_id: int, payload: FAKRatesPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by = self.authn.get_current_user().emp_id

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
                    await cur.execute(query, {**changes, "fak_id": fak_id, "updated_by":updated_by})
                    row = await cur.fetchone()

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"FAK rate {fak_id} not found")
        return row

    async def delete_fak_rate(self, fak_id: int) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM fak_rates WHERE fak_id = %s RETURNING fak_id", (fak_id,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"FAK rate {fak_id} not found")
        return row

    async def add_special_rate(self, payload: SpecialRateNew) -> dict:
        data = payload.model_dump()
        emp_id = self.authn.get_current_user().emp_id
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("special_rate", {**data, "emp_id":emp_id}, "sprid"), {**data, "emp_id":emp_id})
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
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_special_rate(self, sprid: int, payload: SpecialRatePatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by= self.authn.get_current_user().emp_id

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
                    await cur.execute(query, {**changes, "sprid": sprid, "updated_by":updated_by})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Special rate {sprid} not found")
        return row

    async def delete_special_rate(self, sprid: int) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM special_rate WHERE sprid = %s RETURNING sprid", (sprid,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Special rate {sprid} not found")
        return row

    async def read_non_persistent_rate(self, rate_id: int, rate_type: str) -> dict:
        emp_id = self.authn.get_current_user().emp_id
        TABLE_MAP = {
            "vessel_by_vessel_rate": ("SELECT * FROM vessel_by_vessel_rate WHERE srid = %(rate_id)s",                          {"rate_id": rate_id}),
            "fak_rates":             ("SELECT * FROM fak_rates WHERE fak_id = %(rate_id)s",                                    {"rate_id": rate_id}),
            "special_rate":          ("SELECT * FROM special_rate WHERE sprid = %(rate_id)s AND emp_id = %(emp_id)s",          {"rate_id": rate_id, "emp_id": emp_id}),
        }
        if rate_type not in TABLE_MAP:
            raise HTTPException(400, f"Unknown rate_type '{rate_type}'. Valid values: {list(TABLE_MAP)}")

        query, params = TABLE_MAP[rate_type]
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, params)
                    row = await cur.fetchone()

        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"{rate_type} with id {rate_id} not found")
        return row
        
    async def read_all_fak_rates(self) -> list[dict]:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM fak_rates WHERE valid_to > NOW()")
                    return await cur.fetchall()

        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_all_vessel_rates(self) -> list[dict]:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM vessel_by_vessel_rate WHERE fcl_cutoff > NOW()")
                    return await cur.fetchall()

        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_all_special_rates(self) -> list[dict]:
        emp_id = self.authn.get_current_user().emp_id
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT * FROM special_rate WHERE valid_to > NOW() AND emp_id = %(emp_id)s",
                        {"emp_id": emp_id},
                    )
                    return await cur.fetchall()

        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
