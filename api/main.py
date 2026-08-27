from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .data import ActionResult, DataResult, get_cors_list

CURRENT_VERSION = '0.2.0'
IS_PROD_ENV = False # Note: Change to True before deployment

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

