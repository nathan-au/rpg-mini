from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select

app = FastAPI()

class ComplexityEnum(str, Enum):
    simple = "simple"
    average = "average"
    complex = "complex"

class Client(SQLModel, table = True):
    id: int | None = Field(default=None, primary_key=True)    
    name: str
    email: str
    complexity: ComplexityEnum
    created_at: datetime = Field(default_factory=datetime.now)

engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

@app.post("/clients")
def create_client(client: Client):
    with Session(engine) as session:
        session.add(client)
        session.commit()
        session.refresh(client)
        return client

@app.get("/clients")
def read_clients():
    with Session(engine) as session:
        clients_in_db = session.exec(select(Client)).all()
        return clients_in_db
