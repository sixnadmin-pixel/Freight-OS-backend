import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from modules.authen.jwt_service import decode_token, employee_from_token
from modules.authen.context import set_current_employee
from modules.authen.employee_types import Employee

# In-memory blacklist (swap for Redis later)
_blacklisted_jtis: set[str] = set()

PUBLIC_PATHS = frozenset({"/auth/login", "/auth/callback", "/auth/refresh", "/docs", "/openapi.json", "/"})

# ──────────────────────────────────────────────────────────────
# UNSECURE-TEST MODE: bypass all authentication.
# Every request gets a dummy employee so downstream services
# that call get_current_user() keep working.
# TODO: remove before merging to master
# ──────────────────────────────────────────────────────────────
_DUMMY_EMPLOYEE = Employee(
    emp_id=7,
    name="Test User",
    desig="Developer",
    dept="customer-service",
    mail_id="test@freightos.local",
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # In unsecure-test mode, skip JWT validation entirely.
        # If a valid Bearer token is present, honour it; otherwise
        # fall back to the dummy employee.
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                jti = payload.get("jti")
                if not (jti and jti in _blacklisted_jtis):
                    employee = employee_from_token(payload)
                    set_current_employee(employee)
                    return await call_next(request)
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass  # fall through to dummy employee

        set_current_employee(_DUMMY_EMPLOYEE)
        return await call_next(request)