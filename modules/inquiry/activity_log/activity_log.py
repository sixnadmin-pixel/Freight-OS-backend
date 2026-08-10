import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.inquiry.activity_log.activity_types import WorkflowStage, WorkflowStatusNew, WorkflowStatusPatch


class ActivityLogModule(IAcitivityLog):

    async def create_workflow(self, payload: WorkflowStatusNew) -> dict:
        data = payload.model_dump()
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    data['stage'] = WorkflowStage.rate_check_in_progress

                    await cur.execute(build_insert("workflow_stats", data), data)
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

    async def update_workflow_status(self, inq_id: int, payload: WorkflowStatusPatch) -> dict:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(400, {"error": "no_fields", "message": "No fields provided for update"})

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    set_clause = sql.SQL(", ").join(
                        sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k))
                        for k in data
                    )
                    query = sql.SQL(
                        "UPDATE workflow_stats SET {set} WHERE inq_id = %(inq_id)s RETURNING *"
                    ).format(set=set_clause)
                    data["inq_id"] = inq_id
                    await cur.execute(query, data)
                    row = await cur.fetchone()

            if row is None:
                raise HTTPException(404, {"error": "not_found", "message": f"No workflow found for inquiry {inq_id}"})
            return row

        except HTTPException:
            raise
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
        
    async def get_inquiry_status(self, inq_id):
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        SELECT workflow_id, status FROM workflow_stats WHERE inq_id=%(inq_id)s
                        """,
                        inq_id
                    )
                    row = await cur.fetchone()
                    return row
                    
        except HTTPException:
            raise
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
               "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e
