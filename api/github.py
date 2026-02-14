import asyncio, calendar, httpx
from bs4 import BeautifulSoup
from datetime import date
from pydantic import BaseModel, model_serializer

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
