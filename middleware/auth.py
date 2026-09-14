from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from model.Stakeholder import Stakeholder
from beanie import PydanticObjectId
from core.config import get_auth_config

auth_cfg = get_auth_config()

PUBLIC_PATHS = [
    "/",
    "/docs",
    "/openapi.json",
    "/api/v1/login",
    "/api/v1/register",
    "/api/v1/onboarding",
]


async def verify_token_middleware(request: Request, call_next):
    is_public_receipt = request.url.path.startswith("/api/v1/receipt/") or request.url.path.startswith("/api/v1/public/")
    is_public = request.url.path in PUBLIC_PATHS or is_public_receipt
    if request.method == "OPTIONS" or is_public:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401, content={"detail": "Missing or invalid authorization token"}
        )

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token, auth_cfg.jwt_secret, algorithms=[auth_cfg.jwt_algorithm]
        )
        request.state.user = payload
    except JWTError:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or expired session token"}
        )

    response = await call_next(request)
    return response


async def get_current_user(request: Request) -> dict:
    """Extract current user payload from request state"""
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return request.state.user


async def get_current_user_optional(request: Request) -> dict | None:
    """Returns user if authenticated, None if not"""
    if not hasattr(request.state, "user"):
        return None
    return request.state.user


async def get_current_stakeholder(request: Request) -> Stakeholder:
    """Extract verified DB stakeholder with fresh permissions and shop binding"""
    user = await get_current_user(request)
    sub = user.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    try:
        stakeholder = await Stakeholder.get(PydanticObjectId(sub))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stakeholder ID"
        )

    if not stakeholder or not stakeholder.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or deleted"
        )
    return stakeholder


def require_roles(allowed_roles: list[str]):
    """Role-based access control dependency"""
    async def role_checker(stakeholder: Stakeholder = Depends(get_current_stakeholder)):
        # Super admin always has access
        if stakeholder.worker_role == "super_admin":
            return stakeholder
        
        # Backward compatibility: "admin" maps to "owner"
        effective_role = stakeholder.worker_role
        if effective_role == "admin" and "owner" in allowed_roles:
            return stakeholder

        if effective_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}",
            )
        return stakeholder
    return role_checker


async def admin_protected_route(request: Request):
    """Admin / Manager / Owner level access"""
    stakeholder = await get_current_stakeholder(request)
    if stakeholder.worker_role not in ("super_admin", "owner", "admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required",
        )
    return str(stakeholder.id)


async def super_admin_protected_route(request: Request):
    """Platform Super Admin level access (FJ Pay operators)"""
    stakeholder = await get_current_stakeholder(request)
    if stakeholder.worker_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="FJ Pay Platform Administrator access required",
        )
    return str(stakeholder.id)
