from pydantic import BaseModel

class RateRequestNew(BaseModel):
    inq_id: int
    emp_id_requested: int
    is_given: bool = False
    remark: str

class RateRequestPatch(BaseModel):
    emp_id_requester: int | None = None
    emp_id_requested: int | None = None
    is_given: bool = False
    remark: str

class RateRequestOptionNew(BaseModel):
    request_id: int
    rate_type: str
    rate_id: int

class RateRequestOptionPatch(BaseModel):
    updated_by: int
    rate_type: str | None = None
    rate_id: int | None = None

