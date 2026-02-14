# contribs-api 

Web API for fetching GitHub contributions data, using FastAPI (Python)

## Running uvicorn 
```
cd api
uvicorn main:app --reload
```

## Rebasing dev to main 
```bash
git switch dev 
git fetch origin 
git rebase origin/main 
git push origin dev --force
```

## Merging main to dev 
```bash
git switch dev
git fetch origin
git merge origin/main 
git push origin dev
```