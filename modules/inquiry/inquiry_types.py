from pydantic import BaseModel
from datetime import date
from typing import Literal

# CASE 1 TYPES

class ClientNew(BaseModel):
    name: str
    kyc_completed: bool = False


class ContactNew(BaseModel):
    name: str
    designation: str | None = None
    email: str | None = None
    whatsapp: str | None = None
    phone: str | None = None
    wechat: str | None = None


class CommodityNew(BaseModel):
    name: str | None = None
    com_type: str | None = None
    hs_code: str | None = None
    description: str | None = None
    weight: float | None = None
    remark: str | None = None


class ContainerNew(BaseModel):
    commodity_index: int | None = None    # position in the commodities list, or None if unlinked
    container_type: str | None = None
    temperature: int | None = None
    qty: int | None = None                # schema CHECK: qty > 0
    destination: str  
    address: str | None = None                 
    zip_code: str | None = None
    is_fully_loaded: bool = False
    free_time: str | None = None


class InquiryFields(BaseModel):
    sbu: str | None = None
    remark: str | None = None
    origin: str                           # NOT NULL, FK -> port(unlocode)
    incoterm: str | None = None
    cargo_ready_date: date | None = None
    priority: str | None = None
    preferred_liners: str | None = None
    preferred_rate: float | None = None
    service_mode: Literal["DOOR_TO_DOOR", "PORT_TO_PORT", "PORT_TO_DOOR","DOOR_TO_PORT"] | None = None


class InquiryNewNew(BaseModel):
    client: ClientNew
    contact: ContactNew
    inquiry: InquiryFields
    commodities: list[CommodityNew] = []
    containers: list[ContainerNew] = []


# CASE 2 TYPES

class InquiryOldNew(BaseModel):
    cli_id: int
    contact: ContactNew
    inquiry: InquiryFields
    commodities: list[CommodityNew] = []
    containers: list[ContainerNew] = []

# CASE 3 TYPES

class InquiryOldOld(BaseModel):
    cli_id:int
    cp_id:int
    inquiry: InquiryFields
    commodities: list[CommodityNew] = []
    containers: list[ContainerNew] = []

# Patch an inquiry

class InquiryPatch(BaseModel):
    sbu: str | None = None
    remark: str | None = None
    origin: str | None = None                         # NOT NULL, FK -> port(unlocode)
    incoterm: str | None = None
    cargo_ready_date: date | None = None
    priority: str | None = None
    preferred_liners: str | None = None
    preferred_rate: float | None = None
    service_mode: Literal["DOOR_TO_DOOR", "PORT_TO_PORT"] | None = None


class CommodityPatch(BaseModel):
    com_type: str | None = None
    hs_code: str | None = None
    description: str | None = None
    weight: float | None = None
    remark: str | None = None

class ContainerPatch(BaseModel):
    container_type: str | None = None
    temperature: int | None = None
    qty: int | None = None                # schema CHECK: qty > 0
    destination: str | None = None      
    address: str | None = None              # NOT NULL, FK -> port(unlocode)
    zip_code: str | None = None
    is_fully_loaded: bool = False
    free_time: str | None = None

class InquiryView(BaseModel):
    sbu: str | None = None
    remark: str | None = None
    origin: str                           # NOT NULL, FK -> port(unlocode)
    incoterm: str | None = None
    cargo_ready_date: date | None = None
    priority: str | None = None
    preferred_liners: str | None = None
    preferred_rate: float | None = None
    service_mode: Literal["DOOR_TO_DOOR", "PORT_TO_PORT"] | None = None
    contact: ContactNew
    commodity: CommodityNew
    container: ContainerNew



# RFQ BULK TYPES
# One RFQ = one customer + many origin-destination routes.
# Each line reuses the existing per-inquiry building blocks.

class RfqLine(BaseModel):
    inquiry: InquiryFields                  # carries origin
    commodities: list[CommodityNew] = []
    containers: list[ContainerNew] = []     # carries destination


class RfqBulkNew(BaseModel):
    cli_id: int                             # RFQs are existing customers only
    cp_id: int | None = None                # existing contact, if known
    contact: ContactNew | None = None       # else create ONE, reused by every line
    lines: list[RfqLine]



class RfqPreviewRow(BaseModel):
    row: int
    origin: str = ""             # as written in the sheet
    origin_code: str = ""        # resolved UN/LOCODE, "" if unresolved
    destination: str = ""
    destination_code: str = ""
    country: str = ""
    known_port: bool = False     # True when BOTH ends resolved


class RfqPreviewResult(BaseModel):
    destination: str | None
    rows: list[RfqPreviewRow]
    skipped: list[dict]
    unknown_count: int

