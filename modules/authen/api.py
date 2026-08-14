from typing import Protocol
from modules.authen.employee_types import Employee


class IAuthnModule(Protocol):
    def get_current_user(self) -> Employee: ...
