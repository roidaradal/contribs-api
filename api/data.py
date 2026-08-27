import os
from pydantic import BaseModel
from typing import Optional

OK_MESSAGE = 'OK'

class ActionResult(BaseModel):
    success: bool = True 
    message: str = OK_MESSAGE

class DataResult[T](BaseModel):
    data: Optional[T] = None 
    message: str = OK_MESSAGE

def get_cors_list() -> list[str]:
    '''Get list of origins allowed for CORS policy'''
    cors = os.getenv('CORS_LIST') or ''
    return [x.strip() for x in cors.split(',')]
