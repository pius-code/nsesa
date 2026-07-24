from model.Client import Client
from model.Stakeholder import Stakeholder
from schema.client import ClientCreate, ClientUpdate, ClientResponse
from beanie import PydanticObjectId
from beanie.operators import Or, RegEx
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError


def _to_response(client: Client) -> ClientResponse:
    return ClientResponse(
        id=str(client.id),
        client_name=client.client_name,
        client_phone=client.client_phone,
        client_email=client.client_email,
        notes=client.notes,
        worker_shop_name=client.worker_shop_name,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


async def _get_worker_shop(worker_id: str) -> str:
    worker = await Stakeholder.find_one(Stakeholder.id == PydanticObjectId(worker_id)) # noqa
    if not worker:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return worker.worker_shop_name


async def create_client(payload: ClientCreate, worker_id: str):
    shop_name = await _get_worker_shop(worker_id)

    new_client = Client(
        client_name=payload.client_name,
        client_phone=payload.client_phone or None,
        client_email=payload.client_email or None,
        notes=payload.notes,
        worker_shop_name=shop_name,
        created_by=worker_id,
    )
    try:
        await new_client.insert()
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="A client with this phone number already exists in your shop") # noqa
    return _to_response(new_client)


async def search_clients(worker_id: str, query: str | None = None, limit: int = 20):
    shop_name = await _get_worker_shop(worker_id)

    conditions = [Client.worker_shop_name == shop_name, Client.is_deleted == False] # noqa
    if query:
        conditions.append(
            Or(
                RegEx(Client.client_name, query, options="i"),
                RegEx(Client.client_phone, query, options="i"),
            )
        )

    clients = await Client.find(*conditions).sort(Client.client_name).limit(limit).to_list() # noqa
    return [_to_response(c) for c in clients]


async def get_client_by_id(client_id: str, worker_id: str):
    shop_name = await _get_worker_shop(worker_id)
    client = await Client.get(PydanticObjectId(client_id))
    if not client or client.is_deleted or client.worker_shop_name != shop_name:
        raise HTTPException(status_code=404, detail="Client not found")
    return _to_response(client)


async def update_client(client_id: str, payload: ClientUpdate, admin: str):
    shop_name = await _get_worker_shop(admin)
    client = await Client.get(PydanticObjectId(client_id))
    if not client or client.is_deleted or client.worker_shop_name != shop_name:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    try:
        await client.save()
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="A client with this phone number already exists in your shop") # noqa
    return _to_response(client)


async def delete_client(client_id: str, admin: str):
    shop_name = await _get_worker_shop(admin)
    client = await Client.get(PydanticObjectId(client_id))
    if not client or client.is_deleted or client.worker_shop_name != shop_name:
        raise HTTPException(status_code=404, detail="Client not found")

    client.is_deleted = True
    await client.save()
    return {"message": "Client deleted successfully"}
