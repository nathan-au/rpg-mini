from fastapi import APIRouter, UploadFile, File
from sqlmodel import Session, select
import os
from hashlib import sha256
from models import Intake, IntakeCreate, Client, ChecklistItem, Document
from enums import ChecklistItemDocKindEnum, DocumentDocKindEnum
from database import engine

router = APIRouter(prefix="/intakes", tags=["Intakes"])

CLIENT_COMPLEXITY_CHECKLIST = {
    "simple": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id],
    "average": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt],
    "complex": [ChecklistItemDocKindEnum.T4, ChecklistItemDocKindEnum.id, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt, ChecklistItemDocKindEnum.receipt]
}

@router.get("/")
def TEMP_read_intakes():
    with Session(engine) as session:
        intakes = session.exec(select(Intake)).all()
        return intakes
    
@router.post("/")
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
    
UPLOAD_DIR = "bucket"  
os.makedirs(UPLOAD_DIR, exist_ok=True) 

@router.post("/{intake_id}/documents")
async def upload_document(intake_id: int, file: UploadFile = File(...)):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            return {"error": "Intake not found"}
        
        file_contents = await file.read()

        if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
            return {"error": "Invalid file type (only PDF, PNG, and JPG allowed)"}

        file_hash = sha256(file_contents).hexdigest()
        
        duplicate_document = session.exec(select(Document).where(Document.intake_id == intake_id, Document.sha256 == file_hash)).first()
        if duplicate_document:
            return {"error": "Duplicate document found"}

        stored_path = os.path.join(UPLOAD_DIR, f"{intake_id}_{file.filename}")
        with open(stored_path, "wb") as f:
            f.write(file_contents)

        document = Document(
            intake_id=intake_id,
            filename=file.filename,
            sha256=file_hash,
            mime_type=file.content_type,
            size_bytes=len(file_contents),
            stored_path=stored_path,
            doc_kind=DocumentDocKindEnum.unknown,  
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        
        return {"document_id": document.id, "filename": document.filename, "doc_kind": document.doc_kind}

@router.get("/{intake_id}/checklist")
def get_intake_checklist(intake_id: int):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            return {"error": "Intake not found"}

        checklist_items = session.exec(
            select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
        ).all()

        checklist = [
            {"doc_kind": item.doc_kind, "status": item.status} for item in checklist_items
        ]

        return {
            "intake status": intake.status,
            "checklist": checklist
        }