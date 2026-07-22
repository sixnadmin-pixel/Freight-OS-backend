import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from modules.helpers import build_insert
from modules.client.api import IClientModule
from modules.authen.api import IAuthnModule
from modules.client.client_types import ClientNew, ClientPatch, ContactPatch, KYCStatusPatch
from modules.inquiry.inquiry_types import ContactNew

# TODO client assignment 
# assigned_to is how we 


class ClientModule(IClientModule):
    def __init__(self, authentiation: IAuthnModule):
        self.authen=authentiation

    async def create_new_client(self, payload: ClientNew) -> dict:
        emp_id = self.authen.get_current_user().emp_id
        client_data = payload.model_dump(exclude={"primary_contact"})
        contact_person = payload.primary_contact.model_dump()

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    
                    cli_data={**client_data, "emp_id":emp_id}

                    await cur.execute(build_insert("client", client_data, "cli_id"), client_data)
                    cli_id = (await cur.fetchone())['cli_id']

                    cp_data = {**contact_person, "cli_id": cli_id}
                    await cur.execute(build_insert("contact_person", cp_data, "cpid"), cp_data)
                    cp_id = (await cur.fetchone())['cpid']

            return {"cli_id": cli_id, "cpid": cp_id}

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

    # TODO: EMPLOYEE RE-ASSIGNMENT PATCH FUNCTIONS

    async def patch_clients(self, cli_id: int, payload: ClientPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by = self.authen.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'no client data to update...')

        set_clause = sql.SQL(",").join(
            sql.SQL("{}={}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE client SET {} WHERE cli_id={} RETURNING *"
        ).format(set_clause, sql.Placeholder("cli_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "cli_id": cli_id, "updated_by":updated_by})
                    row = await cur.fetchone()
        except psycopg.errors.UniqueViolation as e:
            raise HTTPException(409, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

        if row is None:
            raise HTTPException(404, f"Client {cli_id} not found")
        return row
    
    async def read_all_clients(self):
        emp_id= self.authen.get_current_user().emp_id

        QUERY="""
              SELECT cli_id, name FROM client WHERE assigned_to=%(emp_id)s
              """
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"emp_id": emp_id})
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

    async def fetch_all_contacts(self, cli_id):
        QUERY = "SELECT cpid, name FROM contact_person WHERE cli_id=%(cli_id)s"
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(QUERY, {"cli_id": cli_id})
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

    async def patch_contact_person(self, cli_id: int, cpid: int, payload: ContactPatch) -> dict:
        changes = payload.model_dump(exclude_unset=True)
        updated_by= self.authen.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE contact_person SET {} WHERE cpid = {} AND cli_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("cpid"), sql.Placeholder("cli_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "cpid": cpid, "cli_id": cli_id, "updated_by":updated_by})
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
            raise HTTPException(404, f"Contact person {cpid} not found for client {cli_id}")
        return row
    
    async def add_contact_person(
            self,
            cli_id:int,
            payload: ContactNew
    )->dict:
        data=payload.model_dump()
        emp_id=self.authen.get_current_user().emp_id
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(build_insert('contact_person',{**data,'cli_id':cli_id},'cpid'), {**data,'cli_id':cli_id, 'emp_id':emp_id})
                    row = await cur.fetchone()
                    if row is None:
                        raise HTTPException(404, f"Contact person not found for client {cli_id}")
                    return row
                
        except psycopg.errors.UniqueViolation as e:
            raise HTTPException(409, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_kyc_status(self, cli_id, payload:KYCStatusPatch):
        changes = payload.model_dump(exclude_unset=True)
        updated_by= self.authen.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE client SET {} WHERE cli_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("cli_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes,"cli_id": cli_id, "updated_by":updated_by})
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
            raise HTTPException(404, f"Could not update the KYC status of {cli_id}")
        return row
    
    async def read_kyc_status(self, cli_id):
        emp_id= self.authen.get_current_user().emp_id

        QUERY="""
                SELECT kyc_completed FROM client WHERE assigned_to=%(emp_id)s AND cli_id=%(cli_id)s
                """
        try:
                async with pool.connection() as conn:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(QUERY, {"emp_id": emp_id, "cli_id":cli_id})
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
