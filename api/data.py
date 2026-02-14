import os
from datetime import date
from pydantic import BaseModel
from typing import Optional

okMessage = 'OK'
std_date_format = '%Y-%m-%d'
    
class ActionResult(BaseModel):
    success: bool = True 
    message: str = okMessage

class DataResult[T](BaseModel):
    data: Optional[T] = None
    message: str = okMessage

def new_date(date_string: str) -> date:
    '''Parse date_string as date, defaults to date today if invalid date'''
    today = date.today()
    if date_string.lower() == 'today':
        return today 
    try:
        return date.strptime(date_string, std_date_format)
    except:
        return today

def date_format(d: date) -> str:
    '''String representation of date object in standard format'''
    return d.strftime(std_date_format)

def get_devs(devs: str) -> list[str]:
    '''Get list of devs from the input string'''
    devs = devs.strip()
    if devs == '@goodapps':
        devs = os.getenv('GOODAPPS_DEVS') or ''
    if devs == '':
        return []
    return [x.strip() for x in devs.split(',')]
