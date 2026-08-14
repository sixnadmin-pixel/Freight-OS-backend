import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from modules.authen.jwt_service import decode_token, employee_from_token
from modules.authen.context import set_current_employee

# In-memory blacklist (swap for Redis later)
_blacklisted_jtis: set[str] = set()

PUBLIC_PATHS = frozenset({"/auth/login", "/auth/callback", "/auth/refresh", "/docs", "/openapi.json", "/"})


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response("Unauthorized", status_code=401)

        token = auth_header[7:]

        try:
            payload = decode_token(token)

            jti = payload.get("jti")
            if jti and jti in _blacklisted_jtis:
                return Response("Token revoked", status_code=401)

            employee = employee_from_token(payload)
            set_current_employee(employee)

        except jwt.ExpiredSignatureError:
            return Response("Token expired", status_code=401)
        except jwt.InvalidTokenError:
            return Response("Invalid token", status_code=401)

        return await call_next(request)