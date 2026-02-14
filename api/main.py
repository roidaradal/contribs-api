import asyncio, calendar, httpx, os
from bs4 import BeautifulSoup
from datetime import date
from fastapi import FastAPI 
from pydantic import BaseModel, model_serializer
from typing import Optional

IS_PROD_ENV = True # Note: change to True before deploy
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
    
    dev_contribs, err = await get_devs_contribs(devs_list, input_date)
    if err.has:
        return DataResult(data=None, message=err.message)
    
    return DataResult(data = {
        'date' : input_date,
        'contribs': dev_contribs,
    })

############################## DATA FUNCTIONS #######################################

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

############################## GITHUB FUNCTIONS #######################################

HTML_URL: str = 'https://github.com/users/%s/contributions?from=%s' # (username, start_date)

class Contrib(BaseModel):
    count: int = 0
    level: int = 0

    @model_serializer
    def serialize_contrib(self) -> tuple[int, int]:
        return (self.count, self.level)

class Error(BaseModel):
    message: str = ''

    @property 
    def has(self) -> bool:
        return self.message != ''
    
    @model_serializer
    def serialize_error(self) -> str:
        return self.message

MonthContribs = dict[str, Contrib]      # day => Contrib 
DevContribs = dict[str, MonthContribs]  # dev => MonthContribs

async def get_devs_contribs(devs: list[str], input_date: date) -> tuple[DevContribs, Error]:
    '''Fetch each dev's contributions for the month'''
    dev_contribs: DevContribs = {}
    async with httpx.AsyncClient() as client:
        print('Fetching dev contributions...')
        tasks = [fetch_dev_contribs(dev, input_date, client) for dev in devs]
        results = await asyncio.gather(*tasks)
        for dev, contribs, err in results:
            if err.has: return {}, err 
            dev_contribs[dev] = contribs
            total = sum(x.count for x in contribs.values())
            print(dev, total)
    return dev_contribs, Error()

async def fetch_dev_contribs(dev: str, input_date: date, client: httpx.AsyncClient) -> tuple[str, MonthContribs, Error]:
    '''Fetch dev contributions for the month'''
    year, month = input_date.year, input_date.month
    year_start = date(year, 1, 1) # January 1 of given year
    url = HTML_URL % (dev, str(year_start))

    # Fetch HTML page and use BeautifulSoup 
    try:
        response = await client.get(url, timeout=10.0)
        soup = BeautifulSoup(response.text, 'html.parser')
    except httpx.HTTPStatusError as e:
        return dev, {}, Error(message = f'Status Error: {e.response.status_code}')
    except httpx.RequestError as e:
        return dev, {}, Error(message = f'Request Error: {e}')
    
    # Setup month date range 
    last_month_day = calendar.monthrange(year, month)[1]
    month_start = str(date(year, month, 1))
    month_end   = str(date(year, month, last_month_day))

    # Get contributions data
    contribs: MonthContribs = {}
    for cell in soup.select('td.ContributionCalendar-day'):
        cell_date = str(cell['data-date'])
        if not (month_start <= cell_date <= month_end): continue # skip if not within month range
        day = int(cell_date.split('-')[2], 10)

        # Find tooltip associated with td cell 
        tooltip = soup.find('tool-tip', attrs={'for': cell['id']})

        # Extract count from tooltip's inner text 
        text = 'No' # default: No contributions 
        if tooltip: text = tooltip.get_text()

        count_text = text.strip().split()[0]
        count = 0 if count_text == 'No' else int(count_text)
        level = int(str(cell['data-level']))
        contribs[str(day)] = Contrib(count = count, level = level)

    return dev, contribs, Error()

'''
TODO:
- Hash the devs list and cache results for 1 hr 
- Add force flag to force re-fetching of GitHub contribs
'''