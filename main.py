from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select

from models import Client, Intake, ChecklistItem
from enums import ClientComplexityEnum, IntakeStatusEnum, ChecklistItemDocKindEnum, ChecklistItemStatusEnum

app = FastAPI()

CLIENT_COMPLEXITY_CHECKLIST = {
    "simple": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id],
    "average": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt],
    "complex": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt]
}

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
        expected_docs = CLIENT_COMPLEXITY_CHECKLIST[client.complexity.value]

        checklist_items = [
            ChecklistItem(intake_id=intake.id, doc_kind=doc)
            for doc in expected_docs
        ]

        session.add_all(checklist_items)
        session.commit()

        return {
            "intake": {
                "id": intake.id,
                "client_id": intake.client_id,
                "fiscal_year": intake.fiscal_year,
                "status": intake.status,
                "created_at": intake.created_at,
            },
            "checklist": [
                {"doc_kind": item.doc_kind, "status": item.status}
                for item in checklist_items
            ],
        }
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
