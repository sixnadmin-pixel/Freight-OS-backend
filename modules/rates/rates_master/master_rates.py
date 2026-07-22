import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.rates.rates_master.api import IRatesMasterModule
from modules.authen.api import IAuthnModule
from modules.rates.rates_master.rate_types import TarrifNew, TariffPatch, NACNew, NACPatch, ContractNew, ContractPatch


class RatesMasterModule(IRatesMasterModule):
    def __init__(self, authentication:IAuthnModule):
        self.authn = authentication
        
    async def add_tariff_rate(self, payload: TarrifNew) -> dict:
        data = payload.model_dump()
        data["emp_id_sales"] = data.pop("salesperson")
        emp_id = self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("tariff_rates", {**data, "emp_id":emp_id}, "tar_id"), {**data, "emp_id":emp_id})
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

    async def patch_tariff_rate(self, tar_id: int, payload: TariffPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by= self.authn.get_current_user().emp_id

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
                    await cur.execute(query, {**changes, "tar_id": tar_id, "updated_by":updated_by})
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
            raise HTTPException(404, f"Tariff rate {tar_id} not found")
        return row

    async def add_nac_rate(self, payload: NACNew) -> dict:
        data = payload.model_dump()
        emp_id= self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("nac", {**data, "emp_id":emp_id}, "nac_id"), {**data, "emp_id":emp_id})
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

    async def patch_nac_rate(self, nac_id: int, payload: NACPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by = self.authn.get_current_user().emp_id

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
                    await cur.execute(query, {**changes, "nac_id": nac_id, "updated_by": updated_by})
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
            raise HTTPException(404, f"NAC rate {nac_id} not found")
        return row

    async def add_contracted_rate(self, payload: ContractNew) -> dict:
        contract = payload.model_dump(exclude={'client_ids'})
        client_ids = payload.client_ids
        emp_id= self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('contracted_rates', {**contract, "emp_id":emp_id}), {**contract, "emp_id":emp_id})
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
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_contracted_rate(self, crate_id: int, payload: ContractPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True, exclude={'client_ids'})
        clients = payload.client_ids
        updated_by= self.authn.get_current_user().emp_id

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
                        await cur.execute(query, {**changes, 'crate_id': crate_id, "updated_by":updated_by})
                        row = await cur.fetchone()

                        # TODO research here
                    # else:
                    #     await cur.execute(
                    #         "SELECT * FROM contracted_rates WHERE crate_id = %s", (crate_id,)
                    #     )
                    #     row = await cur.fetchone()

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
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_nac_rate(self, nac_id: int) -> dict:
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * FROM nac
            WHERE nac_id = %(nac_id)s
              AND (emp_id = %(emp_id)s OR emp_id_sales = %(emp_id)s OR emp_id_cs = %(emp_id)s)
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"nac_id": nac_id, "emp_id": emp_id})
                    row = await cur.fetchone()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"NAC rate {nac_id} not found")
        return row

    async def read_all_nac_rates(self) -> list[dict]:
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * FROM nac
            WHERE valid_to > NOW()
              AND (emp_id = %(emp_id)s OR emp_id_sales = %(emp_id)s OR emp_id_cs = %(emp_id)s)
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"emp_id": emp_id})
                    return await cur.fetchall()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
            
    async def read_client_nac_rates(self, cli_id):
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * FROM nac
            WHERE valid_to > NOW()
              AND (emp_id = %(emp_id)s OR emp_id_sales = %(emp_id)s OR emp_id_cs = %(emp_id)s)
              AND cli_id=%(cli_id)s
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"emp_id": emp_id, "cli_id":cli_id})
                    return await cur.fetchall()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
        
    async def read_contracted_rate(self, crate_id: int) -> dict:
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * FROM contracted_rates
            WHERE crate_id = %(crate_id)s
              AND (emp_id = %(emp_id)s OR emp_id_sales = %(emp_id)s OR emp_id_cs = %(emp_id)s)
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"crate_id": crate_id, "emp_id": emp_id})
                    row = await cur.fetchone()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Contracted rate {crate_id} not found")
        return row
    
    async def read_client_contracted_rates(self, cli_id):
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * 
            FROM contracted_rates cr
            JOIN contracted_customer_group cg ON cr.crate_id = cg.crate_id
            WHERE (cr.emp_id = %(emp_id)s OR cr.emp_id_sales = %(emp_id)s OR cr.emp_id_cs = %(emp_id)s)
            AND cg.cli_id = %(cli_id)s
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"emp_id": emp_id, "cli_id":cli_id})
                    return await cur.fetchall()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_all_contracted_rates(self) -> list[dict]:
        emp_id = self.authn.get_current_user().emp_id
        QUERY = """
            SELECT * FROM contracted_rates
            WHERE valid_to > NOW()
              AND (emp_id = %(emp_id)s OR emp_id_sales = %(emp_id)s OR emp_id_cs = %(emp_id)s)
            """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"emp_id": emp_id})
                    return await cur.fetchall()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_tariff_rate(self, tar_id: int) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT * FROM tariff_rates WHERE tar_id = %(tar_id)s",
                        {"tar_id": tar_id},
                    )
                    row = await cur.fetchone()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Tariff rate {tar_id} not found")
        return row

    async def read_all_tariff_rates(self) -> list[dict]:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT * FROM tariff_rates WHERE valid_to > NOW()")
                    return await cur.fetchall()
        except HTTPException:
            raise
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def delete_tariff_rate(self, tar_id: int) -> dict:
        emp_id=self.authn.get_current_user().emp_id  # establishes caller identity for audit
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM tariff_rates WHERE tar_id = %s RETURNING tar_id", (tar_id,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Tariff rate {tar_id} not found")
        return row

    async def delete_nac_rate(self, nac_id: int) -> dict:
        emp_id=self.authn.get_current_user().emp_id  # establishes caller identity for audit
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM nac WHERE nac_id = %s RETURNING nac_id", (nac_id,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"NAC rate {nac_id} not found")
        return row

    async def delete_contracted_rate(self, crate_id: int) -> dict:
        emp_id=self.authn.get_current_user().emp_id  # establishes caller identity for audit
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM contracted_rates WHERE crate_id = %s RETURNING crate_id", (crate_id,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Contracted rate {crate_id} not found")
        return row
    
    