from fastapi import FastAPI
from app.routers import users
from app.database import Base, engine
from app import models

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.include_router(users.router)
