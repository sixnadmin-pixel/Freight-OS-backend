import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.inquiry.api import IInquiryModule
from modules.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch


# case 1: new client, new contact person
# case 2: existing client, new contact person
# case 3: existing client, existing contact person

class InquiryModule(IInquiryModule):
    async def create_inquiry_case_1(self, payload: InquiryNewNew) -> dict:
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
                    await cur.execute(build_insert("client", cli_data, "cli_id"), cli_data)
                    cli_id = (await cur.fetchone())["cli_id"]

                    cp_data = {**cp, "cli_id": cli_id}
                    await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                    cp_id = (await cur.fetchone())["cpid"]

                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id}
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

            return {
                "inq_id": inq_id,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "constraint_violation",
                    "constraint": e.diag.constraint_name,
                    "message": e.diag.message_primary,
                },
            ) from e

    async def create_inquiry_case_2(self, payload: InquiryOldNew) -> dict:
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
                    cp_data = {**cp, "cli_id": cli_id}
                    await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                    cp_id = (await cur.fetchone())["cpid"]

                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id}
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

            return {
                "inq_id": inq_id,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "constraint_violation",
                    "constraint": e.diag.constraint_name,
                    "message": e.diag.message_primary,
                },
            ) from e

    async def create_inquiry_case_3(self, payload: InquiryOldOld) -> dict:
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
                    inq_data = {**inq, "cpid": cp_id, "cli_id": cli_id}
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

            return {
                "inq_id": inq_id,
                "cli_id": cli_id,
                "cpid": cp_id,
                "com_ids": com_ids,
                "cont_ids": cont_ids,
            }

        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.NotNullViolation,
                psycopg.errors.UniqueViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "constraint_violation",
                    "constraint": e.diag.constraint_name,
                    "message": e.diag.message_primary,
                },
            ) from e

    async def patch_inquiry_fields(self, inq_id: int, payload: InquiryPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)

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
                    await cur.execute(query, {**changes, "inq_id": inq_id})
                    row = await cur.fetchone()
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e

        if row is None:
            raise HTTPException(404, f"Inquiry {inq_id} not found")
        return row

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

        if row is None:
            raise HTTPException(404, f"Commodity {com_id} not found in inquiry {inq_id}")
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

        if row is None:
            raise HTTPException(404, f"Container {cont_id} not found in inquiry {inq_id}")
        return row
