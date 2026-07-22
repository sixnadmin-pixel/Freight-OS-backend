from pydantic import BaseModel

from modules.inquiry.inquiry_types import ContactNew

class ClientNew(BaseModel):
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
    name: str | None = None
    vat_no: str | None = None
    tin: str | None = None
    kyc_completed: bool | None = None
    addr_street_ln: str
    addr_city:str

class ContactPatch(BaseModel):
    name: str | None = None
    designation : str | None = None
    email: str | None = None
    whatsapp: str | None = None
    phone: str | None = None
    wechat: str | None = None

class KYCStatusPatch(BaseModel):
    kyc_completed: bool = True