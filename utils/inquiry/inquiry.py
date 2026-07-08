import psycopg
from psycopg import sql
from psycopg.rows import tuple_row, dict_row
from fastapi import HTTPException

from data.dbconn import pool

from utils.inquiry.inquiry_types import  InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch


# case 1: new client, new contact person
# case 2: existing client, new contact person
# case 3: existing client, existing contact person

async def create_inquiry_case_1(
        payload: InquiryNewNew
)-> dict:
    
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
            async with conn.cursor(row_factory=tuple_row) as cur: 
                await cur.execute(
                    """
                    INSERT INTO client(name, kyc_completed) VALUES (%(name)s, %(kyc_completed)s) RETURNING cli_id
                    """,
                    cl
                )
                cli_id = (await cur.fetchone())[0]

                await cur.execute(
                    """
                    INSERT INTO contact_person(cli_id, emp_id, name, email, whatsapp, wechat)
                    VALUES (%(cli_id)s, %(emp_id)s, %(name)s, %(email)s, %(whatsapp)s, %(wechat)s)
                    RETURNING cpid
                    """,
                    {**cp, "cli_id": cli_id},
                )
                cp_id=(await cur.fetchone())[0]

                await cur.execute(
                    """INSERT INTO inquiry
                           (cpid, cli_id, emp_id, description, sbu, remark,
                            origin, incoterm, cargo_ready_date, priority,
                            preferred_liners, service_mode)
                       VALUES (%(cpid)s, %(cli_id)s, %(emp_id)s, %(description)s,
                               %(sbu)s, %(remark)s, %(origin)s, %(incoterm)s,
                               %(cargo_ready_date)s, %(priority)s,
                               %(preferred_liners)s, %(service_mode)s)
                       RETURNING inq_id""",
                    {**inq, "cpid": cp_id, "cli_id": cli_id},
                )
                inq_id = (await cur.fetchone())[0]

                com_ids: list[int] = []
                for c in payload.commodities:
                    await cur.execute(
                        """
                        INSERT INTO commodity(inq_id, name, com_type, description, weight, remark)
                        VALUES (%(inq_id)s, %(name)s, %(com_type)s, %(description)s, %(weight)s, %(remark)s)
                        RETURNING com_id
                        """,
                        {**c.model_dump(), "inq_id": inq_id},
                    )
                    com_ids.append((await cur.fetchone())[0])

                cont_ids: list[int] = []

                for ctr in payload.containers:
                    data= ctr.model_dump()
                    idx= data.pop("commodity_index")
                    data["com_id"] = com_ids[idx] if idx is not None else None

                    await cur.execute(
                        """
                        INSERT INTO container (inq_id, com_id, container_type, qty,
                                destination, zip_code, is_fully_loaded, free_time)
                        VALUES (%(inq_id)s, %(com_id)s, %(container_type)s,
                                   %(qty)s, %(destination)s, %(zip_code)s,
                                   %(is_fully_loaded)s, %(free_time)s)
                        RETURNING cont_id
                        """,
                        {**data, "inq_id": inq_id}
                    )

                    cont_ids.append((await cur.fetchone())[0])

        ret_vals={
            "inq_id": inq_id,
            "cli_id": cli_id,
            "cpid": cp_id,
            "com_ids": com_ids,
            "cont_ids": cont_ids,
        }

        print(ret_vals)

        return ret_vals

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

async def create_inquiry_case_2(
        payload: InquiryOldNew
)-> dict:
    
    cli_id=payload.cli_id
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
            async with conn.cursor(row_factory=tuple_row) as cur: 

                await cur.execute(
                    """
                    INSERT INTO contact_person(cli_id, emp_id, name, email, whatsapp, wechat)
                    VALUES (%(cli_id)s, %(emp_id)s, %(name)s, %(email)s, %(whatsapp)s, %(wechat)s)
                    RETURNING cpid
                    """,
                    {**cp, "cli_id": cli_id},
                )
                cp_id=(await cur.fetchone())[0]

                await cur.execute(
                    """INSERT INTO inquiry
                           (cpid, cli_id, emp_id, description, sbu, remark,
                            origin, incoterm, cargo_ready_date, priority,
                            preferred_liners, service_mode)
                       VALUES (%(cpid)s, %(cli_id)s, %(emp_id)s, %(description)s,
                               %(sbu)s, %(remark)s, %(origin)s, %(incoterm)s,
                               %(cargo_ready_date)s, %(priority)s,
                               %(preferred_liners)s, %(service_mode)s)
                       RETURNING inq_id""",
                    {**inq, "cpid": cp_id, "cli_id": cli_id},
                )
                inq_id = (await cur.fetchone())[0]

                com_ids: list[int] = []
                for c in payload.commodities:
                    await cur.execute(
                        """
                        INSERT INTO commodity(inq_id, name, com_type, description, weight, remark)
                        VALUES (%(inq_id)s, %(name)s, %(com_type)s, %(description)s, %(weight)s, %(remark)s)
                        RETURNING com_id
                        """,
                        {**c.model_dump(), "inq_id": inq_id},
                    )
                    com_ids.append((await cur.fetchone())[0])

                cont_ids: list[int] = []

                for ctr in payload.containers:
                    data= ctr.model_dump()
                    idx= data.pop("commodity_index")
                    data["com_id"] = com_ids[idx] if idx is not None else None

                    await cur.execute(
                        """
                        INSERT INTO container (inq_id, com_id, container_type, qty,
                                destination, zip_code, is_fully_loaded, free_time)
                        VALUES (%(inq_id)s, %(com_id)s, %(container_type)s,
                                   %(qty)s, %(destination)s, %(zip_code)s,
                                   %(is_fully_loaded)s, %(free_time)s)
                        RETURNING cont_id
                        """,
                        {**data, "inq_id": inq_id}
                    )

                    cont_ids.append((await cur.fetchone())[0])

        ret_vals={
            "inq_id": inq_id,
            "cli_id": cli_id,
            "cpid": cp_id,
            "com_ids": com_ids,
            "cont_ids": cont_ids,
        }

        print(ret_vals)

        return ret_vals

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

async def create_inquiry_case_3(
        payload: InquiryOldOld
)-> dict:
    
    cli_id=payload.cli_id
    cp_id=payload.cp_id
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
            async with conn.cursor(row_factory=tuple_row) as cur: 

                await cur.execute(
                    """INSERT INTO inquiry
                           (cpid, cli_id, emp_id, description, sbu, remark,
                            origin, incoterm, cargo_ready_date, priority,
                            preferred_liners, service_mode)
                       VALUES (%(cpid)s, %(cli_id)s, %(emp_id)s, %(description)s,
                               %(sbu)s, %(remark)s, %(origin)s, %(incoterm)s,
                               %(cargo_ready_date)s, %(priority)s,
                               %(preferred_liners)s, %(service_mode)s)
                       RETURNING inq_id""",
                    {**inq, "cpid": cp_id, "cli_id": cli_id},
                )
                inq_id = (await cur.fetchone())[0]

                com_ids: list[int] = []
                for c in payload.commodities:
                    await cur.execute(
                        """
                        INSERT INTO commodity(inq_id, name, com_type, description, weight, remark)
                        VALUES (%(inq_id)s, %(name)s, %(com_type)s, %(description)s, %(weight)s, %(remark)s)
                        RETURNING com_id
                        """,
                        {**c.model_dump(), "inq_id": inq_id},
                    )
                    com_ids.append((await cur.fetchone())[0])

                cont_ids: list[int] = []

                for ctr in payload.containers:
                    data= ctr.model_dump()
                    idx= data.pop("commodity_index")
                    data["com_id"] = com_ids[idx] if idx is not None else None

                    await cur.execute(
                        """
                        INSERT INTO container (inq_id, com_id, container_type, qty,
                                destination, zip_code, is_fully_loaded, free_time)
                        VALUES (%(inq_id)s, %(com_id)s, %(container_type)s,
                                   %(qty)s, %(destination)s, %(zip_code)s,
                                   %(is_fully_loaded)s, %(free_time)s)
                        RETURNING cont_id
                        """,
                        {**data, "inq_id": inq_id}
                    )

                    cont_ids.append((await cur.fetchone())[0])

        ret_vals={
            "inq_id": inq_id,
            "cli_id": cli_id,
            "cpid": cp_id,
            "com_ids": com_ids,
            "cont_ids": cont_ids,
        }

        print(ret_vals)

        return ret_vals

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
    
# PATCH an inquiry
async def patch_inquiry_fields(
        inq_id:int,
        payload:InquiryPatch
):
    changes= payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(400,'No fields provided for update...')

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
            psycopg.errors.CheckViolation) as e:
        raise HTTPException(422, {
            "constraint": e.diag.constraint_name,
            "message": e.diag.message_primary,
        }) from e

    if row is None:
        raise HTTPException(404, f"Inquiry {inq_id} not found")
    return row

async def patch_commodity_fields(
        inq_id:int,
        com_id:int,
        payload:CommodityPatch
):
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
            psycopg.errors.CheckViolation) as e:
        raise HTTPException(422, {
            "constraint": e.diag.constraint_name,
            "message": e.diag.message_primary,
        }) from e

    if row is None:
        raise HTTPException(404, f"Commodity {com_id} not found in inquiry {inq_id}")
    return row

async def patch_container_fields(
       inq_id:int,
       cont_id:int,
       payload:ContainerPatch
):
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
            psycopg.errors.CheckViolation) as e:
        raise HTTPException(422, {
            "constraint": e.diag.constraint_name,
            "message": e.diag.message_primary,
        }) from e

    if row is None:
        raise HTTPException(404, f"Container {cont_id} not found in inquiry {inq_id}")
    return row