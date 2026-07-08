import psycopg
from psycopg import sql
from psycopg.rows import tuple_row, dict_row
from fastapi import HTTPException

from data.dbconn import pool

from utils.client.client_types import ClientNew, ClientPatch, ContactPatch

# Add a new client with a new contact person

async def create_new_client(
        payload:ClientNew
)->dict:
    
    client_data=payload.model_dump(exclude={"primary_contact"})

    contact_person=payload.primary_contact.model_dump()

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO client(name, vat_no, tin, kyc_completed, addr_street_ln, addr_city, assigned_to)
                    VALUES (%(name)s, %(vat_no)s, %(tin)s, %(kyc_completed)s, %(address_street_ln)s, %(address_city)s, %(emp_id)s )
                    RETURNING cli_id
                    """,
                    client_data
                )
                cli_id=(await cur.fetchone())['cli_id']

                await cur.execute(
                    """
                    INSERT INTO contact_person(cli_id, emp_id, name, email, whatsapp, wechat)
                    VALUES (%(cli_id)s, %(emp_id)s, %(name)s, %(email)s, %(whatsapp)s, %(wechat)s )
                    RETURNING cpid
                    """,
                    {**contact_person, "cli_id": cli_id}
                )
                cp_id=(await cur.fetchone())['cpid']

        ret_vals={
            "cli_id": cli_id,
            "cpid": cp_id,
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

# TODO: EMPLOYEE RE-ASSIGNMENT PATCH FUNCTIONS

async def patch_clients(
        cli_id:int,
        payload:ClientPatch
)->dict:
    changes=payload.model_dump()

    if not changes:
        raise HTTPException(400, 'no client data to update...')
    
    set_clause=sql.SQL(",").join(
        sql.SQL("{}={}").format(sql.Identifier(col), sql.Placeholder(col))
        for col in changes
    )
    query=sql.SQL(
        "UPDATE client SET {} WHERE cli_id={} RETURNING *"
    ).format(set_clause, sql.Placeholder("cli_id"))

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, {**changes, "cli_id":cli_id})
                row= await cur.fetchone()
    except psycopg.errors.UniqueViolation as e:
        raise HTTPException(409, {
            "constraint": e.diag.constraint_name,
            "message": e.diag.message_primary,
        }) from e

    if row is None:
        raise HTTPException(404, f"Client {cli_id} not found")
    return row

async def patch_contact_person(
        cli_id:int,
        cpid:int,
        payload:ContactPatch
)->dict:
    changes=payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(400, 'No fields provided for update...')

    set_clause=sql.SQL(", ").join(
        sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
        for col in changes
    )
    query=sql.SQL(
        "UPDATE contact_person SET {} WHERE cpid = {} AND cli_id = {} RETURNING *"
    ).format(set_clause, sql.Placeholder("cpid"), sql.Placeholder("cli_id"))

    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, {**changes, "cpid": cpid, "cli_id": cli_id})
                row = await cur.fetchone()
    except (psycopg.errors.ForeignKeyViolation,
            psycopg.errors.CheckViolation) as e:
        raise HTTPException(422, {
            "constraint": e.diag.constraint_name,
            "message": e.diag.message_primary,
        }) from e

    if row is None:
        raise HTTPException(404, f"Contact person {cpid} not found for client {cli_id}")
    return row
