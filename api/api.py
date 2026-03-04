import os, httpx, asyncio
from datetime import datetime
from pydantic import BaseModel 
from .github import REQUEST_TIMEOUT, Error, is_valid_cache_entry

REPOS_URL: str = 'https://api.github.com/users/%s/repos' # username
LANGUAGES_URL: str = 'https://api.github.com/repos/%s/languages'

class Repo(BaseModel):
    name: str = ''
    full_name: str = ''
    description: str|None = None
    size_kb: int = 0
    languages: dict[str, int] = {}

class ReposList(BaseModel):
    repos: list[Repo] = []
    count: int = 0

class Result:
    def __init__(self, repo: str, languages: dict[str,int], error: Error):
        self.repo = repo 
        self.languages = languages 
        self.error = error

REPOS_CACHE: dict[str, tuple[datetime, ReposList]] = {} # username => (time_saved, ReposList)

def get_github_api_token() -> str:
    return os.getenv('GITHUB_API_TOKEN') or ''

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
        headers: dict[str,str] = {
            'Authorization': f'Bearer {get_github_api_token()}',
            'X-GitHub-Api-Version': '2022-11-28',
            'Accept': 'application/vnd.github+json',
        }
        async with httpx.AsyncClient() as client:
            print('Fetching user %s repos...' % dev)
            repos: list[Repo] = []

            while url != '':
                response = await client.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
                repos += [Repo(  name = repo['name'],
                                full_name = repo['full_name'],
                                description = repo['description'],
                                size_kb = repo['size'],
                            ) 
                            for repo in response.json()
                        ]
                link = str(response.headers.get('Link', '')) 
                if link != '':
                    next_link = [part.strip() for part in link.split(',') if part.strip().endswith('; rel="next"')]
                    if len(next_link) == 1:
                        link = next_link[0].split(';')[0].strip('<>')
                    else:
                        break
                url = link
            
            print('Dev repos:', dev, 'fresh')

            # Fetch languages of repos in parallel
            tasks = [get_repo_languages(repo.full_name, headers, client) for repo in repos]
            results = await asyncio.gather(*tasks)
            repo_languages: dict[str, dict[str,int]] = {}
            for r in results:
                if r.error.has:
                    print(r.repo, r.error) 
                    continue 
                repo_languages[r.repo] = r.languages
            for repo in repos:
                if repo.full_name not in repo_languages: continue 
                repo.languages = repo_languages[repo.full_name]
            print('Repo languages: OK')

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

async def get_repo_languages(repo: str, headers: dict[str,str], client: httpx.AsyncClient) -> Result:
    url = LANGUAGES_URL % repo 
    try: 
        response = await client.get(url, timeout=REQUEST_TIMEOUT, headers = headers)
        languages: dict[str, int] = response.json()
        return Result(repo, languages, Error())
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return Result(repo, {}, error)
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return Result(repo, {}, error)
    except Exception as e:
        error = Error(message = f'Unexpected error occurred: {e}')
        return Result(repo, {}, error)