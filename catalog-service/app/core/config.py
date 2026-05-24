from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5433/catalog_db"
    port: int = 3001
    pool_min_size: int = 2
    pool_max_size: int = 10
    command_timeout: int = 30
    jwt_secret_key: str = "supersecret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 900
    refresh_token_expire_seconds: int = 604800

    model_config = {"env_file": ".env"}


settings = Settings()
