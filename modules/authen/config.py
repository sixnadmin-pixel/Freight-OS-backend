import os
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID", "common")
CLIENT_ID = os.getenv("APP_CLIENT_ID")
CLIENT_SECRET = os.getenv("APP_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-default-key")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:6002")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8002")

AUTH_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
