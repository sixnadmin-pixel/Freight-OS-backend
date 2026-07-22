from fastapi import APIRouter, Depends

from modules.liners.liner_types import LinerNew
from modules.liners.api import ILinersModule

router = APIRouter(prefix='/liners', tags=['Liners'])


def get_liners_module() -> ILinersModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.get("")
async def list_liners(
    service: ILinersModule = Depends(get_liners_module)
):
    return await service.read_all_liners()


@router.post("", status_code=201)
async def create_liner(
    payload: LinerNew,
    service: ILinersModule = Depends(get_liners_module)
):
    return await service.add_liner(payload)
