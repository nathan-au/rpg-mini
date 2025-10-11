from fastapi import FastAPI, UploadFile, File
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select
from hashlib import sha256
import os


from models import Client,ClientCreate, Intake, IntakeCreate, ChecklistItem, Document
from enums import ClientComplexityEnum, IntakeStatusEnum, ChecklistItemDocKindEnum, ChecklistItemStatusEnum, DocumentDocKindEnum

from database import engine, init_database_tables

init_database_tables()

app = FastAPI()

CLIENT_COMPLEXITY_CHECKLIST = {
    "simple": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id],
    "average": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt],
    "complex": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt]
}



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

UPLOAD_DIR = "bucket"  
os.makedirs(UPLOAD_DIR, exist_ok=True) 

@app.post("/intakes/{intake_id}/documents")
async def upload_document(intake_id: int, file: UploadFile = File(...)):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            return {"error": "Intake not found"}
        
        contents = await file.read()
        file_hash = sha256(contents).hexdigest()
        
        existing_doc = session.exec(
            select(Document).where(Document.intake_id == intake_id, Document.sha256 == file_hash)
        ).first()
        if existing_doc:
            return {"error": "Duplicate document found"}

        stored_path = os.path.join(UPLOAD_DIR, f"{intake_id}_{file.filename}")
        with open(stored_path, "wb") as f:
            f.write(contents)

        doc = Document(
            intake_id=intake_id,
            filename=file.filename,
            sha256=file_hash,
            mime_type=file.content_type,
            size_bytes=len(contents),
            stored_path=stored_path,
            doc_kind=DocumentDocKindEnum.unknown,  
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        
        return {"document_id": doc.id, "filename": doc.filename, "doc_kind": doc.doc_kind}