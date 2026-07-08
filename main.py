from fastapi import FastAPI
from contextlib import asynccontextmanager

from data.dbconn import pool
from utils.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch
from utils.inquiry.inquiry import create_inquiry_case_1, create_inquiry_case_2, create_inquiry_case_3, patch_inquiry_fields, patch_commodity_fields, patch_container_fields

from utils.client.client_types import ClientNew, ClientPatch, ContactPatch
from utils.client.client import create_new_client, patch_clients, patch_contact_person

@asynccontextmanager
async def lifespan(app:FastAPI):
   await pool.open()
   yield
   await pool.close()

app = FastAPI(lifespan=lifespan)



@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/inquiries-new-new", status_code=201)
async def create_inquiry(payload: InquiryNewNew):
    return await create_inquiry_case_1(payload)

@app.post("/inquiries-old-new", status_code=201)
async def create_inquiry(payload: InquiryOldNew):
    return await create_inquiry_case_2(payload)

@app.post("/inquiries-old-old", status_code=201)
async def create_inquiry(payload: InquiryOldOld):
    return await create_inquiry_case_3(payload)

@app.patch("/inquiries/{inq_id}")
async def patch_inquiry(inq_id: int, payload: InquiryPatch):
    return await patch_inquiry_fields(inq_id, payload)

@app.patch("/inquiries/{inq_id}/commodities/{com_id}")
async def patch_commodity(inq_id: int, com_id: int, payload: CommodityPatch):
    return await patch_commodity_fields(inq_id, com_id, payload)

@app.patch("/inquiries/{inq_id}/containers/{cont_id}")
async def patch_container(inq_id: int, cont_id: int, payload: ContainerPatch):
    return await patch_container_fields(inq_id, cont_id, payload)

@app.post("/clients", status_code=201)
async def add_client(payload: ClientNew):
    return await create_new_client(payload)

@app.patch("/clients/{cli_id}")
async def update_client(cli_id: int, payload: ClientPatch):
    return await patch_clients(cli_id, payload)

@app.patch("/clients/{cli_id}/contacts/{cpid}")
async def update_contact(cli_id: int, cpid: int, payload: ContactPatch):
    return await patch_contact_person(cli_id, cpid, payload)

