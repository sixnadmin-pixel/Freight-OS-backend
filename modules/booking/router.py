from fastapi import APIRouter, Depends

from modules.booking.booking_types import bookingRequestNew, bookingRequestPatch, bookingRequestReview
from modules.booking.api import IBookingModule
from modules.authen.api import IAuthnModule

router = APIRouter(prefix='/booking-requests', tags=['Booking Requests'])


def get_booking_module() -> IBookingModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")

def get_authn_module() -> IAuthnModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.post("", status_code=201)
async def create_booking_request(
    payload: bookingRequestNew,
    service: IBookingModule = Depends(get_booking_module),
    authn: IAuthnModule = Depends(get_authn_module),
):
    emp_id_cs = authn.get_current_user().emp_id
    return await service.create_new_booking_req(emp_id_cs, payload)


@router.patch("")
async def patch_booking_request(
    payload: bookingRequestPatch,
    service: IBookingModule = Depends(get_booking_module),
    authn: IAuthnModule = Depends(get_authn_module),
):
    updated_by = authn.get_current_user().emp_id
    return await service.patch_booking_req(updated_by, payload)


@router.patch("/review")
async def review_booking_request(
    payload: bookingRequestReview,
    service: IBookingModule = Depends(get_booking_module),
    authn: IAuthnModule = Depends(get_authn_module),
):
    reviewed_by = authn.get_current_user().emp_id
    return await service.review_booking_req(reviewed_by, payload)
