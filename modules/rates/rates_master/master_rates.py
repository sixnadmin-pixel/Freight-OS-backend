import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.rates.rates_master.api import IRatesMasterModule
from modules.authen.api import IAuthnModule
from modules.rates.rate_types import TarrifNew, TariffPatch, NACNew, NACPatch, ContractNew, ContractPatch, SurchargeNew, SurchargePatch


class RatesMasterModule(IRatesMasterModule):
    def __init__(self, authentication:IAuthnModule):
        self.authn = authentication
        
    async def add_tariff_rate(self, payload: TarrifNew) -> dict:
        data = payload.model_dump(exclude={'surcharges'})
        data["emp_id_sales"] = data.pop("salesperson")
        surcharges = payload.surcharges
        emp_id = self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("tariff_rates", {**data, "emp_id":emp_id}, "tar_id"), {**data, "emp_id":emp_id})
                    row = await cur.fetchone()
                    tar_id = row["tar_id"]

                    if surcharges:
                        for s in surcharges:
                            s_data = {**s.model_dump(), "rate_id": tar_id}
                            await cur.execute(build_insert("surcharge", s_data), s_data)

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
        changes = payload.model_dump(exclude_unset=True, exclude={'surcharges'})
        surcharges = payload.surcharges if 'surcharges' in payload.model_fields_set else None
        updated_by= self.authn.get_current_user().emp_id

        if not changes and surcharges is None:
            raise HTTPException(400, "No fields provided for update...")

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    if changes:
                        set_clause = sql.SQL(", ").join(
                            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                            for col in changes
                        )
                        query = sql.SQL(
                            "UPDATE tariff_rates SET {} WHERE tar_id = {} RETURNING *"
                        ).format(set_clause, sql.Placeholder("tar_id"))
                        await cur.execute(query, {**changes, "tar_id": tar_id, "updated_by":updated_by})
                        row = await cur.fetchone()
                    else:
                        await cur.execute(
                            "SELECT * FROM tariff_rates WHERE tar_id = %s", (tar_id,)
                        )
                        row = await cur.fetchone()

                    if row is None:
                        raise HTTPException(404, f"Tariff rate {tar_id} not found")

                    if surcharges is not None:
                        for s in surcharges:
                            s_changes = s.model_dump(exclude_unset=True, exclude={'sur_id'})
                            if not s_changes:
                                continue
                            s_set = sql.SQL(", ").join(
                                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                                for col in s_changes
                            )
                            s_query = sql.SQL(
                                "UPDATE surcharge SET {} WHERE sur_id = {} RETURNING *"
                            ).format(s_set, sql.Placeholder("sur_id"))
                            await cur.execute(s_query, {**s_changes, "sur_id": s.sur_id})

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

    async def add_nac_rate(self, payload: NACNew) -> dict:
        data = payload.model_dump(exclude={'surcharges'})
        surcharges = payload.surcharges
        emp_id= self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("nac", {**data, "emp_id":emp_id}, "nac_id"), {**data, "emp_id":emp_id})
                    row = await cur.fetchone()
                    nac_id = row["nac_id"]

                    if surcharges:
                        for s in surcharges:
                            s_data = {**s.model_dump(), "rate_id": nac_id}
                            await cur.execute(build_insert("surcharge", s_data), s_data)

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
        changes = payload.model_dump(exclude_unset=True, exclude={'surcharges'})
        surcharges = payload.surcharges if 'surcharges' in payload.model_fields_set else None
        updated_by = self.authn.get_current_user().emp_id

        if not changes and surcharges is None:
            raise HTTPException(400, "No fields provided for update...")

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    if changes:
                        set_clause = sql.SQL(", ").join(
                            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                            for col in changes
                        )
                        query = sql.SQL(
                            "UPDATE nac SET {} WHERE nac_id = {} RETURNING *"
                        ).format(set_clause, sql.Placeholder("nac_id"))
                        await cur.execute(query, {**changes, "nac_id": nac_id, "updated_by": updated_by})
                        row = await cur.fetchone()
                    else:
                        await cur.execute(
                            "SELECT * FROM nac WHERE nac_id = %s", (nac_id,)
                        )
                        row = await cur.fetchone()

                    if row is None:
                        raise HTTPException(404, f"NAC rate {nac_id} not found")

                    if surcharges is not None:
                        for s in surcharges:
                            s_changes = s.model_dump(exclude_unset=True, exclude={'sur_id'})
                            if not s_changes:
                                continue
                            s_set = sql.SQL(", ").join(
                                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                                for col in s_changes
                            )
                            s_query = sql.SQL(
                                "UPDATE surcharge SET {} WHERE sur_id = {} RETURNING *"
                            ).format(s_set, sql.Placeholder("sur_id"))
                            await cur.execute(s_query, {**s_changes, "sur_id": s.sur_id})

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

    async def add_contracted_rate(self, payload: ContractNew) -> dict:
        contract = payload.model_dump(exclude={'client_ids', 'surcharges'})
        client_ids = payload.client_ids
        surcharges = payload.surcharges
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

                    if surcharges:
                        for s in surcharges:
                            s_data = {**s.model_dump(), "rate_id": crate_id}
                            await cur.execute(build_insert("surcharge", s_data), s_data)

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
        changes = payload.model_dump(exclude_unset=True, exclude={'client_ids', 'surcharges'})
        clients = payload.client_ids
        surcharges = payload.surcharges if 'surcharges' in payload.model_fields_set else None
        updated_by= self.authn.get_current_user().emp_id

        if not changes and clients is None and surcharges is None:
            raise HTTPException(400, "No fields, clients, or surcharges provided for update")

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

                    if surcharges is not None:
                        for s in surcharges:
                            s_changes = s.model_dump(exclude_unset=True, exclude={'sur_id'})
                            if not s_changes:
                                continue
                            s_set = sql.SQL(", ").join(
                                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                                for col in s_changes
                            )
                            s_query = sql.SQL(
                                "UPDATE surcharge SET {} WHERE sur_id = {} RETURNING *"
                            ).format(s_set, sql.Placeholder("sur_id"))
                            await cur.execute(s_query, {**s_changes, "sur_id": s.sur_id})

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
            SELECT n.*, s.sur_id, s.type AS surcharge_type, s.amt AS surcharge_amt, s.currency AS surcharge_currency
            FROM nac n
            LEFT JOIN surcharge s ON s.rate_id = n.nac_id
            WHERE n.valid_to > NOW()
              AND (n.emp_id = %(emp_id)s OR n.emp_id_sales = %(emp_id)s OR n.emp_id_cs = %(emp_id)s)
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
            SELECT cr.*, s.sur_id, s.type AS surcharge_type, s.amt AS surcharge_amt, s.currency AS surcharge_currency
            FROM contracted_rates cr
            LEFT JOIN surcharge s ON s.rate_id = cr.crate_id
            WHERE cr.valid_to > NOW()
              AND (cr.emp_id = %(emp_id)s OR cr.emp_id_sales = %(emp_id)s OR cr.emp_id_cs = %(emp_id)s)
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
                    await cur.execute("SELECT t.*, s.sur_id, s.type AS surcharge_type, s.amt AS surcharge_amt, s.currency AS surcharge_currency FROM tariff_rates t LEFT JOIN surcharge s ON s.rate_id = t.tar_id WHERE t.valid_to > NOW()")
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
    
    