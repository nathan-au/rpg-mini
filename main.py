from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select

app = FastAPI()

class ClientComplexityEnum(str, Enum):
    simple = "simple"
    average = "average"
    complex = "complex"

class Client(SQLModel, table = True):
    id: int | None = Field(default=None, primary_key=True)    
    name: str
    email: str
    complexity: ClientComplexityEnum
    created_at: datetime = Field(default_factory=datetime.now)

class IntakeStatusEnum(str, Enum):
    open = "open"
    done = "done"

class Intake(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")  # link to Client
    fiscal_year: int
    status: IntakeStatusEnum = Field(default=IntakeStatusEnum.open)
    created_at: datetime = Field(default_factory=datetime.now)


engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

class ClientCreate(BaseModel):
    name: str
    email: str
    complexity: ClientComplexityEnum

class IntakeCreate(BaseModel):
    client_id: int
    fiscal_year: int

@app.post("/clients")
def create_client(client_data: ClientCreate):
    client = Client(**client_data.model_dump())
    with Session(engine) as session:
        session.add(client)
        session.commit()
        session.refresh(client)
        return client
    
@app.post("/intakes")
def create_intake(intake_data: IntakeCreate):
    intake = Intake(**intake_data.model_dump())

    with Session(engine) as session:
        client = session.get(Client, intake.client_id)
        if not client:
            return {"error": "Client not found"}
        session.add(intake)
        session.commit()
        session.refresh(intake)
        return intake

@app.get("/clients")
def read_clients():
    with Session(engine) as session:
        clients = session.exec(select(Client)).all()
        return clients
    
@app.get("/intakes")
def read_intakes():
    with Session(engine) as session:
        intakes = session.exec(select(Intake)).all()
        return intakes
