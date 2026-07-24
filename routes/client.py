from fastapi import APIRouter, Depends, Query
from schema.client import ClientCreate, ClientUpdate
from repository.client import create_client, search_clients, get_client_by_id, update_client, delete_client # noqa
from repository.transaction import get_transactions_by_client
from repository.stakeholder import get_stakeholder_worker_shop_name
from middleware.auth import get_current_user, admin_protected_route

router = APIRouter(prefix="/api/v1/clients", tags=["client"])


@router.post("")
async def add_client(payload: ClientCreate, worker=Depends(get_current_user)): # noqa
    """Any authenticated worker — register a new client for their shop"""
    return await create_client(payload, worker.get("sub"))


@router.get("")
async def list_clients(
    q: str | None = Query(default=None, description="Search by name or phone"),
    limit: int = Query(default=20, ge=1, le=100),
    worker=Depends(get_current_user), # noqa
):
    """Any authenticated worker — search/list clients for their shop"""
    return await search_clients(worker.get("sub"), query=q, limit=limit)


@router.get("/{client_id}")
async def get_client(client_id: str, worker=Depends(get_current_user)): # noqa
    """Any authenticated worker — fetch a single client"""
    return await get_client_by_id(client_id, worker.get("sub"))


@router.get("/{client_id}/transactions")
async def get_client_transactions(client_id: str, worker=Depends(get_current_user)): # noqa
    """Any authenticated worker — purchase history for a client in their shop"""
    shop_name = await get_stakeholder_worker_shop_name(worker.get("sub"))
    return await get_transactions_by_client(client_id, shop_name) # type: ignore # noqa


@router.patch("/{client_id}")
async def edit_client(client_id: str, payload: ClientUpdate, admin=Depends(admin_protected_route)): # noqa
    """Admin only — update a client's details"""
    return await update_client(client_id, payload, admin)


@router.delete("/{client_id}")
async def remove_client(client_id: str, admin=Depends(admin_protected_route)): # noqa
    """Admin only — soft delete a client"""
    return await delete_client(client_id, admin)
