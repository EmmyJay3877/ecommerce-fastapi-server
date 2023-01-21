from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routers import item, customer, auth, order, admin
from .config import settings
from .routers.customer import start_background_tasks

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customer.router)
app.include_router(order.router)
app.include_router(auth.router)
app.include_router(item.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "Hello World"}

app.add_event_handler('startup', start_background_tasks)