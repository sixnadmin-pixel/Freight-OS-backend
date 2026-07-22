from pydantic import BaseModel


class Employee(BaseModel):
    emp_id: int
    name: str
    desig: str
    dept: str
