import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from utils.excel_processor import parse_tender_excel
from modules.inquiry.api import IInquiryModule
from modules.inquiry.activity_log.api import IAcitivityLog
from modules.authen.api import IAuthnModule
from modules.kyc.api import IKYCModule
from modules.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch, RfqBulkNew, RfqPreviewResult, RfqPreviewRow 


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



    async def create_rfq_bulk(self, payload: RfqBulkNew) -> dict:
        """
        One RFQ = one existing client + one contact + many origin-destination routes.
        Client and contact are created/resolved ONCE, then every line becomes its
        own inquiry. All of it in a single transaction.
        """
        emp_id = self.authen.get_current_user().emp_id

        if not payload.lines:
            raise HTTPException(422, "RFQ must contain at least one line")
        if payload.cp_id is None and payload.contact is None:
            raise HTTPException(422, "Provide either cp_id or contact")

        # Validate every line up front, before touching the database
        for li, line in enumerate(payload.lines):
            n_com = len(line.commodities)
            for ci, ctr in enumerate(line.containers):
                if ctr.commodity_index is not None and not (0 <= ctr.commodity_index < n_com):
                    raise HTTPException(
                        status_code=422,
                        detail=f"line[{li}].container[{ci}].commodity_index="
                               f"{ctr.commodity_index} is out of range (0..{n_com - 1})",
                    )

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:

                    await cur.execute("SELECT nextval('rfq_ref_seq') AS r")
                    rfq_ref = (await cur.fetchone())["r"]

                    # --- contact person: resolved ONCE for the whole RFQ ---
                    cp_id = payload.cp_id
                    if cp_id is None:
                        cp_data = {**payload.contact.model_dump(),
                                   "cli_id": payload.cli_id, "emp_id": emp_id}
                        await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                        cp_id = (await cur.fetchone())["cpid"]

                    # --- one inquiry per line ---
                    created: list[dict] = []
                    for line in payload.lines:
                        inq_data = {**line.inquiry.model_dump(),
                                    "cpid": cp_id, "cli_id": payload.cli_id, "emp_id": emp_id, "rfq_ref": rfq_ref}
                        await cur.execute(build_insert("inquiry", inq_data, "inq_id"), inq_data)
                        inq_id = (await cur.fetchone())["inq_id"]

                        com_ids: list[int] = []
                        for c in line.commodities:
                            com_data = {**c.model_dump(), "inq_id": inq_id}
                            await cur.execute(build_insert("commodity", com_data, "com_id"), com_data)
                            com_ids.append((await cur.fetchone())["com_id"])

                        cont_ids: list[int] = []
                        for ctr in line.containers:
                            data = ctr.model_dump()
                            idx = data.pop("commodity_index")
                            data["com_id"] = com_ids[idx] if idx is not None else None
                            ctr_data = {**data, "inq_id": inq_id}
                            await cur.execute(build_insert("container", ctr_data, "cont_id"), ctr_data)
                            cont_ids.append((await cur.fetchone())["cont_id"])

                        workflow_state = {"inq_id": inq_id, "flow_id": 1,
                                          "stage": "rate_check_in_progress"}
                        await cur.execute(
                            build_insert("workflow_stats", workflow_state, "inq_id"),
                            workflow_state,
                        )

                        created.append({"inq_id": inq_id,
                                        "com_ids": com_ids,
                                        "cont_ids": cont_ids})

            return {
                "rfq_ref": rfq_ref,
                "cli_id": payload.cli_id,
                "cpid": cp_id,
                "line_count": len(created),
                "inquiries": created,
            }

        except HTTPException:
            raise
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



    async def preview_rfq_excel(self, file_bytes: bytes) -> RfqPreviewResult:
        """Parse a tender spreadsheet and flag any port codes we don't recognise. Saves nothing."""
        try:
            parsed = parse_tender_excel(file_bytes)
        except Exception as e:
            raise HTTPException(422, {"error": "parse_failed", "message": str(e)})

        _CTRY_ALIAS = {
            "usa": "united states", "us": "united states", "u.s.a.": "united states",
            "uk": "united kingdom", "great britain": "united kingdom",
            "korea": "south korea", "quatar": "qatar",
            "netherland": "netherlands", "holland": "netherlands",
            "uae": "united arab emirates",
        }

        async def _resolve(cur, text: str, country: str) -> str:
            """UN/LOCODE for a code or a port name. '' when unresolved."""
            t = (text or "").strip()
            if not t:
                return ""

            # 1. already a code?
            if len(t) == 5:
                await cur.execute("SELECT unlocode FROM port WHERE unlocode = %s", (t.upper(),))
                if await cur.fetchone():
                    return t.upper()

            # 2. exact name, NO country filter
            await cur.execute(
                "SELECT unlocode, country FROM port WHERE lower(name) = lower(%s)", (t,)
            )
            hits = await cur.fetchall()
            if len(hits) == 1:
                return hits[0]["unlocode"]

            # 3. several matches — use country to break the tie
            ct = (country or "").strip().lower()
            ct = _CTRY_ALIAS.get(ct, ct)
            if hits and ct:
                narrowed = [h for h in hits if (h["country"] or "").lower() == ct]
                if len(narrowed) == 1:
                    return narrowed[0]["unlocode"]

            # 4. drop a trailing state/region — "Chicago, IL" -> "Chicago"
            if "," in t:
                base = t.split(",")[0].strip()
                if base and base != t:
                    return await _resolve(cur, base, country)

            return ""

        rows: list[RfqPreviewRow] = []
        if parsed["rows"]:
            try:
                async with pool.connection() as conn:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        for r in parsed["rows"]:
                            o_txt = r.get("origin", "")
                            d_txt = r.get("destination", "")
                            ctry  = r.get("country", "")
                            o_code = await _resolve(cur, o_txt, ctry)
                            d_code = await _resolve(cur, d_txt, ctry)
                            rows.append(RfqPreviewRow(
                                row=r.get("row", 0),
                                origin=o_txt, origin_code=o_code,
                                destination=d_txt, destination_code=d_code,
                                country=ctry,
                                known_port=(not o_txt or bool(o_code)) and (not d_txt or bool(d_code)),
                            ))
            except psycopg.OperationalError as e:
                raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        return RfqPreviewResult(
            destination=parsed["destination"],
            rows=rows,
            skipped=parsed["skipped"],
            unknown_count=sum(1 for r in rows if not r.known_port),
        )

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
                    i.rfq_ref,
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
                LEFT JOIN commodity cm  ON cm.inq_id = i.inq_id
                LEFT JOIN container cont ON cont.com_id = cm.com_id
                LEFT JOIN workflow_stats w ON w.inq_id= i.inq_id
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
                    i.rfq_ref,
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
                LEFT JOIN commodity cm  ON cm.inq_id = i.inq_id
                LEFT JOIN container cont ON cont.com_id = cm.com_id
                LEFT JOIN workflow_stats w ON w.inq_id = i.inq_id
                LEFT JOIN kyc_request kr ON kr.cli_id = cl.cli_id;
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
