import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.authen.middleware import JWTAuthMiddleware
from contextlib import asynccontextmanager

from data.dbconn import pool

from modules.inquiry.router import router as inquiry_router, get_inquiry_module, get_activity_log_module
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

from modules.liners.router import router as liners_router, get_liners_module
from modules.liners.liners import LinersModule

from modules.quotation.router import router as quotation_router, get_quotation_module
from modules.quotation.quotation import QuotationModule

from modules.authen.router import router as authn_router, get_authn_module
from modules.authen.authn import AuthnModule

from modules.inquiry.activity_log.activity_log import ActivityLogModule


@asynccontextmanager
async def lifespan(app:FastAPI):
   await pool.open()
   yield
   await pool.close()

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JWTAuthMiddleware)

# TODO research : should inquiry be allowed to create new client?
# when clinnt module is down what happens to inquiry????


# services
authn_service = AuthnModule()
activity_log_service = ActivityLogModule()
client_service = ClientModule(authn_service)
kyc_service = KYCModule(client_service, authn_service)
inquiry_service = InquiryModule(authn_service, activity_log_service, kyc_service)
rates_master_service = RatesMasterModule(authn_service)
rates_service = RatesModule(authn_service)
rate_request_service = RateRequestModule(authn_service, activity_log_service)
liners_service = LinersModule(authn_service)
quotation_service = QuotationModule(authn_service, activity_log_service)

app.dependency_overrides[get_inquiry_module] = lambda: inquiry_service
app.dependency_overrides[get_client_module] = lambda: client_service
app.dependency_overrides[get_rates_master_module] = lambda: rates_master_service
app.dependency_overrides[get_rates_module] = lambda: rates_service
app.dependency_overrides[get_rate_request_module] = lambda: rate_request_service
app.dependency_overrides[get_kyc_module] = lambda: kyc_service
app.dependency_overrides[get_liners_module] = lambda: liners_service
app.dependency_overrides[get_activity_log_module] = lambda: activity_log_service
app.dependency_overrides[get_quotation_module] = lambda: quotation_service
app.dependency_overrides[get_authn_module] = lambda: authn_service


# routers
app.include_router(inquiry_router)
app.include_router(client_router)
app.include_router(rates_router)
app.include_router(rate_requests_router)
app.include_router(kyc_router)
app.include_router(liners_router)
app.include_router(quotation_router)
app.include_router(authn_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

