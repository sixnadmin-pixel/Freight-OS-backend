from typing import Optional
from pydantic import BaseModel


class Employee(BaseModel):
    emp_id: int
    name: str
    desig: Optional[str] = None
    dept: str
    mail_id: Optional[str] = None
