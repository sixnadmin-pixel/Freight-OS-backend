from pydantic import BaseModel

class LinerNew(BaseModel):
    name : str 
    has_portal : bool = False
    is_on_intra: bool = False