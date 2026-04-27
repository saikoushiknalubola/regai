from fastapi import APIRouter
from app.api.v1 import anonymisation, summarisation, completeness, classification, documents

api_router = APIRouter()

api_router.include_router(anonymisation.router, prefix="/anonymise", tags=["Anonymisation"])
api_router.include_router(summarisation.router, prefix="/summarise", tags=["Summarisation"])
api_router.include_router(completeness.router, prefix="/completeness", tags=["Completeness"])
api_router.include_router(classification.router, prefix="/classify", tags=["Classification"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
