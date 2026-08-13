from pydantic import BaseModel
from datetime import date

from modules.client.client_types import ContactNew

<<<<<<< Updated upstream
=======
class KYCStage(str, Enum):
     kyc_uninitiated          ='kyc_uninitiated'
     kyc_pending              ='kyc_pending'
     documents_submitted      ='documents_submitted'
     kyc_completed            ='kyc_completed'


>>>>>>> Stashed changes
class DocumentChecklist(BaseModel):
    cli_id: int
    br_form: str | None = None
    vat_certificate: str | None = None
    svat_certificate: str | None = None
    tin_certificate: str | None = None
    form20: str | None = None

class KYCRequestNew(BaseModel):
    br_number: str
    parent_organization: str | None = None
    emp_id_sales: int | None = None
    emp_id_cs: int | None = None
    document_submission_deadline: date
    cli_type: str
    currency: str
    website : str | None = None
    svat_no : str | None = None
    tax_exemptions: str
    sea_imports: bool = False
    sea_exports: bool = False
    trade_lanes: bool = False
    forwarding: bool = False
    cross_trade: bool = False
    air_imports: bool = False
    air_exports: bool = False
    general_cargo: bool = False
    dangerous_goods: bool = False
    perishable_goods: bool = False
    contact_person: ContactNew | None = None
    docs: DocumentChecklist

class DocumentChecklistPatch(BaseModel):
    cli_id: int | None = None
    br_form: str | None = None
    vat_certificate: str | None = None
    svat_certificate: str | None = None
    tin_certificate: str | None = None
    form20: str | None = None

class  KYCRequestPatch(BaseModel):
    br_number: str | None = None
    parent_organization: str | None = None
    emp_id_sales: int | None = None
    emp_id_cs: int | None = None
    document_submission_deadline: date
    cli_type: str | None = None
    currency: str | None = None
    website : str | None = None
    svat_no : str | None = None
    tax_exemptions: str | None = None
    sea_imports: bool = False
    sea_exports: bool =False
    trade_lanes: bool = False
    forwarding: bool = False
    cross_trade: bool = False
    air_imports: bool = False
    air_exports: bool = False
    general_cargo: bool = False
    dangerous_goods: bool = False
    perishable_goods: bool = False



