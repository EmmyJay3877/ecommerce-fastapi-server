from pydantic import BaseSettings


# validation for our environment variables
class Settings(BaseSettings):
    dev_database_hostname: str
    dev_database_port: str
    dev_database_password: str
    dev_database_name: str
    dev_database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    cloud_name: str
    api_key: int
    api_secret: str
    secure: bool
    stripe_secret_key: str
    dev_redis_host: str
    dev_redis_port: str
    python_env: str
    local_client: str

    class Config:
        env_file = ".env"


settings = Settings()
