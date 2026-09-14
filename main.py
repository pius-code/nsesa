from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from core.lifespan import lifespan
from utils.swagger import custom_openapi
from routes import api_router
from middleware.auth import verify_token_middleware
from core.config import get_cors_config, get_app_config

app_cfg = get_app_config()
cors_cfg = get_cors_config()

IS_DEV = app_cfg.env == "development"

app = FastAPI(
    title="FJ PAY API",
    description="Production-Grade POS, Payment & Inventory Management API for Ghanaian Merchants",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if IS_DEV else None,
    redoc_url=None,
)

# Custom OpenAPI
app.openapi = lambda: custom_openapi(app)

# Security Middleware for Headers & Method Restrictions
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # Method validation - reject unneeded methods
    if request.method not in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
        return JSONResponse(status_code=405, content={"detail": f"Method {request.method} not allowed"})
    
    response = await call_next(request)
    
    # Secure headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Auth middleware
app.middleware("http")(verify_token_middleware)

# Locked-down CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_cfg.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Branch-ID",
        "X-Idempotency-Key",
        "Accept",
        "Origin",
    ],
)

# Router registration
app.include_router(api_router)


def main():
    print("Starting FJ PAY API...")
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
