import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class DatabaseConfig(BaseModel):
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/nsesa_db")


class AuthConfig(BaseModel):
    jwt_secret: str = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


class CorsConfig(BaseModel):
    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://fjpay.app,https://app.fjpay.com").split(",")
        if origin.strip()
    ]


class SmsConfig(BaseModel):
    arkesel_api_key: str | None = os.getenv("ARKESEL_API_KEY")
    arkesel_sender_id: str = os.getenv("ARKESEL_SENDER_ID", "FJPAY")
    hubtel_client_id: str | None = os.getenv("HUBTEL_CLIENT_ID")
    hubtel_client_secret: str | None = os.getenv("HUBTEL_CLIENT_SECRET")
    hubtel_sender_id: str = os.getenv("HUBTEL_SENDER_ID", "FJPAY")


class PaymentConfig(BaseModel):
    paystack_secret_key: str | None = os.getenv("PAYSTACK_SECRET_KEY")
    paystack_public_key: str | None = os.getenv("PAYSTACK_PUBLIC_KEY")
    hubtel_merchant_id: str | None = os.getenv("HUBTEL_MERCHANT_ID")


class AppConfig(BaseModel):
    env: str = os.getenv("ENV", "development")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    app_name: str = "FJ PAY"


# Scoped access providers so components only retrieve their needed configuration
def get_db_config() -> DatabaseConfig:
    return DatabaseConfig()


def get_auth_config() -> AuthConfig:
    return AuthConfig()


def get_cors_config() -> CorsConfig:
    return CorsConfig()


def get_sms_config() -> SmsConfig:
    return SmsConfig()


def get_payment_config() -> PaymentConfig:
    return PaymentConfig()


def get_app_config() -> AppConfig:
    return AppConfig()
