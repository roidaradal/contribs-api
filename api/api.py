import httpx
from typing import Any
from pydantic import BaseModel 
from .github import REQUEST_TIMEOUT, Error

REPOS_URL: str = 'https://api.github.com/users/%s/repos' # username

class Repo(BaseModel):
    name: str = ''
    full_name: str = ''
    description: str|None = None

class ReposList(BaseModel):
    repos: list[Repo] = []
    count: int = 0

async def get_dev_repos(dev: str) -> tuple[ReposList, Error]:
    '''Fetch dev's list of repos'''
    url = REPOS_URL % dev 
    try:
        async with httpx.AsyncClient() as client:
            print('Fetching user %s repos...' % dev)
            response = await client.get(url, timeout=REQUEST_TIMEOUT)
            repos: list[Repo] = [create_repo(repo) for repo in response.json()]
            return ReposList(repos = repos, count = len(repos)), Error()
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return ReposList(), error
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return ReposList(), error
    except Exception as e:
        error = Error(message = f'Unexpected error occurred: {e}')
        return ReposList(), error

def create_repo(d: Any) -> Repo:
    '''Extracts relevant repo information from API response'''
    return Repo(
        name = d['name'],
        full_name = d['full_name'],
        description= d['description'],
    )
