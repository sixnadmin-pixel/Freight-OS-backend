from pydantic import BaseModel

from modules.inquiry.inquiry_types import ContactNew

class ClientNew(BaseModel):
    emp_id:int
    name: str
    assigned_to: int | None= None
    vat_no: str | None = None
    tin: str | None = None
    kyc_completed: bool | None = None
    addr_street_ln: str
    addr_city:str
    addr_country: str
    primary_contact: ContactNew


class ClientPatch(BaseModel):
    updated_by:int
    name: str | None = None
    vat_no: str | None = None
    tin: str | None = None
    kyc_completed: bool | None = None
    addr_street_ln: str
    addr_city:str

class ContactPatch(BaseModel):
    updated_by:int
    name: str | None = None
    emp_id: int | None = None
    email: str | None = None
    whatsapp: str | None = None
    wechat: str | None = None