from pydantic import BaseModel
from datetime import date, datetime

class VesselByVesselRateNew(BaseModel):
    inq_id: int
    voyage : str 
    vessel_name: str
    eta : date
    etd : date
    rate: float
    currency : str
    fcl_opening : datetime
    fcl_cutoff : datetime
    origin : str
    destination : str
    tr_ln_id: int
    iwe: str | None = None
    free_days: str | None = None
    container_type : str
    volume: int
    max_weight: int | None = None
    note: str | None = None
    special_remark : str | None = None
    issold : bool | None = None
    iscancelled: bool | None = None
    cancellationreason: str | None = None
    cancellationfee: float | None = None


class VesselByVesselRatePatch(BaseModel):
    inq_id: int | None= None
    voyage : str | None = None
    vessel_name: str | None = None
    eta : date | None = None
    etd : date | None = None
    rate: float | None = None
    currency : str | None = None
    fcl_opening : datetime | None = None
    fcl_cutoff : datetime | None = None
    origin : str| None = None
    destination : str | None = None
    tr_ln_id: int | None = None
    iwe: str | None = None
    emp_id: int | None = None
    free_days: str | None = None
    container_type : str
    volume: int | None = None
    max_weight: int | None = None
    note: str | None = None
    special_remark : str | None = None
    issold : bool | None = None
    iscancelled: bool | None = None
    cancellationreason: str | None = None
    cancellationfee: float | None = None

class FAKRatesNew(BaseModel):
    lin_id: int
    tr_ln_id: int
    inq_id: int
    valid_from : datetime 
    valid_to : datetime 
    volume: int
    iwe: str | None=None
    container_type: str
    transit: str | None=None
    origin: str
    destination: str
    free_time: str | None=None
    max_weight: int | None=None
    note: str | None=None
    special_remark: str | None=None
    rate: float
    currency: str
    issold: bool | None=None


class FAKRatesPatch(BaseModel):
    lin_id: int | None=None
    tr_ln_id: int | None=None
    inq_id: int | None=None
    valid_from : datetime | None=None
    valid_to : datetime | None=None
    volume: int | None=None
    iwe: str | None=None
    container_type: str | None=None
    transit: str | None=None
    origin: str | None=None
    destination: str | None=None
    free_time: str | None=None
    max_weight: int | None=None
    note: str | None=None
    special_remark: str | None=None
    rate: float| None=None
    currency: str | None=None
    issold: bool | None=None

class SpecialRateNew(BaseModel):
    lin_id: int
    tr_ln_id: int
    inq_id: int
    com_id: int
    valid_from : datetime 
    valid_to : datetime 
    rate: float 
    transit: str | None=None
    origin: str
    destination: str
    iwe: str | None=None
    free_days: str | None=None
    container_type: str 
    volume: int
    max_weight: int | None=None
    currency: str
    note: str | None=None
    special_remark: str | None=None
    issold: bool | None=None

class SpecialRatePatch(BaseModel):
    lin_id: int | None=None
    tr_ln_id: int | None=None
    inq_id: int | None=None
    com_id: int | None=None
    valid_from : datetime  | None=None
    valid_to : datetime | None=None
    rate: float | None=None
    transit: str | None=None
    origin: str | None=None
    destination: str | None=None
    iwe: str | None=None
    free_days: str | None=None
    container_type: str | None=None
    volume: int | None=None
    max_weight: int | None=None
    currency: str | None=None
    note: str | None=None
    special_remark: str | None=None
    isSold: bool | None=None