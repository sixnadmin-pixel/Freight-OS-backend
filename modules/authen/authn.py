import json
from pathlib import Path

from modules.authen.api import IAuthnModule
from modules.authen.employee_types import Employee

USER_FILE = Path(__file__).parent / "cur_user.json"

TEST_USERS = {
    5: {"emp_id": 5, "name": "procu-test", "desig": "exec", "dept": "procurement"},
    6: {"emp_id": 6, "name": "fin-test", "desig": "exec", "dept": "finance"},
    7: {"emp_id": 7, "name": "cs-test", "desig": "exec", "dept": "cusomer-service"},
    8: {"emp_id": 8, "name": "sales-test", "desig": "exec", "dept": "sales"},
}


class AuthnModule(IAuthnModule):
    def get_current_user(self) -> Employee:
        with open(USER_FILE, "r") as f:
            data = json.load(f)
        return Employee(**data)

    def set_current_user(self, emp_id: int) -> Employee:
        if emp_id not in TEST_USERS:
            raise ValueError(f"Unknown test user: {emp_id}. Valid ids: {list(TEST_USERS)}")
        with open(USER_FILE, "w") as f:
            json.dump(TEST_USERS[emp_id], f, indent=2)
        return Employee(**TEST_USERS[emp_id])
