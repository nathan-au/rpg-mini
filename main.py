from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field

app = FastAPI()


class ComplexityEnum(str, Enum):
    simple = "simple"
    average = "average"
    complex = "complex"

class Client(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    email: str
    complexity: ComplexityEnum
    created_at: datetime = Field(default = datetime.now())


@app.post("/clients")
def create_client(client: Client):
    return client

@app.get("/")
def read_root():
    return {"message": "FastAPI hello world"}

