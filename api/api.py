import os, httpx, asyncio
from datetime import datetime
from pydantic import BaseModel 
from .github import REQUEST_TIMEOUT, Error

REPOS_URL: str = 'https://api.github.com/users/%s/repos' # username
LANGUAGES_URL: str = 'https://api.github.com/repos/%s/languages'

class Repo(BaseModel):
    name: str = ''
    full_name: str = ''
    description: str|None = None
    size_kb: int = 0
    size: str = ''

class ReposList(BaseModel):
    repos: list[Repo] = []
    count: int = 0

class DevLanguages(BaseModel):
    languages: dict[str, tuple[str, float]] = {}
    count: int = 0 
    total_bytes: str = ''

class Result:
    def __init__(self, repo: str, languages: dict[str,int], error: Error):
        self.repo = repo 
        self.languages = languages 
        self.error = error

REPOS_CACHE: dict[str, tuple[datetime, ReposList]] = {} # username => (time_saved, ReposList)

def get_github_api_headers() -> dict[str,str]:
    '''GitHub API headers'''
    token = os.getenv('GITHUB_API_TOKEN') or ''
    return {
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'Accept': 'application/vnd.github+json',
    }

def is_valid_cache_entry(time_saved: datetime) -> bool:
    '''Check if time saved is still fresh based on cache TTL'''
    cache_age_hours = (datetime.now() - time_saved).total_seconds() / (60 * 60) 
    return cache_age_hours < get_repos_cache_ttl_hours()

def get_repos_cache_ttl_hours() -> int:
    '''Get repos cache TTL in hours'''
    try:
        ttl = int(os.getenv('REPOS_CACHE_TTL_HOURS') or '48')
        return max(1, ttl) # floor cache TTL = 1 hour
    except:
        return 48 # default cache TTL

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
        headers: dict[str,str] = get_github_api_headers()
        async with httpx.AsyncClient() as client:
            print('Fetching user %s repos...' % dev)
            repos: list[Repo] = []

            while url != '':
                response = await client.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
                repos += [Repo(  name = repo['name'],
                                full_name = repo['full_name'],
                                description = repo['description'],
                                size_kb = repo['size'],
                                size = string_bytes(int(repo['size']) * 1024),
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
    '''Fetch repo languages'''
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
    
async def get_dev_languages(dev: str, force: bool) -> tuple[DevLanguages, Error]:
    data, error = await get_dev_repos(dev, force)
    if error.has:
        return DevLanguages(), error
    
    total: dict[str, int] = {}
    # for repo in data.repos:
    #     for language, size in repo.languages.items():
    #         total.setdefault(language, 0)
    #         total[language] += size
    dev_total = sum(total.values())
    languages: dict[str, tuple[str,float]] = {}
    # for language, language_size in total.items():
    #     size = string_bytes(language_size)
    #     ratio = float(language_size) / dev_total
    #     ratio = float('%.4f' % ratio)
    #     languages[language] = (size, ratio)

    return DevLanguages(languages = languages, count = len(languages), total_bytes = string_bytes(dev_total)), Error()


def string_bytes(num_bytes: int) -> str:
    '''Convert num_bytes to human-readable size'''
    B = float(num_bytes)
    KB = float(1024)
    MB = float(KB ** 2)
    GB = float(KB ** 3)

    if B < KB:
        return '{0} B'.format(B)
    elif KB <= B < MB:
        return '{0:.1f} KB'.format(B / KB)
    elif MB <= B < GB:
        return '{0:.1f} MB'.format(B / MB)
    else:
        return '{0:.1f} GB'.format(B / GB)

'''
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
'''