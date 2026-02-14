from fastapi import FastAPI 
from dotenv import load_dotenv
from data import *

load_dotenv()
app = FastAPI()

@app.get('/')
async def health_check() -> ActionResult:
    return ActionResult(success=True, message='OK')

@app.get('/{date_string}')
async def get_month_data(date_string: str = 'today', devs: str = ''):
    input_date: date = new_date(date_string)
    devs_list: list[str] = get_devs(devs)
    return DataResult(data = {
        'date' : input_date,
        'devs' : devs_list,
    })

'''
TODO:
- Fetch GitHub contributions
'''