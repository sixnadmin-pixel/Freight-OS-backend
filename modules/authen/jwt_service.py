import jwt, uuid
from datetime import datetime, timedelta, timezone
from  modules.authen.employee_types import Employee
from modules.authen import config

ALGORITHM = 'HS256'

def create_access_token(employee: Employee) -> str:
    jti=str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload = {
        "sub": str(employee.emp_id),
        "mail_id": str(employee.mail_id),
        "name": str(employee.name),
        "dept": str(employee.dept),
        "desig": str(employee.desig),
        "exp": expires,
        "jti":jti
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(employee: Employee) -> tuple[str, str]:
    jti=str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "sub": str(employee.emp_id),
        "type": "refresh",
        "exp": expires,
        "jti": jti
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)
    return token, jti

def decode_token(token: str) -> dict:
    return jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])

def employee_from_token(payload: dict) -> Employee:
    # Reconstruct a partial Employee object from the JWT claims 
    # to avoid a DB hit on every request.
    return Employee(
        emp_id=int(payload["sub"]),
        mail_id=payload.get("mail_id"),
        name=payload.get("name"),
        dept=payload.get("dept")
    )