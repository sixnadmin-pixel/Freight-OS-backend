from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum

class bookingRequestStatus(str, Enum):
    request_initiated = 'request_initiated'
    request_reviewed = 'request_reviewed'
    request_booking_success = 'request_booking_success'
    request_booking_failure = 'request_booking_failure'
    release_order_received = 'release_order_received'

class bookingRequestNew(BaseModel):
    inq_id: int 
    cli_id : int
    lin_id: int
    origin : str
    destination : str
    vessel : str
    vessel_etd : datetime
    voyage : str
    cargo_ready_date : date
    delivery_type: str
    agreed_rate : float
    rate_remark : str | None = None
    delivery_term : str
    commodity : int
    hs_code: str
    contract_no : str | None = None
    ra_number : str | None = None
    specific_routing : str | None = None
    bl_type: str
    booking_type : str | None = None
    reefer_temp : str | None = None
    delivery_agent: str | None = None
    status : bookingRequestStatus = bookingRequestStatus.request_initiated
    notes : str


class bookingRequestPatch(BaseModel):
        inq_id: int 
        cli_id : int
        lin_id: int | None = None
        origin : str | None = None
        destination : str | None = None
        vessel : str | None = None
        vessel_etd : datetime | None = None
        voyage : str | None = None
        cargo_ready_date : date | None = None
        delivery_type: str | None = None
        agreed_rate : float | None = None
        rate_remark : str | None = None
        delivery_term : str | None = None
        commodity : int | None = None
        hs_code: str | None = None
        contract_no : str | None = None
        ra_number : str | None = None
        specific_routing : str | None = None
        bl_type: str
        booking_type : str | None = None
        reefer_temp : str | None = None
        delivery_agent: str | None = None
        status : str | None = None
        notes : str | None = None

class bookingRequestReview(BaseModel):
        inq_id: int 
        cli_id : int
        lin_id: int | None = None
        origin : str | None = None
        destination : str | None = None
        vessel : str | None = None
        vessel_etd : datetime | None = None
        voyage : str | None = None
        cargo_ready_date : date | None = None
        delivery_type: str | None = None
        agreed_rate : float | None = None
        rate_remark : str | None = None
        delivery_term : str | None = None
        commodity : int | None = None
        hs_code: str | None = None
        contract_no : str | None = None
        ra_number : str | None = None
        specific_routing : str | None = None
        bl_type: str
        booking_type : str | None = None
        reefer_temp : str | None = None
        delivery_agent: str | None = None
        status : bookingRequestStatus = bookingRequestStatus.request_reviewed
        notes : str | None = None

class bookingSucess(BaseModel):
        booking_id: int
        status: bookingRequestStatus = bookingRequestStatus.request_booking_success

# class cutoffSchedules(BaseModel):
#         bl_cutoff : date
#         vgm_weight : float
           
