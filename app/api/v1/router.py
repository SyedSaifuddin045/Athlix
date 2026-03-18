from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

from .endpoints import auth, exercises, health, users

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)

# Protected routers
api_router.include_router(
    users.router,
    dependencies=[Depends(get_current_user)],
)

api_router.include_router(
    exercises.router,
    dependencies=[Depends(get_current_user)],
)