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
    today = date.today()
    if date_string.lower() == 'today':
        return today 
    try:
        return date.strptime(date_string, std_date_format)
    except:
        return today

def date_format(d: date) -> str:
    return d.strftime(std_date_format)