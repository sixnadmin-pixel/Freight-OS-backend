from pydantic import BaseModel
from datetime import date

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

class TariffPatch(BaseModel):
    lin_id : int | None = None
    tr_ln_id: int | None = None
    updated_by: int
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

class NACNew(BaseModel):
    cli_id: int
    emp_id: int
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
    updated_by: int


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