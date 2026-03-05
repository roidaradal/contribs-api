from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .data import ActionResult, DataResult, new_date, get_devs, get_dev_limit, get_cors_list
from .github import get_devs_contribs
from .api import get_dev_repos, get_devs_repos, get_repo_languages, get_dev_languages

CURRENT_VERSION = '0.1.1'
IS_PROD_ENV = True # Note: change to True before deploy

if not IS_PROD_ENV:
    from dotenv import load_dotenv
    load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_list(),
    allow_methods=['GET'],
    allow_headers=['*'],
)

@app.get('/')
async def health_check() -> ActionResult:
    return ActionResult(success=True, message='OK')

@app.get('/version')
async def get_version() -> DataResult:
    return DataResult(data = {'version': CURRENT_VERSION})

@app.get('/contribs/{date_string}')
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

@app.get('/devs/repos')
async def get_devs_repos_data(devs: str = '', force: bool= False) -> DataResult:
    devs_list = get_devs(devs)
    num_devs = len(devs_list)
    dev_limit = get_dev_limit()
    if num_devs == 0:
        return DataResult(data=None, message='Empty devs list')
    elif num_devs > dev_limit:
        return DataResult(data=None, message=f'Devs list exceeds limit: {dev_limit}')
    
    devs_repos, err = await get_devs_repos(devs_list, force)
    if err.has:
        return DataResult(data=None, message=err.message)
    return DataResult(data = devs_repos)

@app.get('/devs/list/{devs}')
async def get_devs_data(devs: str) -> DataResult:
    devs_list = get_devs(devs)
    return DataResult(data = devs_list)


@app.get('/repos/{dev}')
async def get_dev_repos_data(dev: str, force: bool = False) -> DataResult:
    dev_repos, err = await get_dev_repos(dev, force)
    if err.has:
        return DataResult(data=None, message=err.message)
    return DataResult(data = dev_repos)

@app.get('/repo/{dev}/{repo}/languages')
async def get_repo_languages_data(dev: str, repo: str, force: bool=False) -> DataResult:
    languages, err = await get_repo_languages(f'{dev}/{repo}', force)
    if err.has:
        return DataResult(data=None, message=err.message)
    return DataResult(data = languages)
    
@app.get('/languages/{dev}')
async def get_dev_languages_data(dev: str, force: bool = False) -> DataResult:
    dev_languages, err = await get_dev_languages(dev, force)
    if err.has:
        return DataResult(data=None, message=err.message)
    return DataResult(data = dev_languages)