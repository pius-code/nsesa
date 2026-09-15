import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class DatabaseConfig(BaseModel):
    mongo_url: str = Field(default_factory=lambda: os.getenv("MONGO_URL", "mongodb://localhost:27017/nsesa_db"))


class AuthConfig(BaseModel):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 1440

    @classmethod
    def from_env(cls) -> "AuthConfig":
        env = os.getenv("ENV", "development")
        secret = os.getenv("JWT_SECRET_KEY")
        if env == "production" and not secret:
            raise ValueError("JWT_SECRET_KEY must be set when ENV=production")
        if not secret:
            secret = "dev-only-secret-change-me"
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        expires = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        return cls(jwt_secret=secret, jwt_algorithm=algorithm, token_expire_minutes=expires)


class CorsConfig(BaseModel):
    allowed_origins: list[str] = Field(default_factory=lambda: [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://fjpay.app,https://app.fjpay.com",
        ).split(",")
        if origin.strip()
    ])

    @classmethod
    def from_env(cls) -> "CorsConfig":
        raw = os.getenv("ALLOWED_ORIGINS")
        if raw is None:
            origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "https://fjpay.app",
                "https://app.fjpay.com",
            ]
        else:
            origins = [
                origin.strip()
                for origin in raw.split(",")
                if origin.strip()
            ]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must include at least one trusted origin")
        if any(origin == "*" for origin in origins):
            raise ValueError("Wildcard CORS origins are not allowed. Configure an explicit allowlist.")
        return cls(allowed_origins=origins)


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
    return AuthConfig.from_env()


def get_cors_config() -> CorsConfig:
    return CorsConfig.from_env()


def get_sms_config() -> SmsConfig:
    return SmsConfig()


def get_payment_config() -> PaymentConfig:
    return PaymentConfig()


def get_app_config() -> AppConfig:
    return AppConfig()
