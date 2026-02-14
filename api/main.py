from fastapi import FastAPI
from .data import ActionResult, DataResult, new_date, get_devs, get_dev_limit
from .github import get_devs_contribs

CURRENT_VERSION = '0.1.0'
IS_PROD_ENV = True # Note: change to True before deploy

if not IS_PROD_ENV:
    from dotenv import load_dotenv
    load_dotenv()

app = FastAPI()

@app.get('/')
async def health_check() -> ActionResult:
    return ActionResult(success=True, message='OK')

@app.get('/version')
async def get_version() -> DataResult:
    return DataResult(data = {'version': CURRENT_VERSION})

@app.get('/{date_string}')
async def get_month_data(date_string: str = 'today', devs: str = '', force: bool = False) -> DataResult:
    input_date = new_date(date_string)
    devs_list = get_devs(devs)
    num_devs = len(devs_list)
    dev_limit = get_dev_limit()
    if num_devs == 0:
        return DataResult(data=None, message='Empty devs list')
    elif num_devs > dev_limit:
        return DataResult(data=None, message=f'Devs list exceeds limit: {dev_limit}')
    
    dev_contribs, err = await get_devs_contribs(devs_list, input_date, force)
    if err.has:
        return DataResult(data=None, message=err.message)
    
    return DataResult(data = {
        'date' : input_date,
        'contribs': dev_contribs,
    })
