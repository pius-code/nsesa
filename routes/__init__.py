from fastapi import APIRouter
from routes.stakeholder import router as stakeholder_router



api_router = APIRouter()


api_router.include_router(stakeholder_router)
