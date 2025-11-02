from __future__ import annotations
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # RabbitMQ
    RABBIT_URL: str = Field(default="amqp://guest:guest@localhost:5672/%2f")
    EVENT_EXCHANGE: str = Field(default="ibanking.events")
    EVENT_DLX: str = Field(default="ibanking.dlx")

    # Queue/routing keys
    OTP_QUEUE: str = Field(default="otp.payment.q")
    CONSUMER_PREFETCH: int = Field(default=32)
    RK_PAYMENT_PROCESSING: str = Field(default="payment.v1.processing")
    RK_OTP_GENERATED: str = Field(default="otp.v1.generated")
    RK_OTP_SUCCEED: str = Field(default="otp.v1.succeed")
    RK_OTP_EXPIRED: str = Field(default="otp.v1.expired")

    # OTP params
    OTP_TTL_SEC: int = Field(default=300)  # 5 minutes
    OTP_LENGTH: int = Field(default=6)

    # Redis cache
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    REDIS_POOL_SIZE: int = Field(default=10)

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
