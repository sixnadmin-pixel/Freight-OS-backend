from fastapi import APIRouter, Depends

from modules.authen.api import IAuthnModule

router = APIRouter(prefix='/auth', tags=['Authentication'])

def get_authn_module() -> IAuthnModule:
    raise NotImplementedError("This must be overridden at the app composition root (main.py)")


@router.get("/me")
def get_current_user(service: IAuthnModule = Depends(get_authn_module)):
    return service.get_current_user()


@router.post("/switch-user/{emp_id}")
def switch_user(emp_id: int, service: IAuthnModule = Depends(get_authn_module)):
    return service.set_current_user(emp_id)
