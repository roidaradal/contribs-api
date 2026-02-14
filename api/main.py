from fastapi import FastAPI 
from data import *
from github import get_devs_contributions

IS_PROD_ENV = False # Note: change to True before deploy
DEV_LIMIT = 9

if not IS_PROD_ENV:
    from dotenv import load_dotenv
    load_dotenv()

app = FastAPI()

@app.get('/')
async def health_check() -> ActionResult:
    return ActionResult(success=True, message='OK')

@app.get('/{date_string}')
async def get_month_data(date_string: str = 'today', devs: str = ''):
    input_date: date = new_date(date_string)
    devs_list: list[str] = get_devs(devs)
    num_devs = len(devs_list)
    if num_devs == 0:
        return DataResult(data=None, message='Empty devs list')
    elif num_devs > DEV_LIMIT:
        return DataResult(data=None, message=f'Devs list exceeds limit: {DEV_LIMIT}')
    
    dev_contribs = await get_devs_contributions(devs_list, input_date)
    return DataResult(data = {
        'date' : input_date,
        'contribs': dev_contribs,
    })

'''
TODO:
- Fetch GitHub contributions
- Hash the devs list and cache results for 1 hr 
- Add force flag to force re-fetching of GitHub contribs
'''