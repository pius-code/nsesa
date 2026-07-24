from fastapi import APIRouter
from routes.stakeholder import router as stakeholder_router
from routes.transaction import router as transaction_router
from routes.admin import router as admin_router
from routes.inventory import router as inventory_router
from routes.category import router as category_router
from routes.client import router as client_router
from routes.dashboard import router as dashboard_router
api_router = APIRouter()


api_router.include_router(stakeholder_router)
api_router.include_router(transaction_router)
api_router.include_router(admin_router)
api_router.include_router(inventory_router)
api_router.include_router(category_router)
api_router.include_router(client_router)
api_router.include_router(dashboard_router)
