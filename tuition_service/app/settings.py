from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Web server
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8080)

    # Database (SQLAlchemy URL for PostgreSQL recommended)
    TUITION_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://account_user:account_pass@localhost:5432/account_db",
        description="Connection string to the Tuition service database",
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)

    # RabbitMQ
    RABBIT_URL: str = Field(default="amqp://guest:guest@localhost:5672/%2f")
    EVENT_EXCHANGE: str = Field(default="ibanking.events")
    EVENT_DLX: str = Field(default="ibanking.dlx")
    TUITION_PAYMENT_QUEUE: str = Field(default="tuition.payment.q")
    CONSUMER_PREFETCH: int = Field(default=32)

    # Routing keys (subscribe)
    RK_PAYMENT_INITIATED: str = Field(default="payment.v1.initiated")
    RK_PAYMENT_AUTHORIZED: str = Field(default="payment.v1.authorized")

    # Routing keys (publish)
    RK_TUITION_LOCK: str = Field(default="tuition.v1.tuition_lock")
    RK_TUITION_LOCK_FAILED: str = Field(default="tuition.v1.tuition_lock_failed")
    RK_TUITION_UPDATED: str = Field(default="tuition.v1.tuition_updated")
    RK_TUITION_UNLOCKED: str = Field(default="tuition.v1.tuition_unlocked")

    # Business parameters
    HOLD_EXPIRES_MIN: int = Field(default=15, description="Minutes until a hold expires")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()