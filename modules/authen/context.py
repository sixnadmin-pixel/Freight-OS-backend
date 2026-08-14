from contextvars import ContextVar
from typing import Optional
from modules.authen.employee_types import Employee

_current_employee_ctx: ContextVar[Optional[Employee]] = ContextVar("current_employee", default=None)

def set_current_employee(employee: Employee) -> None:
    _current_employee_ctx.set(employee)

def get_current_employee() -> Optional[Employee]:
    return _current_employee_ctx.get()