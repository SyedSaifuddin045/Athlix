from fastapi import APIRouter

# relative import to the sibling `endpoints` package
from .endpoints import health

api_router = APIRouter()

api_router.include_router(health.router)