from fastapi import APIRouter, Depends
from schema.category import CategoryCreate, CategoryUpdate
from repository.category import create_category, get_all_categories, update_category, delete_category # noqa
from middleware.auth import get_current_user, require_permission

router = APIRouter(prefix="/api/v1/categories", tags=["category"])


@router.post("")
async def add_category(payload: CategoryCreate, worker_id=Depends(require_permission("can_add_categories"))): # noqa
    """Permission: can_add_categories — create a new category"""
    return await create_category(payload, worker_id)


@router.get("")
async def list_categories(user=Depends(get_current_user)): # noqa
    """Any authenticated user — list categories for their own shop (used to tag inventory)""" # noqa
    return await get_all_categories(user.get("sub"))


@router.patch("/{category_id}")
async def edit_category(category_id: str, payload: CategoryUpdate, worker_id=Depends(require_permission("can_add_categories"))): # noqa
    """Permission: can_add_categories — update a category"""
    return await update_category(category_id, payload, worker_id)


@router.delete("/{category_id}")
async def remove_category(category_id: str, worker_id=Depends(require_permission("can_add_categories"))): # noqa
    """Permission: can_add_categories — soft delete a category""" # noqa
    return await delete_category(category_id, worker_id)

