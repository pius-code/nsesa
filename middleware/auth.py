from fastapi import Request, HTTPException, status
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


async def admin_protected_route(request: Request):
    user = await get_current_user(request)
    sub = user.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated" # noqa
        )
    # Fetch user from the database to check their role
    try:
        stakeholder = await Stakeholder.get(PydanticObjectId(sub))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format" # noqa
        )

    if not stakeholder or stakeholder.worker_role not in ("admin", "super_admin"): # noqa
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",  # noqa
        )
    return sub


async def super_admin_protected_route(request: Request):
    user = await get_current_user(request)
    sub = user.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated" # noqa
        )
    # Fetch user from the database to check their role
    try:
        stakeholder = await Stakeholder.get(PydanticObjectId(sub))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format" # noqa
        )

    if not stakeholder or stakeholder.worker_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required",  # noqa
        )
    return sub
