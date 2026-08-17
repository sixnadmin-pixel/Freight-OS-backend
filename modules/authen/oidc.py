import secrets
import hashlib
import base64
import httpx
from urllib.parse import urlencode
from modules.authen import config

def generate_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode('ascii').rstrip('=')
    return code_verifier, code_challenge

def build_authorize_url(state: str, code_challenge: str, redirect_uri: str) -> str:
    params = {
        "client_id": config.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": f"api://{config.CLIENT_ID}/FreightSSO openid profile email",
        "response_mode": "query",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    return f"{config.AUTH_ENDPOINT}?{urlencode(params)}"

async def exchange_code_for_tokens(code: str, code_verifier: str, redirect_uri: str) -> dict:
    data = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(config.TOKEN_ENDPOINT, data=data)
        response.raise_for_status()
        return response.json()