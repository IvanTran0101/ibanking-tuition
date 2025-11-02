from __future__ import annotations
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Web service
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8080)

    # RabbitMQ
    RABBIT_URL: str = Field(default="amqp://guest:guest@localhost:5672/%2f")
    EVENT_EXCHANGE: str = Field(default="ibanking.events")
    EVENT_DLX: str = Field(default="ibanking.dlx")

    # Queue/routing keys
    NOTIFICATION_QUEUE: str = Field(default="notification.events.q")
    CONSUMER_PREFETCH: int = Field(default=32)
    RK_OTP_GENERATED: str = Field(default="otp.v1.generated")
    RK_PAYMENT_COMPLETED: str = Field(default="payment.v1.completed")
    
    # Email (SMTP)
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="trananhm265@gmail.com")
    SMTP_PASSWORD: str = Field(default="mtaixgkchrxwjmrt")
    EMAIL_FROM: str = Field(default="trananhm265@gmail.com")
    
    # Testing
    DRY_RUN: bool = Field(default=False)

settings = Settings()
