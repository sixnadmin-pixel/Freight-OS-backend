import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.inquiry.api import IInquiryModule
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.authen.api import IAuthnModule
from modules.kyc.api import IKYCModule
from modules.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch


# case 1: new client, new contact person
# case 2: existing client, new contact person
# case 3: existing client, existing contact person

class InquiryModule(IInquiryModule):
    def __init__(self, authentication: IAuthnModule, activity_log: IAcitivityLog, kyc: IKYCModule):
        self.authen=authentication
        self.activity_log=activity_log
        self.kyc=kyc

    async def create_inquiry_case_1(self, payload: InquiryNewNew) -> dict:
        emp_id= self.authen.get_current_user().emp_id
        cl = payload.client.model_dump()
        cp = payload.contact.model_dump()
        inq = payload.inquiry.model_dump()

        n_com = len(payload.commodities)
        for i, ctr in enumerate(payload.containers):
            if ctr.commodity_index is not None and not (0 <= ctr.commodity_index < n_com):
                raise HTTPException(
                    status_code=422,
                    detail=f"container[{i}].commodity_index={ctr.commodity_index} "
                           f"is out of range (0..{n_com - 1})",
                )

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    cli_data = cl
                    await cur.execute(build_insert("client", {**cli_data,'emp_id':emp_id}, "cli_id"), {**cli_data,'emp_id':emp_id})
                    cli_id = (await cur.fetchone())["cli_id"]

                    cp_data = {**cp, "cli_id": cli_id, "emp_id":emp_id}
                    await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                    cp_id = (await cur.fetchone())["cpid"]

                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id, "emp_id":emp_id}
                    await cur.execute(build_insert("inquiry", inq_data, "inq_id"), inq_data)
                    inq_id = (await cur.fetchone())["inq_id"]

                    com_ids: list[int] = []
                    for c in payload.commodities:
                        com_data = {**c.model_dump(), "inq_id": inq_id}
                        await cur.execute(build_insert("commodity", com_data, "com_id"), com_data)
                        com_ids.append((await cur.fetchone())["com_id"])

                    cont_ids: list[int] = []
                    for ctr in payload.containers:
                        data = ctr.model_dump()
                        idx = data.pop("commodity_index")
                        data["com_id"] = com_ids[idx] if idx is not None else None
                        ctr_data = {**data, "inq_id": inq_id}
                        await cur.execute(build_insert("container", ctr_data, "cont_id"), ctr_data)
                        cont_ids.append((await cur.fetchone())["cont_id"])

                    workflow_state={'inq_id':inq_id, 'flow_id':1, 'stage':'rate_check_in_progress'}

                    await cur.execute(build_insert('workflow_stats',workflow_state, 'inq_id'), workflow_state)
                    inq_id_log=(await cur.fetchone())["inq_id"]

            await self.kyc.create_kyc_stage(cli_id)

            return {
                "inq_id": inq_id,
                "logged_inq_id": inq_id_log,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn,
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

    async def create_inquiry_case_2(self, payload: InquiryOldNew) -> dict:
        emp_id= self.authen.get_current_user().emp_id
        cli_id = payload.cli_id
        cp = payload.contact.model_dump()
        inq = payload.inquiry.model_dump()

        n_com = len(payload.commodities)
        for i, ctr in enumerate(payload.containers):
            if ctr.commodity_index is not None and not (0 <= ctr.commodity_index < n_com):
                raise HTTPException(
                    status_code=422,
                    detail=f"container[{i}].commodity_index={ctr.commodity_index} "
                           f"is out of range (0..{n_com - 1})",
                )

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    cp_data = {**cp, "cli_id": cli_id, "emp_id":emp_id}
                    await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                    cp_id = (await cur.fetchone())["cpid"]

                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id, "emp_id":emp_id}
                    await cur.execute(build_insert("inquiry", inq_data, "inq_id"), inq_data)
                    inq_id = (await cur.fetchone())["inq_id"]

                    com_ids: list[int] = []
                    for c in payload.commodities:
                        com_data = {**c.model_dump(), "inq_id": inq_id}
                        await cur.execute(build_insert("commodity", com_data, "com_id"), com_data)
                        com_ids.append((await cur.fetchone())["com_id"])

                    cont_ids: list[int] = []
                    for ctr in payload.containers:
                        data = ctr.model_dump()
                        idx = data.pop("commodity_index")
                        data["com_id"] = com_ids[idx] if idx is not None else None
                        ctr_data = {**data, "inq_id": inq_id}
                        await cur.execute(build_insert("container", ctr_data, "cont_id"), ctr_data)
                        cont_ids.append((await cur.fetchone())["cont_id"])


                    workflow_state={'inq_id':inq_id, 'flow_id':1, 'stage':'rate_check_in_progress'}
                    
                    await cur.execute(build_insert('workflow_stats',workflow_state, 'inq_id'), workflow_state)
                    inq_id_log=(await cur.fetchone())["inq_id"]

            return {
                "inq_id": inq_id,
                "logged_inq_id": inq_id_log,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn,
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

    async def create_inquiry_case_3(self, payload: InquiryOldOld) -> dict:
        emp_id= self.authen.get_current_user().emp_id
        cli_id = payload.cli_id
        cp_id = payload.cp_id
        inq = payload.inquiry.model_dump()

        n_com = len(payload.commodities)
        for i, ctr in enumerate(payload.containers):
            if ctr.commodity_index is not None and not (0 <= ctr.commodity_index < n_com):
                raise HTTPException(
                    status_code=422,
                    detail=f"container[{i}].commodity_index={ctr.commodity_index} "
                           f"is out of range (0..{n_com - 1})",
                )

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id, "emp_id":emp_id}
                    await cur.execute(build_insert("inquiry", inq_data, "inq_id"), inq_data)
                    inq_id = (await cur.fetchone())["inq_id"]

                    com_ids: list[int] = []
                    for c in payload.commodities:
                        com_data = {**c.model_dump(), "inq_id": inq_id}
                        await cur.execute(build_insert("commodity", com_data, "com_id"), com_data)
                        com_ids.append((await cur.fetchone())["com_id"])

                    cont_ids: list[int] = []
                    for ctr in payload.containers:
                        data = ctr.model_dump()
                        idx = data.pop("commodity_index")
                        data["com_id"] = com_ids[idx] if idx is not None else None
                        ctr_data = {**data, "inq_id": inq_id}
                        await cur.execute(build_insert("container", ctr_data, "cont_id"), ctr_data)
                        cont_ids.append((await cur.fetchone())["cont_id"])

                    workflow_state={'inq_id':inq_id, 'flow_id':1, 'stage':'rate_check_in_progress'}
                                        
                    await cur.execute(build_insert('workflow_stats',workflow_state, 'inq_id'), workflow_state)
                    inq_id_log=(await cur.fetchone())["inq_id"]

            return {
                "inq_id": inq_id,
                "logged_inq_id": inq_id_log,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn,
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

    async def patch_inquiry_fields(self, inq_id: int, payload: InquiryPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by=self.authen.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE inquiry SET {} WHERE inq_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("inq_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "inq_id": inq_id, "updated_by":updated_by})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Inquiry {inq_id} not found")
        return row

    async def read_inquiry(self, inq_id):
        QUERY="""
                SELECT
                    i.cli_id,
                    i.inq_id,
                    w.stage AS workflow_stage,
                    cl.name,
                    cl.kyc_completed,
                    i.sbu,
                    i.origin,
                    i.incoterm,
                    i.priority,
                    i.service_mode,
                    i.cargo_ready_date,
                    i.preferred_liners,
                    i.preferred_rate,

                    cm.com_id,
                    cm.name          AS commodity_name,
                    cm.com_type          AS commodity_type,
                    cm.hs_code,
                    cm.weight        AS commodity_weight,
                    cont.cont_id,
                    cont.container_type,
                    cont.temperature,
                    cont.qty,
                    cont.destination,
                    cont.zip_code,
                    cont.address,
                    cont.is_fully_loaded,
                    cont.free_time
                FROM inquiry i
                JOIN client cl ON cl.cli_id = i.cli_id
                JOIN commodity cm  ON cm.inq_id = i.inq_id
                JOIN container cont ON cont.com_id = cm.com_id
                JOIN workflow_stats w ON w.inq_id= i.inq_id
                WHERE i.inq_id = %(inq_id)s
              """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("SELECT 1 FROM inquiry WHERE inq_id = %s", (inq_id,))
                    if await cur.fetchone() is None:
                        raise HTTPException(404, f"Inquiry {inq_id} not found")
                    await cur.execute(QUERY, {"inq_id": inq_id})
                    return await cur.fetchall()
                
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

    async def read_all_inquiry(self):
        QUERY="""
                SELECT
                    i.cli_id,
                    i.inq_id,
                    w.stage AS workflow_stage,
                    cl.name,
                    cl.kyc_completed,
                    kr.kyc_stage,
                    i.preferred_rate,
                    i.sbu,
                    i.origin,
                    i.incoterm,
                    i.priority,
                    i.service_mode,
                    i.cargo_ready_date,
                    i.preferred_liners,
                   cm.com_id,
                    cm.name          AS commodity_name,
                    cm.com_type          AS commodity_type,
                    cm.hs_code,
                    cm.weight        AS commodity_weight,
                    cont.cont_id,
                    cont.container_type,
                    cont.temperature,
                    cont.qty,
                    cont.destination,
                    cont.zip_code,
                    cont.address,
                    cont.is_fully_loaded,
                    cont.free_time
                FROM inquiry i
                JOIN client cl ON cl.cli_id = i.cli_id
                JOIN commodity cm  ON cm.inq_id = i.inq_id
                JOIN container cont ON cont.com_id = cm.com_id
                JOIN workflow_stats w ON w.inq_id= i.inq_id
                JOIN kyc_request kr ON kr.cli_id = cl.cli_id;
              """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY)
                    return await cur.fetchall()
                
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
    
    async def patch_commodity_fields(self, inq_id: int, com_id: int, payload: CommodityPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE commodity SET {} WHERE com_id = {} AND inq_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("com_id"), sql.Placeholder("inq_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "com_id": com_id, "inq_id": inq_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Commodity {com_id} not found in inquiry {inq_id}")
        return row

    async def delete_inquiry(self, inq_id: int) -> dict:
        emp_id = self.authen.get_current_user().emp_id
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "DELETE FROM inquiry WHERE inq_id = %s AND emp_id = %s RETURNING inq_id",
                        (inq_id, emp_id)
                    )
                    row = await cur.fetchone()
        except psycopg.errors.ForeignKeyViolation as e:
            raise HTTPException(409, {
                "error": "constraint_violation",
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Inquiry {inq_id} not found")
        return row

    async def patch_container_fields(self, inq_id: int, cont_id: int, payload: ContainerPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, "No fields provided for update...")

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE container SET {} WHERE cont_id = {} AND inq_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("cont_id"), sql.Placeholder("inq_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "cont_id": cont_id, "inq_id": inq_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Container {cont_id} not found in inquiry {inq_id}")
        return row
