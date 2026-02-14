import asyncio, calendar, httpx, os
from bs4 import BeautifulSoup
from datetime import date, datetime
from pydantic import BaseModel, model_serializer

HTML_URL: str = 'https://github.com/users/%s/contributions?from=%s' # (username, start_date)

class Contrib(BaseModel):
    count: int = 0
    level: int = 0

    @model_serializer
    def serialize_contrib(self) -> tuple[int, int]:
        return (self.count, self.level)

MonthContribs = dict[str, Contrib]      # day => Contrib 
DevContribs = dict[str, MonthContribs]  # dev => MonthContribs

class Error(BaseModel):
    message: str = ''

    @property 
    def has(self) -> bool:
        return self.message != ''
    
    @model_serializer
    def serialize_error(self) -> str:
        return self.message

class Result:
    def __init__(self, dev: str, contribs: MonthContribs, is_fresh: bool, error: Error):
        self.dev = dev 
        self.contribs = contribs 
        self.is_fresh = is_fresh 
        self.error = error

CACHE: dict[str, tuple[datetime, MonthContribs]] = {}   # username.month.year => (time_saved, MonthContribs)

def get_cache_ttl_mins() -> int:
    '''Get cache TTL in minutes'''
    try:
        ttl = int(os.getenv('CACHE_TTL_MINS') or '60')
        return max(1, ttl) # floor cache TTL = 1 minute
    except:
        return 60 # default cache TTL

async def get_devs_contribs(devs: list[str], input_date: date, force: bool) -> tuple[DevContribs, Error]:
    '''Fetch each dev's contributions for the month'''
    dev_contribs: DevContribs = {}
    async with httpx.AsyncClient() as client:
        print('Fetching dev contributions...')
        tasks = [fetch_dev_contribs(dev, input_date, force, client) for dev in devs]
        results = await asyncio.gather(*tasks)
        for r in results:
            if r.error.has: return {}, r.error
            dev_contribs[r.dev] = r.contribs
            total = sum(x.count for x in r.contribs.values())
            print(r.dev, total, 'fresh' if r.is_fresh else 'cache')
    return dev_contribs, Error()

async def fetch_dev_contribs(dev: str, input_date: date, force: bool, client: httpx.AsyncClient) -> Result:
    '''Fetch dev contributions for the month'''
    year, month = input_date.year, input_date.month
    cache_key = '%s.%d.%d' % (dev.lower(), month, year)

    # Check cache first, if not force fetch
    if cache_key in CACHE and not force:
        time_saved, contribs = CACHE[cache_key]
        cache_age_mins = (datetime.now() - time_saved).total_seconds() / 60
        if cache_age_mins < get_cache_ttl_mins():
            # Use cached value if still fresh
            return Result(dev, contribs, False, Error())

    # Fetch HTML page and use BeautifulSoup 
    year_start = date(year, 1, 1) # January 1 of given year
    url = HTML_URL % (dev, str(year_start))
    try:
        response = await client.get(url, timeout=10.0)
        soup = BeautifulSoup(response.text, 'html.parser')
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return Result(dev, {}, False, error)
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return Result(dev, {}, False, error)
    
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

    # Add to cache 
    CACHE[cache_key] = (datetime.now(), contribs)
    return Result(dev, contribs, True, Error())
