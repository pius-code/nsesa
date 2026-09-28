# repository/shop.py
from model.Shop import Shop
from model.Stakeholder import Stakeholder
from model.Inventory import Inventory
from model.Transaction import Transaction
from model.Client import Client
from model.Category import Category
from model.Branch import Branch
from model.StockMovement import StockMovement
from model.Expense import Expense
from schema.shop import ShopProfileUpdate, ShopProfileResponse
from datetime import datetime, timezone
from fastapi import HTTPException


async def get_shop_status(shop_name: str) -> Shop | None:
    return await Shop.find_one(Shop.name == shop_name)


async def get_shop_profile(shop_name: str) -> ShopProfileResponse:
    shop = await Shop.find_one(Shop.name == shop_name)
    if not shop:
        shop = Shop(name=shop_name)
        await shop.insert()
    return ShopProfileResponse(
        name=shop.name,
        logo_url=shop.logo_url,
        location=shop.location,
        phone=shop.phone,
        email=shop.email,
        description=shop.description,
        currency=shop.currency,
        status=shop.status,
        created_at=shop.created_at,
    )


async def update_shop_profile(
    current_shop_name: str,
    payload: ShopProfileUpdate,
) -> dict:
    shop = await Shop.find_one(Shop.name == current_shop_name)
    if not shop:
        shop = Shop(name=current_shop_name)
        await shop.insert()

    requires_relogin = False
    new_name = payload.name.strip() if payload.name and payload.name.strip() else None

    # Handle Rename Cascade across all collections
    if new_name and new_name != current_shop_name:
        existing = await Shop.find_one(Shop.name == new_name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A shop with this name already exists. Please choose another name.",
            )

        # 1. Update Shop document name
        shop.name = new_name
        requires_relogin = True

        # 2. Cascade update across all referenced collections
        await Stakeholder.find(Stakeholder.worker_shop_name == current_shop_name).update_many(
            {"$set": {"worker_shop_name": new_name}}
        )
        await Inventory.find(Inventory.worker_shop_name == current_shop_name).update_many(
            {"$set": {"worker_shop_name": new_name}}
        )
        await Transaction.find(Transaction.at_shop == current_shop_name).update_many(
            {"$set": {"at_shop": new_name}}
        )
        await Client.find(Client.worker_shop_name == current_shop_name).update_many(
            {"$set": {"worker_shop_name": new_name}}
        )
        await Category.find(Category.worker_shop_name == current_shop_name).update_many(
            {"$set": {"worker_shop_name": new_name}}
        )
        await Branch.find(Branch.shop_name == current_shop_name).update_many(
            {"$set": {"shop_name": new_name}}
        )
        await StockMovement.find(StockMovement.shop_name == current_shop_name).update_many(
            {"$set": {"shop_name": new_name}}
        )
        await Expense.find(Expense.shop_name == current_shop_name).update_many(
            {"$set": {"shop_name": new_name}}
        )

    # Handle logo update and sync to Stakeholder avatar
    effective_name = new_name if (new_name and new_name != current_shop_name) else current_shop_name
    if payload.logo_url is not None:
        shop.logo_url = payload.logo_url
        await Stakeholder.find(Stakeholder.worker_shop_name == effective_name).update_many(
            {"$set": {"worker_shop_image": payload.logo_url}}
        )

    if payload.location is not None:
        shop.location = payload.location
    if payload.phone is not None:
        shop.phone = payload.phone
    if payload.email is not None:
        shop.email = payload.email
    if payload.description is not None:
        shop.description = payload.description
    if payload.currency is not None:
        shop.currency = payload.currency

    await shop.save()

    msg = (
        "Business profile and name updated! You must log in again to sync your new credentials."
        if requires_relogin
        else "Company profile updated successfully!"
    )

    return {
        "message": msg,
        "requires_relogin": requires_relogin,
        "shop": ShopProfileResponse(
            name=shop.name,
            logo_url=shop.logo_url,
            location=shop.location,
            phone=shop.phone,
            email=shop.email,
            description=shop.description,
            currency=shop.currency,
            status=shop.status,
            created_at=shop.created_at,
        ),
    }


async def _set_shop_status(shop_name: str, status: str, reason: str, changed_by: str): # noqa
    shop = await Shop.find_one(Shop.name == shop_name)
    if not shop:
        shop = Shop(name=shop_name)
    shop.status = status
    shop.status_reason = reason
    shop.status_changed_by = changed_by
    shop.status_changed_at = datetime.now(timezone.utc)
    await shop.save()
    return {"message": f"Shop {status} successfully"}


async def suspend_shop(shop_name: str, reason: str, super_admin_id: str):
    return await _set_shop_status(shop_name, "suspended", reason, super_admin_id) # noqa


async def delete_shop(shop_name: str, reason: str, super_admin_id: str):
    return await _set_shop_status(shop_name, "deleted", reason, super_admin_id)


async def reactivate_shop(shop_name: str, super_admin_id: str):
    shop = await Shop.find_one(Shop.name == shop_name)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    shop.status = "active"
    shop.status_reason = None
    shop.status_changed_by = super_admin_id
    shop.status_changed_at = datetime.now(timezone.utc)
    await shop.save()
    return {"message": "Shop reactivated successfully"}

