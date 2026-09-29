from fastapi import APIRouter, Depends, Query
from schema.client import ClientCreate, ClientUpdate
from repository.client import create_client, search_clients, get_client_by_id, update_client, delete_client # noqa
from repository.transaction import get_transactions_by_client
from repository.stakeholder import get_stakeholder_worker_shop_name
from middleware.auth import get_current_user, admin_protected_route, require_permission

router = APIRouter(prefix="/api/v1/clients", tags=["client"])


@router.post("")
async def add_client(payload: ClientCreate, worker_id: str = Depends(require_permission("can_add_clients"))): # noqa
    """Register a new client for shop (requires can_add_clients)"""
    return await create_client(payload, worker_id)


@router.get("")
async def list_clients(
    q: str | None = Query(default=None, description="Search by name or phone"),
    limit: int = Query(default=20, ge=1, le=100),
    worker_id: str = Depends(require_permission("can_see_clients")), # noqa
):
    """Search/list clients for shop (requires can_see_clients)"""
    return await search_clients(worker_id, query=q, limit=limit)


@router.get("/{client_id}")
async def get_client(client_id: str, worker_id: str = Depends(require_permission("can_see_clients"))): # noqa
    """Fetch a single client (requires can_see_clients)"""
    return await get_client_by_id(client_id, worker_id)


@router.get("/{client_id}/transactions")
async def get_client_transactions(client_id: str, worker_id: str = Depends(require_permission("can_see_clients"))): # noqa
    """Purchase history for a client in their shop (requires can_see_clients)"""
    shop_name = await get_stakeholder_worker_shop_name(worker_id)
    return await get_transactions_by_client(client_id, shop_name) # type: ignore # noqa


@router.patch("/{client_id}")
async def edit_client(client_id: str, payload: ClientUpdate, worker_id: str = Depends(require_permission("can_edit_clients"))): # noqa
    """Update a client's details (requires can_edit_clients)"""
    return await update_client(client_id, payload, worker_id)


@router.delete("/{client_id}")
async def remove_client(client_id: str, admin=Depends(admin_protected_route)): # noqa
    """Admin only — soft delete a client"""
    return await delete_client(client_id, admin)

