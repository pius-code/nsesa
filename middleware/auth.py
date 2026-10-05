from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
import os
from dotenv import load_dotenv
from model.Stakeholder import Stakeholder
from beanie import PydanticObjectId

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

PUBLIC_PATHS = [
    "/",
    "/docs",
    "/openapi.json",
    "/api/v1/login",
    "/api/v1/auth/forgot-password",
]


async def verify_token_middleware(request: Request, call_next):
    is_public_receipt = request.url.path.startswith("/api/v1/receipt/")
    is_public = request.url.path in PUBLIC_PATHS or is_public_receipt
    if request.method == "OPTIONS" or is_public:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401, content={"detail": "Missing or invalid token"}
        )

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token, str(JWT_SECRET_KEY), algorithms=[str(JWT_ALGORITHM)]
        )
        request.state.user = payload
    except JWTError:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or expired token"}
        )

    response = await call_next(request)
    return response


async def get_current_user(request: Request) -> dict:
    """Extract current user from request state"""
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"  # noqa
        )
    return request.state.user


async def get_current_user_optional(request: Request) -> dict | None:
    """Returns user if authenticated, None if not"""
    if not hasattr(request.state, "user"):
        return None
    return request.state.user


async def _resolve_stakeholder(request: Request) -> Stakeholder:
    """Internal helper — fetches & returns the full Stakeholder for the current JWT."""
    user = await get_current_user(request)
    sub = user.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        stakeholder = await Stakeholder.get(PydanticObjectId(sub))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if not stakeholder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    return stakeholder


async def admin_protected_route(request: Request) -> str:
    """Returns worker ID. Allows admins and super_admins only."""
    stakeholder = await _resolve_stakeholder(request)
    if stakeholder.worker_role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return str(stakeholder.id)


async def super_admin_protected_route(request: Request) -> str:
    """Returns worker ID. Allows super_admins only."""
    stakeholder = await _resolve_stakeholder(request)
    if stakeholder.worker_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required",
        )
    return str(stakeholder.id)


def require_permission(perm: str):
    """
    FastAPI dependency factory for permission-based route guards.

    Usage:
        @router.post("/sell")
        async def sell(..., worker_id=Depends(require_permission("can_sell"))):
            ...

    Super admins bypass permission checks entirely.
    Admins always pass (their permissions dict has all flags True).
    Workers must have the specific flag set to True in their permissions.
    """
    async def _check(request: Request) -> str:
        stakeholder = await _resolve_stakeholder(request)
        # Admins and Super Admins bypass permission checks
        if stakeholder.worker_role in ("admin", "super_admin"):
            return str(stakeholder.id)
        # Check permission flag; fall back to False if field missing (old records)
        perms = stakeholder.permissions or {}
        if not perms.get(perm, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to perform this action. Required: {perm.replace('_', ' ')}",
            )
        return str(stakeholder.id)
    return _check


def require_any_permission(*perms: str):
    """
    FastAPI dependency factory that passes if the user has ANY of the specified permissions.

    Usage:
        @router.get("/inventory")
        async def get_inventory(worker_id=Depends(require_any_permission("can_sell", "can_add_inventory", "can_update_stock"))):
            ...
    """
    async def _check(request: Request) -> str:
        stakeholder = await _resolve_stakeholder(request)
        # Admins and Super Admins bypass permission checks
        if stakeholder.worker_role in ("admin", "super_admin"):
            return str(stakeholder.id)
        user_perms = stakeholder.permissions or {}
        if not any(user_perms.get(p, False) for p in perms):
            readable = " or ".join(p.replace('_', ' ') for p in perms)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to perform this action. Required one of: {readable}",
            )
        return str(stakeholder.id)
    return _check


