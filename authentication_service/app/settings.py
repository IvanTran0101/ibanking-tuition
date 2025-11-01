from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # External services
    ACCOUNT_SERVICE_URL: str = Field(
        default="http://account-service:8080",
        description="Base URL of account service"
    )

    # Security
    JWT_SECRET: str = Field(..., description="JWT HMAC secret (read from ENV)")
    JWT_ALG: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRES_MIN: int = Field(default=60, description="Access token expiry in minutes")
    PASSWORD_SALT: str = Field(default="dev-salt", description="Salt for password hashing")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
