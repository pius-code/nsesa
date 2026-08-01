from fastapi import APIRouter, Depends
from schema.category import CategoryCreate, CategoryUpdate
from repository.category import create_category, get_all_categories, update_category, delete_category # noqa
from middleware.auth import get_current_user, admin_protected_route

router = APIRouter(prefix="/api/v1/categories", tags=["category"])


@router.post("")
async def add_category(payload: CategoryCreate, admin=Depends(admin_protected_route)): # noqa
    """Admin or super admin — create a new category for their own shop"""
    return await create_category(payload, admin)


@router.get("")
async def list_categories(user=Depends(get_current_user)): # noqa
    """Any authenticated user — list categories for their own shop (used to tag inventory)""" # noqa
    return await get_all_categories(user.get("sub"))


@router.patch("/{category_id}")
async def edit_category(category_id: str, payload: CategoryUpdate, admin=Depends(admin_protected_route)): # noqa
    """Admin or super admin — update a category belonging to their own shop"""
    return await update_category(category_id, payload, admin)


@router.delete("/{category_id}")
async def remove_category(category_id: str, admin=Depends(admin_protected_route)): # noqa
    """Admin or super admin — soft delete a category belonging to their own shop""" # noqa
    return await delete_category(category_id, admin)
