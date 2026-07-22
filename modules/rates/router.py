from fastapi import APIRouter, Depends

from modules.rates.rates_master.rate_types import TarrifNew, TariffPatch, NACNew, NACPatch, ContractNew, ContractPatch
from modules.rates.rates.rate_types import VesselByVesselRateNew, VesselByVesselRatePatch, FAKRatesNew, FAKRatesPatch, SpecialRateNew, SpecialRatePatch
from modules.rates.rates_master.api import IRatesMasterModule
from modules.rates.rates.api import IRatesModule

router = APIRouter(prefix='/rates', tags=['Rates'])

def get_rates_master_module() -> IRatesMasterModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")

def get_rates_module() -> IRatesModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


# --- Tariff Rates ---

@router.get("/tariff-rates")
async def list_tariff_rates(
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_all_tariff_rates()

@router.get("/tariff-rates/{tar_id}")
async def get_tariff_rate(
    tar_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_tariff_rate(tar_id)

@router.post("/tariff-rates", status_code=201)
async def create_tariff(
    payload: TarrifNew,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.add_tariff_rate(payload)

@router.patch("/tariff-rates/{tar_id}")
async def update_tariff(
    tar_id: int,
    payload: TariffPatch,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.patch_tariff_rate(tar_id, payload)

@router.delete("/tariff-rates/{tar_id}", status_code=200)
async def remove_tariff(
    tar_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.delete_tariff_rate(tar_id)


# --- NAC Rates ---

@router.get("/nac-rates")
async def list_nac_rates(
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_all_nac_rates()

@router.get("/nac-rates/client/{cli_id}")
async def list_client_nac_rates(
    cli_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_client_nac_rates(cli_id)

@router.get("/nac-rates/{nac_id}")
async def get_nac_rate(
    nac_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_nac_rate(nac_id)

@router.post("/nac-rates", status_code=201)
async def create_nac(
    payload: NACNew,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.add_nac_rate(payload)

@router.patch("/nac-rates/{nac_id}")
async def update_nac(
    nac_id: int,
    payload: NACPatch,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.patch_nac_rate(nac_id, payload)

@router.delete("/nac-rates/{nac_id}", status_code=200)
async def remove_nac(
    nac_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.delete_nac_rate(nac_id)


# --- Contracted Rates ---

@router.get("/contracted-rates")
async def list_contracted_rates(
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_all_contracted_rates()

@router.get("/contracted-rates/client/{cli_id}")
async def list_client_contracted_rates(
    cli_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_client_contracted_rates(cli_id)

@router.get("/contracted-rates/{crate_id}")
async def get_contracted_rate(
    crate_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.read_contracted_rate(crate_id)

@router.post("/contracted-rates", status_code=201)
async def create_contract(
    payload: ContractNew,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.add_contracted_rate(payload)

@router.patch("/contracted-rates/{crate_id}")
async def update_contract(
    crate_id: int,
    payload: ContractPatch,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.patch_contracted_rate(crate_id, payload)

@router.delete("/contracted-rates/{crate_id}", status_code=200)
async def remove_contract(
    crate_id: int,
    service: IRatesMasterModule = Depends(get_rates_master_module)
):
    return await service.delete_contracted_rate(crate_id)


# --- Vessel-by-Vessel Rates ---

@router.post("/vessel-rates", status_code=201)
async def create_vessel_rate(
    payload: VesselByVesselRateNew,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.add_vessel_rate(payload)

@router.patch("/vessel-rates/{srid}")
async def update_vessel_rate(
    srid: int,
    payload: VesselByVesselRatePatch,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.patch_vessel_rate(srid, payload)

@router.delete("/vessel-rates/{srid}", status_code=200)
async def remove_vessel_rate(
    srid: int,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.delete_vessel_rate(srid)


# --- Single non-persistent rate lookup ---

@router.get("/rate/{rate_id}")
async def get_non_persistent_rate(
    rate_id: int,
    rate_type: str,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.read_non_persistent_rate(rate_id, rate_type)


# --- Vessel-by-Vessel Rates (read all) ---

@router.get("/vessel-rates")
async def list_vessel_rates(
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.read_all_vessel_rates()


# --- FAK Rates ---

@router.get("/fak-rates")
async def list_fak_rates(
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.read_all_fak_rates()

@router.post("/fak-rates", status_code=201)
async def create_fak_rate(
    payload: FAKRatesNew,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.add_fak_rate(payload)

@router.patch("/fak-rates/{srid}")
async def update_fak_rate(
    srid: int,
    payload: FAKRatesPatch,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.patch_fak_rates(srid, payload)

@router.delete("/fak-rates/{srid}", status_code=200)
async def remove_fak_rate(
    srid: int,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.delete_fak_rate(srid)


# --- Special Rates ---

@router.get("/special-rates")
async def list_special_rates(
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.read_all_special_rates()

@router.post("/special-rates", status_code=201)
async def create_special_rate(
    payload: SpecialRateNew,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.add_special_rate(payload)

@router.patch("/special-rates/{sprid}")
async def update_special_rate(
    sprid: int,
    payload: SpecialRatePatch,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.patch_special_rate(sprid, payload)

@router.delete("/special-rates/{sprid}", status_code=200)
async def remove_special_rate(
    sprid: int,
    service: IRatesModule = Depends(get_rates_module)
):
    return await service.delete_special_rate(sprid)
