from fastapi import APIRouter, Depends

from modules.kyc.client_kyc_types import KYCRequestNew, KYCRequestPatch, DocumentChecklistPatch, KYCStage
from modules.kyc.api import IKYCModule

router = APIRouter(prefix='/kyc', tags=['KYC'])

def get_kyc_module() -> IKYCModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.post("/kyc-requests", status_code=201)
async def create_kyc_request(
    cli_id:int,
    payload: KYCRequestNew,
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.create_kyc_request(cli_id, payload)

@router.patch("/kyc-requests/{kyc_id}")
async def patch_kyc_request(
    kyc_id: int,
    payload: KYCRequestPatch,
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.patch_kyc_request(kyc_id, payload)

@router.patch("/kyc-requests/{kyc_id}/documents/{doc_id}")
async def patch_document_checklist(
    kyc_id: int,
    doc_id: int,
    payload: DocumentChecklistPatch,
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.patch_document_checklist(doc_id, kyc_id, payload)

@router.post("/kyc-requests/clients/{cli_id}/stage", status_code=201)
async def create_kyc_stage(
    cli_id: int,
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.create_kyc_stage(cli_id)

@router.patch("/kyc-requests/clients/{cli_id}/stage")
async def update_kyc_stage(
    cli_id: int,
    stage: KYCStage,
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.update_kyc_stage(cli_id, stage)

@router.get("/kyc-requests/pending")
async def read_all_pending_kyc(
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.read_all_pending_kyc()

@router.get("/kyc-requests/requests")
async def read_all_pending_kyc(
    service: IKYCModule = Depends(get_kyc_module)
):
    return await service.read_all_kyc_requests()
