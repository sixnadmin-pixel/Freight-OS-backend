from pydantic import BaseModel
from datetime import date

class releaseOrderNew(BaseModel):
      inq_id: int
      booking_id: int
      cli_id: int
      liner_ref: str | None = None
      empty_pickup: date | None = None
      validity_exp: date | None = None
      depot_name: str | None = None
      depot_addr: str | None = None
      vessel_cutoff: date | None = None
      etd: date | None = None
      eta_destination: date | None = None
      next_port: str | None = None
      remark: str | None = None
      cargo_weight: float | None = None
      cargo_desc: str | None = None

class releaseOrderPatch(BaseModel):
      liner_ref: str | None = None
      empty_pickup: date | None = None
      validity_exp: date | None = None
      depot_name: str | None = None
      depot_addr: str | None = None
      vessel_cutoff: date | None = None
      etd: date | None = None
      eta_destination: date | None = None
      next_port: str | None = None
      remark: str | None = None
      cargo_weight: float | None = None
      cargo_desc: str | None = None
