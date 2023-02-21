from pydantic import BaseSettings


# validation for our environment variables
class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str 
    database_name: str 
    database_username: str 
    secret_key: str
    algorithm: str 
    access_token_expire_minutes: int 
    cloud_name: str
    api_key: int 
    api_secret: str 
    secure: bool 
    STRIPE_SECRET_KEY: str
    
    class Config:
        env_file = ".env"

settings= Settings()
