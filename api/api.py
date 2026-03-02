import httpx
from datetime import datetime
from pydantic import BaseModel 
from .github import REQUEST_TIMEOUT, Error, is_valid_cache_entry

REPOS_URL: str = 'https://api.github.com/users/%s/repos' # username

class Repo(BaseModel):
    name: str = ''
    full_name: str = ''
    description: str|None = None

class ReposList(BaseModel):
    repos: list[Repo] = []
    count: int = 0

REPOS_CACHE: dict[str, tuple[datetime, ReposList]] = {} # username => (time_saved, ReposList)

async def get_dev_repos(dev: str, force: bool) -> tuple[ReposList, Error]:
    '''Fetch dev's list of repos'''
    url = REPOS_URL % dev 
    
    #Check cache first, if not force fetch
    if dev in REPOS_CACHE and not force:
        time_saved, reposList = REPOS_CACHE[dev]
        if is_valid_cache_entry(time_saved):
            # Used cached value if still fresh
            print('Dev repos:', dev, 'cache') 
            return reposList, Error()
        
    try:
        async with httpx.AsyncClient() as client:
            print('Fetching user %s repos...' % dev)
            response = await client.get(url, timeout=REQUEST_TIMEOUT)
            repos = [Repo(  name = repo['name'],
                            full_name = repo['full_name'],
                            description = repo['description'],
                        ) 
                        for repo in response.json()
                    ]
            print('Dev repos:', dev, 'fresh')
            reposList = ReposList(repos = repos, count = len(repos))
            # Add to cache 
            REPOS_CACHE[dev] = (datetime.now(), reposList)
            return reposList, Error()
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return ReposList(), error
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return ReposList(), error
    except Exception as e:
        error = Error(message = f'Unexpected error occurred: {e}')
        return ReposList(), error
