from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Web service
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8080)

    # Auth
    JWT_SECRET: str = Field(default="dev-secret")
    JWT_ALG: str = Field(default="HS256")

    # Upstream services
    ACCOUNT_SERVICE_URL: str = Field(default="http://account_service:8080")
    PAYMENT_SERVICE_URL: str = Field(default="http://payment_service:8080")
    TUITION_SERVICE_URL: str = Field(default="http://tuition_service:8080")
    OTP_SERVICE_URL: str = Field(default="http://otp_service:8080")
    NOTIFICATION_SERVICE_URL: str = Field(default="http://notification_service:8080")
    AUTHENTICATION_SERVICE_URL: str = Field(default="http://authentication_service:8080")

    # CORS & HTTP client
    CORS_ALLOW_ORIGINS: str = Field(default="*")
    HTTP_TIMEOUT: float = Field(default=10.0)


settings = Settings()
