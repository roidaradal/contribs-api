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

def get_devs(devs: str) -> list[str]:
    '''Get list of devs from the input string'''
    if devs == '@goodapps':
        devs = os.getenv('GOODAPPS_DEVS') or ''
    if devs == '':
        return []
    return [x.strip() for x in devs.split(',')]

def get_dev_limit() -> int:
    ''' Get limit for number of devs'''
    try:
        limit = int(os.getenv('DEV_LIMIT') or '9')
        return max(1, limit) # floor dev limit = 1
    except:
        return 9 # default limit
