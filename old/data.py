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
