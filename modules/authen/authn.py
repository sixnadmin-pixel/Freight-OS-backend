import json
from fastapi import HTTPException
from pathlib import Path
from modules.authen.context import get_current_employee
from modules.authen.api import IAuthnModule
from modules.authen.employee_types import Employee

class AuthnModule(IAuthnModule):
    def get_current_user(self) -> Employee:
        employee = get_current_employee()
        if not employee:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return employee


