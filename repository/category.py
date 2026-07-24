from model.Category import Category
from schema.category import CategoryCreate, CategoryUpdate, CategoryResponse
from beanie import PydanticObjectId
from fastapi import HTTPException


def _to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(category.id),
        name=category.name,
        description=category.description,
        created_by=category.created_by,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


async def create_category(payload: CategoryCreate, created_by: str):
    existing = await Category.find_one(
        Category.name == payload.name, Category.is_deleted == False # noqa
    )
    if existing:
        raise HTTPException(status_code=400, detail="A category with this name already exists") # noqa

    new_category = Category(
        name=payload.name,
        description=payload.description,
        created_by=created_by,
    )
    await new_category.insert()
    return _to_response(new_category)


async def get_all_categories():
    categories = await Category.find(Category.is_deleted == False).sort(Category.name).to_list() # noqa
    return [_to_response(c) for c in categories]


async def update_category(category_id: str, payload: CategoryUpdate):
    category = await Category.get(PydanticObjectId(category_id))
    if not category or category.is_deleted:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data:
        existing = await Category.find_one(
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


async def delete_category(category_id: str):
    category = await Category.get(PydanticObjectId(category_id))
    if not category or category.is_deleted:
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_deleted = True
    await category.save()
    return {"message": "Category deleted successfully"}
