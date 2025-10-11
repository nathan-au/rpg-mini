from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

app = FastAPI()

clients = []

class ComplexityEnum(str, Enum):
    simple = "simple"
    average = "average"
    complex = "complex"

class Client(BaseModel):
    id: int
    name: str
    email: str
    complexity: ComplexityEnum
    created_at: datetime


@app.post("/clients")
def create_client(client: Client):
    clients.append(client)
    return clients


@app.get("/clients")
def read_clients():
    return clients