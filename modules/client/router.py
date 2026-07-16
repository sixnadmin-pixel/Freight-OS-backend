from fastapi import APIRouter, Depends

from modules.client.client_types import ClientNew, ClientPatch, ContactPatch
from modules.client.api import IClientModule

router = APIRouter(prefix='/clients', tags=['Clients'])

def get_client_module() -> IClientModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.post("/clients", status_code=201)
async def add_client(
    payload: ClientNew,
    service: IClientModule = Depends(get_client_module)
):
    return await service.create_new_client(payload)

@router.patch("/clients/{cli_id}")
async def update_client(
    cli_id: int,
    payload: ClientPatch,
    service: IClientModule = Depends(get_client_module)
):
    return await service.patch_clients(cli_id, payload)

@router.patch("/clients/{cli_id}/contacts/{cpid}")
async def update_contact(
    cli_id: int,
    cpid: int,
    payload: ContactPatch,
    service: IClientModule = Depends(get_client_module)
):
    return await service.patch_contact_person(cli_id, cpid, payload)
