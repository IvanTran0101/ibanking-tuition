from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Web server
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8080)

    # Redis Cache (for storing OTP codes)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for OTP cache"
    )
    REDIS_POOL_SIZE: int = Field(default=10)

    # RabbitMQ
    RABBIT_URL: str = Field(default="amqp://guest:guest@localhost:5672/%2f")
    EVENT_EXCHANGE: str = Field(default="ibanking.events")
    EVENT_DLX: str = Field(default="ibanking.dlx")
    OTP_PAYMENT_QUEUE: str = Field(default="otp.payment.q")
    CONSUMER_PREFETCH: int = Field(default=32)

    # Routing keys (subscribe)
    RK_PAYMENT_INITIATED: str = Field(default="payment.v1.initiated")

    # Routing keys (publish)
    RK_OTP_GENERATED: str = Field(default="otp.v1.generated")
    RK_OTP_EXPIRED: str = Field(default="otp.v1.expired")
    RK_OTP_VERIFIED: str = Field(default="otp.v1.verified")

    # Business parameters
    OTP_EXPIRES_SEC: int = Field(default=300, description="Seconds until OTP expires (5 minutes)")
    OTP_LENGTH: int = Field(default=6, description="Length of OTP code")
    OTP_MAX_ATTEMPTS: int = Field(default=3, description="Maximum OTP verification attempts")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()