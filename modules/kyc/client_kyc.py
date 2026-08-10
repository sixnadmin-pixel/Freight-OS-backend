import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from fastapi import HTTPException

from data.dbconn import pool
from utils.helpers import build_insert
from modules.kyc.api import IKYCModule
from modules.kyc.client_kyc_types import KYCRequestNew, KYCRequestPatch, DocumentChecklistPatch, KYCStage
from modules.client.api import IClientModule
from modules.authen.api import IAuthnModule
from modules.inquiry.inquiry_types import ContactNew

class KYCModule(IKYCModule):
    def __init__(self, client_module: IClientModule, authentication: IAuthnModule):
        self.client = client_module
        self.authn = authentication

    async def create_kyc_request(self, cli_id:int, payload: KYCRequestNew):
        data= {**payload.model_dump(exclude={'contact_person','docs'}), 'cli_id': cli_id}
        contact=payload.contact_person.model_dump() if payload.contact_person else None
        docs=payload.docs.model_dump()
        emp_id=self.authn.get_current_user().emp_id

        if data is None:
            raise HTTPException(400, 'Missing fields...')
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                   await cur.execute(build_insert('kyc_request', {**data, 'emp_id':emp_id},'kyc_id'),{**data, 'emp_id':emp_id})
                   row = await cur.fetchone()

                   if contact:
                        await self.client.add_contact_person(cli_id, ContactNew(**contact))
  
                   kyc_id=row['kyc_id']

                   if kyc_id:
                       await cur.execute(build_insert('document_checklist',{**docs, 'kyc_id':kyc_id}, 'doc_id'), {**docs, 'kyc_id':kyc_id})
                       doc_row = await cur.fetchone()

                       if payload.docs.br_form:
                           await cur.execute(
                               "UPDATE kyc_request SET kyc_stage = %(stage)s WHERE kyc_id = %(kyc_id)s",
                               {"stage": KYCStage.documents_submitted.value, "kyc_id": kyc_id}
                           )

                       return doc_row
                    
                     
                   return row
                                        
        except (psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UndefinedColumn) as e:
            raise HTTPException(422, {
                "constraint": e.diag.constraint_name,
                "message": e.diag.message_primary,
            }) from e
        except psycopg.OperationalError as e:
            raise HTTPException(503, {"error": "database_unavailable", "message": str(e)}) from e

    async def patch_kyc_request(self, kyc_id: int, payload: KYCRequestPatch):
        changes = payload.model_dump(exclude_unset=True)
        updated_by= self.authn.get_current_user().emp_id

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE kyc_request SET {} WHERE kyc_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("kyc_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "updated_by":updated_by, "kyc_id": kyc_id})
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
            raise HTTPException(404, f"KYC request {kyc_id} not found")
        return row

    async def patch_document_checklist(self, doc_id: int, kyc_id: int, payload: DocumentChecklistPatch):
        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(400, 'No fields provided for update...')

        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder(col))
            for col in changes
        )
        query = sql.SQL(
            "UPDATE document_checklist SET {} WHERE doc_id = {} AND kyc_id = {} RETURNING *"
        ).format(set_clause, sql.Placeholder("doc_id"), sql.Placeholder("kyc_id"))

        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, {**changes, "doc_id": doc_id, "kyc_id": kyc_id})
                    row = await cur.fetchone()

                    if "br_form" in changes and changes["br_form"]:
                        await cur.execute(
                            "UPDATE kyc_request SET kyc_stage = %(stage)s WHERE kyc_id = %(kyc_id)s",
                            {"stage": KYCStage.documents_submitted.value, "kyc_id": kyc_id}
                        )
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
            raise HTTPException(404, f"Document checklist {doc_id} not found for KYC request {kyc_id}")
        return row

    async def update_kyc_stage(self, cli_id: int, stage: KYCStage) -> dict:
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        """
                        UPDATE kyc_request SET kyc_stage = %(stage)s
                        WHERE cli_id = %(cli_id)s
                        RETURNING *
                        """,
                        {"cli_id": cli_id, "stage": stage.value}
                    )
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
            raise HTTPException(404, f"KYC request for client {cli_id} not found")
        return row


