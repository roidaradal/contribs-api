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

class LanguageStats(BaseModel):
    num_bytes: int = 0
    size: str = ''
    ratio: float = 0.0

LanguageInfo = dict[str, LanguageStats]

class DevLanguages(BaseModel):
    languages: LanguageInfo = {}
    count: int = 0 
    total_bytes: str = ''

class RepoResult:
    def __init__(self, dev: str, repos: ReposList, error: Error):
        self.dev = dev 
        self.data = repos 
        self.error = error

class LanguageResult:
    def __init__(self, repo: str, languages: LanguageInfo, error: Error):
        self.repo = repo 
        self.languages = languages 
        self.error = error


REPOS_CACHE: dict[str, tuple[datetime, ReposList]] = {} # username => (time_saved, ReposList)
LANGS_CACHE: dict[str, tuple[datetime, LanguageInfo]] = {} # repo_name => (time_saved, LanguageInfo)

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
    '''Get dev repos'''
    headers = get_github_api_headers()
    async with httpx.AsyncClient() as client:
        result = await fetch_dev_repos(dev, force, headers, client)
        return result.data, result.error

async def fetch_dev_repos(dev: str, force: bool, headers: dict[str, str], client: httpx.AsyncClient) -> RepoResult:
    '''Fetch dev's list of repos'''
    url = REPOS_URL % dev 
    
    # Check cache first, if not force fetch
    if dev in REPOS_CACHE and not force:
        time_saved, repos_list = REPOS_CACHE[dev]
        if is_valid_cache_entry(time_saved):
            # Used cached value if still fresh
            print('Dev repos:', dev, 'cache') 
            return RepoResult(dev, repos_list, Error())
        
    try:
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
        repos_list = ReposList(repos = repos, count = len(repos))
        # Add to cache 
        REPOS_CACHE[dev] = (datetime.now(), repos_list)
        return RepoResult(dev, repos_list, Error())
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return RepoResult(dev, ReposList(), error)
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return RepoResult(dev, ReposList(), error)
    except Exception as e:
        error = Error(message = f'Unexpected error occurred: {e}')
        return RepoResult(dev, ReposList(), error)

async def get_repo_languages(repo: str, force: bool) -> tuple[LanguageInfo, Error]:
    '''Get repo languages'''
    headers = get_github_api_headers()
    async with httpx.AsyncClient() as client:
        result = await fetch_repo_languages(repo, force, headers, client)
        return result.languages, result.error

async def fetch_repo_languages(repo: str, force: bool, headers: dict[str,str], client: httpx.AsyncClient) -> LanguageResult:
    '''Fetch repo languages from cache or from GitHub API'''
    url = LANGUAGES_URL % repo 

    # Check cache first, if not force 
    if repo in LANGS_CACHE and not force:
        time_saved, languages = LANGS_CACHE[repo]
        if is_valid_cache_entry(time_saved):
            # Used cached value if still fresh 
            # print('Repo languages:', repo, 'cache')
            return LanguageResult(repo, languages, Error())
        
    try:
        # print('Fetching repo %s languages...' % repo) 
        response = await client.get(url, timeout=REQUEST_TIMEOUT, headers = headers)
        raw_languages: dict[str, int] = response.json()
        # print('Repo languages:', repo, 'fresh')
        languages: LanguageInfo = {}
        total = float(sum(raw_languages.values()))
        for key, num_bytes in raw_languages.items():
            languages[key] = LanguageStats(
                num_bytes = num_bytes,
                size = string_bytes(num_bytes),
                ratio = size_ratio(num_bytes, total)
            )
        # Add to cache 
        LANGS_CACHE[repo] = (datetime.now(), languages)
        return LanguageResult(repo, languages, Error())
    except httpx.HTTPStatusError as e:
        error = Error(message = f'Status Error: {e.response.status_code}')
        return LanguageResult(repo, {}, error)
    except httpx.RequestError as e:
        error = Error(message = f'Request Error: {e.request.url}')
        return LanguageResult(repo, {}, error)
    except Exception as e:
        error = Error(message = f'Unexpected error occurred: {e}')
        return LanguageResult(repo, {}, error)
    
async def get_dev_languages(dev: str, force: bool) -> tuple[DevLanguages, Error]:
    '''Get dev languages'''
    headers = get_github_api_headers()
    async with httpx.AsyncClient() as client:
        result = await fetch_dev_repos(dev, force, headers, client)
        if result.error.has:
            return DevLanguages(), result.error
        
        # Fetch languages of repos in parallel
        repos = result.data.repos
        tasks = [fetch_repo_languages(repo.full_name, force, headers, client) for repo in repos]
        results = await asyncio.gather(*tasks)
        repo_languages: dict[str, dict[str, int]] = {}
        for r in results:
            if r.error.has:
                print('Error:', r.repo, r.error)
                continue
            repo_languages[r.repo] = {k:v.num_bytes for k,v in r.languages.items()}
        
        total: dict[str, int] = {}
        for languages in repo_languages.values():
            for language, num_bytes in languages.items():
                total.setdefault(language, 0)
                total[language] += num_bytes
        dev_total = sum(total.values())
        dev_languages: LanguageInfo = {}
        for language, num_bytes in total.items():
            dev_languages[language] = LanguageStats(
                num_bytes = num_bytes,
                size = string_bytes(num_bytes),
                ratio = size_ratio(num_bytes, float(dev_total)),
            )
        output = DevLanguages(
            languages = dev_languages,
            count = len(dev_languages),
            total_bytes = string_bytes(dev_total),
        )
        return output, Error()

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
    
def size_ratio(num_bytes: int, total: float) -> float:
    '''Compute ratio then format to 4 decimal places'''
    ratio = '%.4f' % (num_bytes / total)
    return float(ratio)
