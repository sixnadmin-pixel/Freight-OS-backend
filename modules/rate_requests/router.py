from fastapi import APIRouter, Depends

# 1. Import the pure types and the Contract (Protocol)
from modules.rate_requests.rate_request_types import RateRequestNew, RateRequestOptionNew, RateRequestOptionPatch
from modules.rate_requests.api import IRateRequestModule

router = APIRouter(prefix='/rate-requests', tags=['Rate Requests'])

# 2. Create the placeholder dependency
def get_rate_request_module() -> IRateRequestModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


# --- Rate Requests ---

@router.get("/incoming")
async def list_incoming_requests(
    service: IRateRequestModule = Depends(get_rate_request_module)
):
    return await service.read_incoming_requests()

@router.post("", status_code=201)
async def create_rate_request(
    payload: RateRequestNew, 
    service: IRateRequestModule = Depends(get_rate_request_module)  # <--- 3. Inject
):
    return await service.add_rate_request(payload)

@router.delete("/{request_id}", status_code=200)
async def remove_rate_request(
    request_id: int, 
    service: IRateRequestModule = Depends(get_rate_request_module)
):
    return await service.delete_rate_request(request_id)


# --- Rate Request Options ---

@router.post("/{request_id}/options", status_code=201)
async def create_request_option(
    request_id: int, 
    payload: RateRequestOptionNew, 
    service: IRateRequestModule = Depends(get_rate_request_module)
):
    return await service.add_request_option(request_id, payload)

@router.patch("/{request_id}/options/{option_id}")
async def update_request_option(
    request_id: int, 
    option_id: int, 
    payload: RateRequestOptionPatch, 
    service: IRateRequestModule = Depends(get_rate_request_module)
):
    # Note: Ensure the argument order matches what you defined in the Protocol/Impl class!
    return await service.patch_rate_request_option(option_id, request_id, payload)

@router.delete("/{request_id}/options/{option_id}", status_code=200)
async def remove_request_option(
    request_id: int, 
    option_id: int, 
    service: IRateRequestModule = Depends(get_rate_request_module)
):
    return await service.delete_rate_request_option(request_id, option_id)