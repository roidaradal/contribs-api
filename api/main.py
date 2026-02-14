import data, github
from fastapi import FastAPI 

IS_PROD_ENV = False # Note: change to True before deploy

if not IS_PROD_ENV:
    from dotenv import load_dotenv
    load_dotenv()

app = FastAPI()

@app.get('/')
async def health_check() -> data.ActionResult:
    return data.ActionResult(success=True, message='OK')

@app.get('/{date_string}')
async def get_month_data(date_string: str = 'today', devs: str = '', force: bool = False):
    input_date = data.new_date(date_string)
    devs_list = data.get_devs(devs)
    num_devs = len(devs_list)
    dev_limit = data.get_dev_limit()
    if num_devs == 0:
        return data.DataResult(data=None, message='Empty devs list')
    elif num_devs > dev_limit:
        return data.DataResult(data=None, message=f'Devs list exceeds limit: {dev_limit}')
    
    dev_contribs, err = await github.get_devs_contribs(devs_list, input_date, force)
    if err.has:
        return data.DataResult(data=None, message=err.message)
    
    return data.DataResult(data = {
        'date' : input_date,
        'contribs': dev_contribs,
    })
