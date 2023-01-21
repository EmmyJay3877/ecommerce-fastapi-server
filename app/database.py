from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from .config import settings
import os

DATABASE_USERNAME = os.environ.get("DATABASE_USERNAME")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
DATABASE_HOSTNAME = os.environ.get("DATABASE_HOSTNAME")
DATABASE_PORT = os.environ.get("DATABASE_PORT")
DATABASE_NAME = os.environ.get("DATABASE_NAME")

# locating our postgres database, using the connection string
SQLALCHEMY_DATABASE_URL = f'postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOSTNAME}:{DATABASE_PORT}/{DATABASE_NAME}' #format for the connection sring


# create engine, its respnsible for the connection of sqlalchemy to postgres
# an engine which the session will use for connection resources
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# talk to the sql database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # these are default values

# define our base class
Base = declarative_base() # all our models will be extending this base class

# Dependency, get a session with the db anytime we get a request and close when done
def get_db():
    db = SessionLocal() # talk wiht the db
    try:
        yield db
    finally:
        db.close()

