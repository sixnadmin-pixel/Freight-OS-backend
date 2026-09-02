import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.booking.release_order.api import IReleaseOrderModule
from modules.authen.api import IAuthnModule
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.inquiry.activity_log.activity_types import WorkflowStage
from modules.booking.booking_types import bookingRequestStatus
from modules.booking.release_order.release_order_types import releaseOrderNew, releaseOrderPatch



class ReleaseOrderModule(IReleaseOrderModule):
    def __init__(self, authentication: IAuthnModule, activity_log: IAcitivityLog):
        self.authen = authentication
        self.activity_log= activity_log

    async def create_realease_order(self, payload: releaseOrderNew) -> dict:
        data = payload.model_dump()
        inq_id=payload.inq_id
        data['emp_id'] = self.authen.get_current_user().emp_id

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('release_order', data, '*'), data)
                    row = await cur.fetchone()

                    self.activity_log.update_workflow_status(inq_id, WorkflowStage.booking_confirmed)

            return row

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.StringDataRightTruncation) as e:
            raise HTTPException(422, {
                "error": "constraint_violation",
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def fetch_all_release_orders(self) -> dict:
        emp_id = self.authen.get_current_user().emp_id

        query = """
            SELECT r.*, w.stage FROM release_order r
            JOIN workflow_stats w ON w.inq_id = r.inq_id
            JOIN booking_request b ON r.inq_id = b.inq_id
            WHERE r.emp_id = %(emp_id)s
              AND w.stage = %(stage)s
              AND b.status = %(status)s
        """

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {
                        "emp_id": emp_id,
                        "stage": WorkflowStage.booking_request.value,
                        "status": bookingRequestStatus.request_booking_success.value,
                    })
                    rows = await cur.fetchall()
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        return rows

    async def patch_realease_order(self, ro_id: int, payload: releaseOrderPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        changes['updated_by'] = self.authen.get_current_user().emp_id

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE release_order SET {} WHERE ro_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("ro_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "ro_id": ro_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.StringDataRightTruncation) as e:
            raise HTTPException(422, {
                "error": "constraint_violation",
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Release order not found for ro_id {ro_id}")
        return row
