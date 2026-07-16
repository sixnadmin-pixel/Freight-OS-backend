from fastapi import APIRouter, Depends

from modules.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch
from modules.inquiry.api import IInquiryModule

router = APIRouter(prefix='/inquiries', tags=['Inquiries'])

def get_inquiry_module() -> IInquiryModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.post("/inquiries-new-new", status_code=201)
async def create_inquiry_new_new(
    payload: InquiryNewNew,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.create_inquiry_case_1(payload)

@router.post("/inquiries-old-new", status_code=201)
async def create_inquiry_old_new(
    payload: InquiryOldNew,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.create_inquiry_case_2(payload)

@router.post("/inquiries-old-old", status_code=201)
async def create_inquiry_old_old(
    payload: InquiryOldOld,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.create_inquiry_case_3(payload)

@router.patch("/inquiries/{inq_id}")
async def patch_inquiry(
    inq_id: int,
    payload: InquiryPatch,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.patch_inquiry_fields(inq_id, payload)

@router.patch("/inquiries/{inq_id}/commodities/{com_id}")
async def patch_commodity(
    inq_id: int,
    com_id: int,
    payload: CommodityPatch,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.patch_commodity_fields(inq_id, com_id, payload)

@router.patch("/inquiries/{inq_id}/containers/{cont_id}")
async def patch_container(
    inq_id: int,
    cont_id: int,
    payload: ContainerPatch,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.patch_container_fields(inq_id, cont_id, payload)
