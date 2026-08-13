from fastapi import APIRouter, Depends

from modules.quotation.quotation_type import QuotationNew, QuotationPatch, QuotationStatus
from modules.quotation.api import IQuotationModule

router = APIRouter(prefix='/quotations', tags=['Quotations'])

def get_quotation_module() -> IQuotationModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.post("/", status_code=201)
async def create_quotation(
    payload: QuotationNew,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.create_quotation(payload)

@router.get("/")
async def read_all_quotations(
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.read_all_quotations()

@router.get("/{quote_id}")
async def read_quotation(
    quote_id: int,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.read_quotation(quote_id)

@router.patch("/{quote_id}")
async def patch_quotation(
    quote_id: int,
    payload: QuotationPatch,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.patch_quotation(quote_id, payload)

@router.delete("/{quote_id}", status_code=200)
async def delete_quotation(
    quote_id: int,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.delete_quotation(quote_id)

@router.patch("/{quote_id}/send")
async def send_quotation(
    quote_id: int,
    status: QuotationStatus,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.send_quotation(quote_id, status)

@router.patch("/{quote_id}/response")
async def record_response(
    quote_id: int,
    status: QuotationStatus,
    service: IQuotationModule = Depends(get_quotation_module)
):
    return await service.record_response(quote_id, status)
