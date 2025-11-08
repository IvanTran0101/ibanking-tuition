from __future__ import annotations

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # Web server
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8080)

    # Database (SQLAlchemy URL for PostgreSQL recommended)
    PAYMENT_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://payment_user:payment_pass@localhost:5432/payment_db",
        description="Connection string to the Payment service database",
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)

    # Redis (payment intent cache)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_POOL_SIZE: int = Field(default=10)

    # RabbitMQ
    RABBIT_URL: str = Field(default="amqp://guest:guest@localhost:5672/%2f")
    EVENT_EXCHANGE: str = Field(default="ibanking.events")
    EVENT_DLX: str = Field(default="ibanking.dlx")
    PAYMENT_PAYMENT_QUEUE: str = Field(default="payment.payment.q")
    CONSUMER_PREFETCH: int = Field(default=32)


    # Routing keys (subscribe)
    RK_TUITION_LOCK: str = Field(default="tuition.v1.tuition_lock")
    RK_TUITION_LOCK_FAILED: str = Field(default="tuition.v1.tuition_lock_failed")
    RK_TUITION_UPDATED: str = Field(default="tuition.v1.tuition_updated")
    RK_TUITION_UNLOCKED: str = Field(default="tuition.v1.tuition_unlocked")
    
    RK_BALANCE_HELD: str = Field(default="account.v1.balance_held")
    RK_BALANCE_HOLD_FAILED: str = Field(default="account.v1.balance_hold_failed")
    RK_BALANCE_UPDATED: str = Field(default="account.v1.balance_updated")
    RK_BALANCE_RELEASED: str = Field(default="account.v1.balance_released")
    
    RK_OTP_GENERATED: str = Field(default="otp.v1.generated")
    RK_OTP_SUCCEED: str = Field(default="otp.v1.succeed")
    RK_OTP_EXPIRED: str = Field(default="otp.v1.expired")
    
    # Routing keys (publish)
    RK_PAYMENT_INITIATED: str = Field(default="payment.v1.initiated")
    RK_PAYMENT_PROCESSING: str = Field(default="payment.v1.processing")
    RK_PAYMENT_AUTHORIZED: str = Field(default="payment.v1.authorized")
    RK_PAYMENT_COMPLETED:  str = Field(default="payment.v1.completed")
    RK_PAYMENT_CANCELED:   str = Field(default="payment.v1.canceled")
    RK_PAYMENT_UNAUTHORIZED: str = Field(default="payment.v1.unauthorized")
    # Business parameters
    HOLD_EXPIRES_MIN: int = Field(default=15, description="Minutes until a hold expires")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
