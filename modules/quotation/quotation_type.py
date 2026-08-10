from pydantic import BaseModel
from typing import date
from enum import Enum

class QuotationStatus(str, Enum):
    in_prep= 'in_prep'
    sent ='sent'
    accepted='accepted'
    rejected = 'rejected'

class QuotationOptions(BaseModel):
    inq_id: int
    rate_id: int 
    option_id: int
    amt: float
    currency: str

class QuotationNew(BaseModel):
    inq_id: int
    status: QuotationStatus = QuotationStatus.in_prep
    quote_date: date
    is_follow_up: bool = False
    acceptence_deadline: date | None = None
    sent_via: str
    options: list[QuotationOptions]

class QuotationPatch(BaseModel):
    status: QuotationStatus | None = None
    quote_date: date | None = None
    is_follow_up: bool = False
    acceptence_deadline: date | None = None
    sent_via: str | None = None
    options: list[QuotationOptions] | None = None
    






