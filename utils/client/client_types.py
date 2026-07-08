from pydantic import BaseModel

from utils.inquiry.inquiry_types import ContactNew

class ClientNew(BaseModel):
    emp_id:int
    name: str
    vat_no: str | None = None
    tin: str | None = None
    kyc_completed: bool | None = None
    address_street_ln: str
    address_city:str
    primary_contact: ContactNew


class ClientPatch(BaseModel):
    updated_by:int
    name: str | None = None
    vat_no: str | None = None
    tin: str | None = None
    kyc_completed: bool | None = None
    address_street_ln: str
    address_city:str

class ContactPatch(BaseModel):
    updated_by:int
    name: str | None = None
    emp_id: int | None = None
    email: str | None = None
    whatsapp: str | None = None
    wechat: str | None = None