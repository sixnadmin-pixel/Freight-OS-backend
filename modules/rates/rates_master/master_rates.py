import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.rates.rates_master.api import IRatesMasterModule
from modules.rates.rates_master.rate_types import TarrifNew, TariffPatch, NACNew, NACPatch, ContractNew, ContractPatch


class RatesMasterModule(IRatesMasterModule):
    async def add_tariff_rate(self, payload: TarrifNew) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    data = payload.model_dump()
                    data["emp_id_sales"] = data.pop("salesperson")
                    await cur.execute(build_insert("tariff_rates", data, "tar_id"), data)
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

    async def patch_tariff_rate(self, tar_id: int, payload: TariffPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE tariff_rates SET {} WHERE tar_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("tar_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "tar_id": tar_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"Tariff rate {tar_id} not found")
        return row

    async def add_nac_rate(self, payload: NACNew) -> dict:
        data = payload.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("nac", data, "nac_id"), data)
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

    async def patch_nac_rate(self, nac_id: int, payload: NACPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE nac SET {} WHERE nac_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("nac_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "nac_id": nac_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"NAC rate {nac_id} not found")
        return row

    async def add_contracted_rate(self, payload: ContractNew) -> dict:
        contract = payload.model_dump(exclude={'client_ids'})
        client_ids = payload.client_ids

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('contracted_rates', contract), contract)
                    crate_id = (await cur.fetchone())['crate_id']

                    if client_ids:
                        await cur.executemany(
                            """INSERT INTO contracted_customer_group (crate_id, cli_id)
                               VALUES (%s, %s)""",
                            [(crate_id, c) for c in client_ids],
                        )
                    return {'crate_id': crate_id, 'client_ids': client_ids}

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

    async def patch_contracted_rate(self, crate_id: int, payload: ContractPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True, exclude={'client_ids'})
        clients = payload.client_ids

        if not changes and clients is None:
            raise HTTPException(400, "No fields or clients provided for update")

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    if changes:
                        set_clause = sql.SQL(", ").join(
                            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                            for col in changes
                        )
                        query = sql.SQL(
                            "UPDATE contracted_rates SET {} WHERE crate_id = {} RETURNING *"
                        ).format(set_clause, sql.Placeholder("crate_id"))
                        await cur.execute(query, {**changes, 'crate_id': crate_id})
                        row = await cur.fetchone()
                    else:
                        await cur.execute(
                            "SELECT * FROM contracted_rates WHERE crate_id = %s", (crate_id,)
                        )
                        row = await cur.fetchone()

                    if row is None:
                        raise HTTPException(404, f"Contracted rate {crate_id} not found")

                    if clients is not None:
                        await cur.execute(
                            "DELETE FROM contracted_customer_group WHERE crate_id = %(crate_id)s",
                            {'crate_id': crate_id},
                        )
                        if clients:
                            await cur.executemany(
                                """INSERT INTO contracted_customer_group (crate_id, cli_id)
                                   VALUES (%s, %s)""",
                                [(crate_id, c) for c in clients],
                            )
                        row['clients'] = clients

            return row

        except HTTPException:
            raise
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
