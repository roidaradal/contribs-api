import os
from datetime import date

std_date_format = '%Y-%m-%d'
    

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

def get_dev_limit() -> int:
    '''Get limit for number of devs'''
    try:
        limit = int(os.getenv('DEV_LIMIT') or '9')
        return max(1, limit) # floor dev limit = 1
    except:
        return 9 # default limit
