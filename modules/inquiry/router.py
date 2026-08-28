from fastapi import APIRouter, Depends, UploadFile, File

from modules.inquiry.inquiry_types import InquiryNewNew, InquiryOldNew, InquiryOldOld, InquiryPatch, CommodityPatch, ContainerPatch, RfqBulkNew, RfqPreviewResult
from modules.inquiry.api import IInquiryModule
from modules.inquiry.activity_log.activity_types import WorkflowStatusNew, WorkflowStatusPatch
from modules.inquiry.activity_log.api import IAcitivityLog

router = APIRouter(prefix='/inquiries', tags=['Inquiries'])

def get_inquiry_module() -> IInquiryModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")

def get_activity_log_module() -> IAcitivityLog:
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


@router.post("/rfq", status_code=201)
async def create_rfq(
    payload: RfqBulkNew,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.create_rfq_bulk(payload)


@router.post("/rfq/preview")
async def preview_rfq(
    file: UploadFile = File(...),
    service: IInquiryModule = Depends(get_inquiry_module)
) -> RfqPreviewResult:
    return await service.preview_rfq_excel(await file.read())


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

@router.get("/inquiries/{inq_id}")
async def read_single_inquiry(
    inq_id: int,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.read_inquiry(inq_id)

@router.get("/inquiries")
async def read_all_inquiry(
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.read_all_inquiry()

@router.patch("/inquiries/{inq_id}/containers/{cont_id}")
async def patch_container(
    inq_id: int,
    cont_id: int,
    payload: ContainerPatch,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.patch_container_fields(inq_id, cont_id, payload)

@router.delete("/inquiries/{inq_id}", status_code=200)
async def delete_inquiry(
    inq_id: int,
    service: IInquiryModule = Depends(get_inquiry_module)
):
    return await service.delete_inquiry(inq_id)


# --- Workflow / Activity Log ---

@router.post("/workflow", status_code=201)
async def create_workflow(
    payload: WorkflowStatusNew,
    service: IAcitivityLog = Depends(get_activity_log_module)
):
    return await service.create_workflow(payload)

@router.patch("/workflow/{inq_id}")
async def update_workflow_status(
    inq_id: int,
    payload: WorkflowStatusPatch,
    service: IAcitivityLog = Depends(get_activity_log_module)
):
    return await service.update_workflow_status(inq_id, payload)
