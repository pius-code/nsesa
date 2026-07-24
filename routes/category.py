from fastapi import APIRouter, Depends
from schema.category import CategoryCreate, CategoryUpdate
from repository.category import create_category, get_all_categories, update_category, delete_category # noqa
from middleware.auth import get_current_user, admin_protected_route, super_admin_protected_route # noqa

router = APIRouter(prefix="/api/v1/categories", tags=["category"])


@router.post("")
async def add_category(payload: CategoryCreate, admin=Depends(admin_protected_route)): # noqa
    """Admin or super admin — create a new global category (shared across all shops)""" # noqa
    return await create_category(payload, admin)


@router.get("")
async def list_categories(user=Depends(get_current_user)): # noqa
    """Any authenticated user — list all categories (used to tag inventory)"""
    return await get_all_categories()


@router.patch("/{category_id}")
async def edit_category(category_id: str, payload: CategoryUpdate, admin=Depends(admin_protected_route)): # noqa
    """Admin or super admin — update a category"""
    return await update_category(category_id, payload)


@router.delete("/{category_id}")
async def remove_category(category_id: str, super_admin=Depends(super_admin_protected_route)): # noqa
    """Super admin only — soft delete a category"""
    return await delete_category(category_id)
