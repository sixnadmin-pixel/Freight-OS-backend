from fastapi import FastAPI
from contextlib import asynccontextmanager

from data.dbconn import pool

from modules.inquiry.router import router as inquiry_router, get_inquiry_module
from modules.inquiry.inquiry import InquiryModule

from modules.client.router import router as client_router, get_client_module
from modules.client.client import ClientModule

from modules.rates.router import router as rates_router, get_rates_master_module, get_rates_module
from modules.rates.rates_master.master_rates import RatesMasterModule
from modules.rates.rates.rates import RatesModule

from modules.rate_requests.router import router as rate_requests_router, get_rate_request_module
from modules.rate_requests.rate_requests import RateRequestModule

from modules.kyc.router import router as kyc_router, get_kyc_module
from modules.kyc.client_kyc import KYCModule


@asynccontextmanager
async def lifespan(app:FastAPI):
   await pool.open()
   yield
   await pool.close()

app = FastAPI(lifespan=lifespan)


# services
inquiry_service = InquiryModule()
client_service = ClientModule()
rates_master_service = RatesMasterModule()
rates_service = RatesModule()
rate_request_service = RateRequestModule()
kyc_service = KYCModule()

app.dependency_overrides[get_inquiry_module] = lambda: inquiry_service
app.dependency_overrides[get_client_module] = lambda: client_service
app.dependency_overrides[get_rates_master_module] = lambda: rates_master_service
app.dependency_overrides[get_rates_module] = lambda: rates_service
app.dependency_overrides[get_rate_request_module] = lambda: rate_request_service
app.dependency_overrides[get_kyc_module] = lambda: kyc_service


# routers
app.include_router(inquiry_router)
app.include_router(client_router)
app.include_router(rates_router)
app.include_router(rate_requests_router)
app.include_router(kyc_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

