import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import File, HTTPException, UploadFile

from data.dbconn import pool
from utils.helpers import build_insert
from modules.booking.api import IBookingModule
from modules.authen.api import IAuthnModule
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.inquiry.activity_log.activity_types import WorkflowStage, WorkflowStatusPatch
from modules.booking.booking_types import bookingRequestNew, bookingRequestPatch, bookingRequestReview, bookingRequestStatus


class BookingModule(IBookingModule):
    def __init__(self, authentication: IAuthnModule, activity_log: IAcitivityLog):
        self.authen = authentication
        self.activity_log = activity_log

    async def create_new_booking_req(self, emp_id_cs: int, payload: bookingRequestNew) -> dict:
        data = payload.model_dump()
        data['emp_id_cs'] = emp_id_cs

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('booking_request', data, 'booking_id'), data)
                    booking_id = (await cur.fetchone())['booking_id']


            await self.activity_log.update_workflow_status(
                payload.inq_id,
                WorkflowStatusPatch(stage=WorkflowStage.booking_request)
            )

            return {"booking_id": booking_id}

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.StringDataRightTruncation) as e:
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

    async def patch_booking_req(self, booking_id: int, updated_by: int, payload: bookingRequestPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        changes['updated_by'] = updated_by
        changes['booking_id'] = booking_id

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE booking_request SET {} WHERE booking_id={} RETURNING *"
        ).format(set_clause, sql.Placeholder("booking_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "booking_id":booking_id})
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
            raise HTTPException(404, f"Booking request not found for {booking_id}")
        return row

    async def review_booking_req(self, booking_id: int, payload: bookingRequestReview) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        reviewed_by= self.authen.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE booking_request SET {} WHERE booking_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("booking_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "booking_id": booking_id})
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
            raise HTTPException(404, f"Booking request not found for booking_id {booking_id}")
        return row

    async def confirm_booking_success(self, booking_id: int) -> dict:
        query = sql.SQL(
            "UPDATE booking_request SET status = {} WHERE booking_id = {} RETURNING *"
        ).format(
            sql.Placeholder("status"),
            sql.Placeholder("booking_id"),
        )

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {
                        "status": bookingRequestStatus.request_booking_success.value,
                        "booking_id": booking_id,
                    })
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
            raise HTTPException(404, f"Booking request not found for booking_id {booking_id}")

        await self.activity_log.update_workflow_status(
            row['inq_id'],
            WorkflowStatusPatch(stage=WorkflowStage.completed)
        )

        return row

    # async def record_cutoffs(self, booking_id: int, payload: cutoffSchedules, file: UploadFile = File(...)) -> dict:
    #     data = payload.model_dump(exclude_unset=True)
    #     data['booking_id'] = booking_id

    #     set_clause = sql.SQL(", ").join(
    #         sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
    #         for col in data if col != 'booking_id'
    #     )
    #     query = sql.SQL(
    #         "UPDATE cutoffs SET {} WHERE booking_id = {} RETURNING *"
    #     ).format(set_clause, sql.Placeholder("booking_id"))

    #     try:
    #         async with pool.connection() as conn:
    #             async with conn.cursor(row_factory=dict_row) as cur:
    #                 await cur.execute(query, data)
    #                 row = await cur.fetchone()
    #     except (psycopg.errors.ForeignKeyViolation,
    #                     psycopg.errors.CheckViolation,
    #                     psycopg.errors.NotNullViolation,
    #                     psycopg.errors.UniqueViolation,
    #                     psycopg.errors.StringDataRightTruncation) as e:
    #         raise HTTPException(422, {
    #                     "error": "constraint_violation",
    #                     "constraint": e.diag.constraint_name,
    #                     "message": e.diag.message_primary,
    #                 }) from e
    #     except psycopg.OperationalError as e:
    #         raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
        
    #     if row is None:
    #         raise HTTPException(404, f"Booking request not found for booking_id {booking_id}")
    #     return row
        


