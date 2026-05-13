from model.Inventory import Inventory
from schema.inventory import InventoryCreate
from beanie import PydanticObjectId
from model.Stakeholder import Stakeholder


async def add_to_shop_inventory(payload: InventoryCreate, admin: str):
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not worker_admin:
        return {"message": "Unauthorized to add inventory items"}  # noqa
    worker_admin_shop_name = worker_admin.worker_shop_name

    new_inventory_item = Inventory(
        product_name=payload.product_name,
        product_price=payload.product_price,
        amount_available=payload.amount_available,
        created_by=admin,
        worker_shop_name=worker_admin_shop_name
    )
    await new_inventory_item.insert()
    return {
        "message": "Inventory item added successfully",
        "inventory_id": str(new_inventory_item.id),
    }


async def get_all_inventory_items_for_shop(worker_id: str):
    worker = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(worker_id))  # noqa
    if not worker:
        return {"message": "Unauthorized to view inventory items"}  # noqa
    items = await Inventory.find(Inventory.worker_shop_name == worker.worker_shop_name, Inventory.is_deleted == False).to_list() # noqa
    return items


async def delete_inventory_item(inventory_id: str, admin: str):
    item = await Inventory.get(inventory_id)
    if not item:
        return {"message": "Inventory item not found"}
    worker_admin = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(admin))  # noqa
    if not worker_admin:
        return {"message": "Unauthorized to delete this inventory item"}  # noqa
    item.is_deleted = True
    await item.save()
    return {"message": "Inventory item deleted successfully"}
