import secrets
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from psycopg.rows import dict_row

from data.dbconn import pool
from modules.authen.api import IAuthnModule
from modules.authen import config
from modules.authen.employee_types import Employee
from modules.authen.jwt_service import (
    create_access_token, create_refresh_token, decode_token,
)
from modules.authen.oidc import (
    generate_pkce_pair, build_authorize_url, exchange_code_for_tokens,
)

router = APIRouter(prefix='/auth', tags=['Authentication'])

def get_authn_module() -> IAuthnModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


# --- In-memory stores (swap for Redis later) ---

_oidc_states: dict[str, dict] = {}       # state -> {code_verifier, redirect_uri}
_refresh_tokens: dict[str, dict] = {}     # jti -> {emp_id, expires_at}


# --- Request / Response models ---

class LoginResponse(BaseModel):
    auth_url: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str | None = None


# --- Endpoints ---

@router.get("/login")
async def login() -> LoginResponse:
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()
    redirect_uri = f"{config.BACKEND_URL}/auth/callback"

    _oidc_states[state] = {
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
    }

    auth_url = build_authorize_url(state, code_challenge, redirect_uri)
    return LoginResponse(auth_url=auth_url)


@router.get("/callback")
async def callback(code: str, state: str):
    # 1. Validate state
    oidc_data = _oidc_states.pop(state, None)
    if oidc_data is None:
        raise HTTPException(400, "Invalid or expired state parameter")

    code_verifier = oidc_data["code_verifier"]
    redirect_uri = oidc_data["redirect_uri"]

    # 2. Exchange code for Azure AD tokens
    try:
        azure_tokens = await exchange_code_for_tokens(code, code_verifier, redirect_uri)
    except Exception as e:
        raise HTTPException(502, f"Failed to exchange authorization code: {e}")

    # 3. Decode id_token (trusted — received from Azure AD token endpoint over HTTPS)
    id_token = azure_tokens.get("id_token")
    if not id_token:
        raise HTTPException(502, "No id_token in Azure AD response")

    claims = pyjwt.decode(id_token, options={"verify_signature": False})

    azure_oid = claims.get("oid")
    email = (claims.get("preferred_username") or claims.get("email", "")).lower()

    if not email and not azure_oid:
        raise HTTPException(502, "Azure AD did not return email or OID")

    # 4. Match to employee table
    employee = None
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Try azure_oid first (returning user)
            if azure_oid:
                await cur.execute(
                    "SELECT emp_id, name, desig, dept, mail_id FROM employee WHERE azure_oid = %s",
                    (azure_oid,),
                )
                row = await cur.fetchone()
                if row:
                    employee = Employee(**row)

            # Fallback: match by email (first-time login)
            if employee is None and email:
                await cur.execute(
                    "SELECT emp_id, name, desig, dept, mail_id FROM employee WHERE LOWER(mail_id) = %s",
                    (email,),
                )
                row = await cur.fetchone()
                if row:
                    employee = Employee(**row)
                    # Store azure_oid for future logins
                    if azure_oid:
                        await cur.execute(
                            "UPDATE employee SET azure_oid = %s WHERE emp_id = %s",
                            (azure_oid, employee.emp_id),
                        )

    if employee is None:
        raise HTTPException(403, f"No employee record found for {email}. Contact your administrator.")

    # 5. Issue backend JWTs
    access_token = create_access_token(employee)
    refresh_token, refresh_jti = create_refresh_token(employee)

    _refresh_tokens[refresh_jti] = {
        "emp_id": employee.emp_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }

    # 6. Redirect to SPA with tokens
    params = urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
    })
    return RedirectResponse(url=f"{config.FRONTEND_URL}/auth/callback?{params}", status_code=302)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expired")
    except pyjwt.PyJWTError:
        raise HTTPException(401, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")

    jti = payload.get("jti")
    if jti not in _refresh_tokens:
        raise HTTPException(401, "Refresh token has been revoked")

    # Look up employee from DB (in case their data changed)
    emp_id = int(payload["sub"])
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT emp_id, name, desig, dept, mail_id FROM employee WHERE emp_id = %s",
                (emp_id,),
            )
            row = await cur.fetchone()

    if row is None:
        _refresh_tokens.pop(jti, None)
        raise HTTPException(401, "Employee no longer exists")

    employee = Employee(**row)

    # Rotate: revoke old, issue new
    _refresh_tokens.pop(jti, None)
    new_access_token = create_access_token(employee)
    new_refresh_token, new_jti = create_refresh_token(employee)

    _refresh_tokens[new_jti] = {
        "emp_id": employee.emp_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=15 * 60,
    )


@router.get("/me")
async def get_current_user(service: IAuthnModule = Depends(get_authn_module)):
    return service.get_current_user()


@router.post("/logout")
async def logout(body: LogoutRequest):
    if body.refresh_token:
        try:
            payload = decode_token(body.refresh_token)
            jti = payload.get("jti")
            if jti:
                _refresh_tokens.pop(jti, None)
        except pyjwt.PyJWTError:
            pass

    return {"message": "Logged out successfully"}
