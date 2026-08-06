from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router_ingestion import router as ingestion_router

app = FastAPI(title='Rouanet Concilia API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(ingestion_router, prefix='/api/v1')

@app.get('/')
def health_check():
    return {'status': 'ok', 'message': 'API Rouanet Concilia online.'}
