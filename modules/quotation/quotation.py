import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.quotation.api import IQuotationModule
from modules.authen.api import IAuthnModule
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.inquiry.activity_log.activity_types import WorkflowStage, WorkflowStatusPatch
from modules.quotation.quotation_type import QuotationNew, QuotationPatch, QuotationStatus


class QuotationModule(IQuotationModule):
    def __init__(self, authentication: IAuthnModule, activity_log: IAcitivityLog):
        self.authn = authentication
        self.activity_log = activity_log

    async def create_quotation(self, payload: QuotationNew) -> dict:
        data = payload.model_dump(exclude={'options'})
        options = payload.options
        emp_id = self.authn.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert("quotation", {**data, "emp_id": emp_id}, "quote_id"), {**data, "emp_id": emp_id})
                    quote_id = (await cur.fetchone())['quote_id']

                    if options:
                        for o in options:
                            o_data = {**o.model_dump(), "quote_id": quote_id}
                            await cur.execute(build_insert("quotation_option", o_data), o_data)

            return {'quote_id': quote_id}

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

    async def patch_quotation(self, quote_id: int, payload: QuotationPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True, exclude={'options'})
        options = payload.options if 'options' in payload.model_fields_set else None
        updated_by = self.authn.get_current_user().emp_id

        if not changes and options is None:
            raise HTTPException(400, "No fields provided for update...")

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT status FROM quotation WHERE quote_id = %s", (quote_id,)
                    )
                    existing = await cur.fetchone()
                    if existing is None:
                        raise HTTPException(404, f"Quotation {quote_id} not found")
                    if existing['status'] in (QuotationStatus.sent.value, QuotationStatus.accepted.value):
                        raise HTTPException(409, f"Cannot modify quotation with status '{existing['status']}'")

                    if changes:
                        set_clause = sql.SQL(", ").join(
                            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
                            for col in changes
                        )
                        query = sql.SQL(
                            "UPDATE quotation SET {} WHERE quote_id = {} RETURNING *"
                        ).format(set_clause, sql.Placeholder("quote_id"))
                        await cur.execute(query, {**changes, "quote_id": quote_id, "updated_by": updated_by})
                        row = await cur.fetchone()
                    else:
                        row = existing

                    if options is not None:
                        await cur.execute(
                            "DELETE FROM quotation_option WHERE quote_id = %s", (quote_id,)
                        )
                        for o in options:
                            o_data = {**o.model_dump(), "quote_id": quote_id}
                            await cur.execute(build_insert("quotation_option", o_data), o_data)

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

    async def delete_quotation(self, quote_id: int) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM quotation WHERE quote_id = %s RETURNING quote_id", (quote_id,)
                    )
                    row = await cur.fetchone()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Quotation {quote_id} not found")
        return row

    async def send_quotation(self, quote_id: int, payload: QuotationStatus) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "UPDATE quotation SET status = %(status)s WHERE quote_id = %(quote_id)s RETURNING *",
                        {"status": payload.value, "quote_id": quote_id}
                    )
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
            raise HTTPException(404, f"Quotation {quote_id} not found")

        await self.activity_log.update_workflow_status(
            row['inq_id'],
            WorkflowStatusPatch(stage=WorkflowStage.quotation_sent)
        )

        return row

    async def read_all_quotations(self) -> list[dict]:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("""
                        SELECT q.*, qo.option_id, qo.rate_id, qo.amt, qo.currency AS option_currency, qo.inq_id AS option_inq_id
                        FROM quotation q
                        LEFT JOIN quotation_option qo ON qo.quote_id = q.quote_id
                    """)
                    return await cur.fetchall()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def read_quotation(self, quote_id: int) -> list[dict]:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("""
                        SELECT q.*, qo.option_id, qo.rate_id, qo.amt, qo.currency AS option_currency, qo.inq_id AS option_inq_id
                        FROM quotation q
                        LEFT JOIN quotation_option qo ON qo.quote_id = q.quote_id
                        WHERE q.quote_id = %(quote_id)s
                    """, {"quote_id": quote_id})
                    rows = await cur.fetchall()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if not rows:
            raise HTTPException(404, f"Quotation {quote_id} not found")
        return rows

    async def record_response(self, quote_id: int, payload: QuotationStatus) -> dict:
        if payload not in (QuotationStatus.accepted, QuotationStatus.rejected):
            raise HTTPException(400, "Status must be 'accepted' or 'rejected'")

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    rate_id=payload.option
                    if payload.value == QuotationStatus.accepted:
                        await cur.execute(
                            """
                            SELECT EXISTS (
                                SELECT 1 
                                FROM quotation_option 
                                WHERE  rate_id= %(rate_id)s AND quote_id=%(quote_id)s
                            )
                            """,
                            {"rate_id": rate_id, "quote_id": quote_id}
                        )

                        exists = await cur.fetchone()["exists"]

                        if exists:
                            await cur.execute(
                                """UPDATE quotation SET status = %(status)s WHERE quote_id = %(quote_id)s RETURNING *""",
                                {"status": payload.value, "quote_id": quote_id}
                            )
                            row = await cur.fetchone()


                        else:
                            raise HTTPException(422, {
                                    "constraint": "OPTION ID VALIDATION FAILED",
                                    "message": "The option you selected does not exist",
                                })
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Quotation {quote_id} not found")

        await self.activity_log.update_workflow_status(
            row['inq_id'],
            WorkflowStatusPatch(stage=WorkflowStage.customer_response)
        )

        return row

