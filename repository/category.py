from model.Category import Category
from model.Stakeholder import Stakeholder
from schema.category import CategoryCreate, CategoryUpdate, CategoryResponse
from beanie import PydanticObjectId
from fastapi import HTTPException


def _to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        description=category.description,
        worker_shop_name=category.worker_shop_name,
        created_by=category.created_by,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


async def _get_worker_shop(worker_id: str) -> str:
    worker = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(worker_id)) # noqa
    if not worker:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return worker.worker_shop_name


async def create_category(payload: CategoryCreate, created_by: str):
    shop_name = await _get_worker_shop(created_by)

    existing = await Category.find_one(
        Category.worker_shop_name == shop_name,
        Category.name == payload.name,
        Category.is_deleted == False, # noqa
    )
    if existing:
        raise HTTPException(status_code=400, detail="A category with this name already exists") # noqa

    new_category = Category(
        name=payload.name,
        description=payload.description,
        worker_shop_name=shop_name,
        created_by=created_by,
    )
    await new_category.insert()
    return _to_response(new_category)


async def get_all_categories(worker_id: str):
    shop_name = await _get_worker_shop(worker_id)
    categories = await Category.find(
        Category.worker_shop_name == shop_name, Category.is_deleted == False # noqa
    ).sort(Category.name).to_list()
    return [_to_response(c) for c in categories]


async def update_category(category_id: str, payload: CategoryUpdate, admin_id: str): # noqa
    shop_name = await _get_worker_shop(admin_id)
    category = await Category.get(PydanticObjectId(category_id))
    if not category or category.is_deleted or category.worker_shop_name != shop_name: # noqa
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data:
        existing = await Category.find_one(
            Category.worker_shop_name == shop_name,
            Category.name == update_data["name"],
            Category.is_deleted == False, # noqa
            Category.id != category.id,
        )
        if existing:
            raise HTTPException(status_code=400, detail="A category with this name already exists") # noqa

    for field, value in update_data.items():
        setattr(category, field, value)

    await category.save()
    return _to_response(category)


async def delete_category(category_id: str, admin_id: str):
    shop_name = await _get_worker_shop(admin_id)
    category = await Category.get(PydanticObjectId(category_id))
    if not category or category.is_deleted or category.worker_shop_name != shop_name: # noqa
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_deleted = True
    await category.save()
    return {"message": "Category deleted successfully"}
