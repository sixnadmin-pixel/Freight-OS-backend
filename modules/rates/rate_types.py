from pydantic import BaseModel
from datetime import date, datetime

class SurchargeNew(BaseModel):
    rate_id: int
    type : str
    amt: float
    currency: str

class SurchargePatch(BaseModel):
    sur_id: int
    type : str | None = None
    amt: float | None= None
    currency: str | None = None

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
    surcharges: list[SurchargeNew] | None = None


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
    surcharges: list[SurchargePatch] | None = None

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
    surcharges: list[SurchargeNew] | None = None


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
    surcharges: list[SurchargePatch] | None = None

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
    surcharges: list[SurchargeNew] | None = None

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
    surcharges: list[SurchargePatch] | None = None


class TarrifNew(BaseModel):
    lin_id : int
    tr_ln_id: int
    updated_by: int
    salesperson: int
    origin: str
    destination: str
    free_time: str | None=None
    valid_from: date
    valid_to: date
    max_weight: int
    iwe: str | None = None
    container_type: str
    rate: float
    currency: str
    transit: str | None = None
    note: str | None = None
    special_remark: str | None = None
    surcharges: list[SurchargeNew] | None = None

class TariffPatch(BaseModel):
    lin_id : int | None = None
    tr_ln_id: int | None = None
    emp_id_sales: int | None = None
    origin: str | None = None
    destination: str | None = None
    free_time: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    max_weight: int | None = None
    iwe: str | None = None
    container_type: str | None = None
    rate: float | None = None
    currency: str | None = None
    transit: str | None = None
    note: str | None = None
    special_remark: str | None = None
    surcharges: list[SurchargePatch] | None = None

class NACNew(BaseModel):
    cli_id: int
    lin_id:int
    tr_ln_id: int
    nac_ref_id: str
    origin: str
    destination: str
    free_time: str | None = None
    valid_from: date
    valid_to: date
    max_weight: int | None = None
    iwe: str | None = None
    container_type: str
    rate: float
    currency: str
    transit: str | None = None
    note: str | None = None
    special_remark: str | None = None
    contracted_volume: int
    emp_id_sales: int
    emp_id_cs: int
    surcharges: list[SurchargeNew] | None = None


class NACPatch(BaseModel):
    cli_id: int | None = None
    emp_id: int | None = None
    lin_id: int | None = None
    tr_ln_id: int | None = None
    nac_ref_id: str | None = None
    origin: str | None = None
    destination: str | None = None
    free_time: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    max_weight: int | None = None
    iwe: str | None = None
    container_type: str | None = None
    rate: float | None = None
    currency: str | None = None
    transit: str | None = None
    note: str | None = None
    special_remark: str | None = None
    contracted_volume: int | None = None
    updated_by: int
    emp_id_sales: int | None = None
    emp_id_cs: int | None = None
    surcharges: list[SurchargePatch] | None = None

class ContractNew(BaseModel):
    lin_id: int
    tr_ln_id: int
    inq_id: int | None = None
    contract_ref_id: str
    valid_from: date
    valid_to: date
    contracted_volume: int
    iwe: str | None = None
    container_type: str
    transit: str | None = None
    updated_by: int
    origin: str
    destination : str
    free_time: str | None = None
    max_weight : int | None = None
    note : str | None = None
    special_remark : str | None = None
    rate: float
    currency: str
    emp_id_sales: int
    emp_id_cs: int
    client_ids: list[int] | None=None
    surcharges: list[SurchargeNew] | None = None

class ContractPatch(BaseModel):
    lin_id: int | None = None
    tr_ln_id: int| None = None
    inq_id: int | None = None
    contract_ref_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    contracted_volume: int | None = None
    iwe: str | None = None
    container_type: str | None = None
    transit: str | None = None
    updated_by: int | None = None
    origin: str | None = None
    destination : str | None = None
    free_time: str | None = None
    max_weight : int | None = None
    note : str | None = None
    special_remark : str | None = None
    rate: float | None = None
    currency: str | None = None
    emp_id_sales: int | None = None
    emp_id_cs: int | None = None
    client_ids: list[int] | None=None
    surcharges: list[SurchargePatch] | None = None