from fastapi import APIRouter, UploadFile, File
from sqlmodel import Session, select
import os
from hashlib import sha256
from models import Intake, IntakeCreate, Client, ChecklistItem, Document
from enums import ChecklistItemDocKindEnum, DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
from database import engine

import pymupdf
import pytesseract
from PIL import Image

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
    

@router.post("/{intake_id}/classify")
def classify_intake_documents(intake_id: int):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            return {"error": "Intake not found"}

        unknown_docs = session.exec(
            select(Document).where(
                Document.intake_id == intake_id,
                Document.doc_kind == DocumentDocKindEnum.unknown
            )
        ).all()

        classified_results = []

        for document in unknown_docs:
            filename = document.filename.lower()
            doc_kind = None

            if "t4" in filename:
                doc_kind = DocumentDocKindEnum.T4
            elif "receipt" in filename:
                doc_kind = DocumentDocKindEnum.receipt
            elif "license" in filename or "id" in filename or "passport" in filename:
                doc_kind = DocumentDocKindEnum.id
            else:
                stored_path = document.stored_path
                text = ""
                try:
                    if stored_path.endswith(".pdf"):
                        pdf = pymupdf.open(stored_path)
                        for page in pdf:
                            text += page.get_text("text")
                        pdf.close()
                    elif stored_path.endswith((".png", ".jpg", ".jpeg")):
                        img = Image.open(stored_path)
                        text = pytesseract.image_to_string(img)
                except Exception as e:
                    print(f"OCR/Extraction failed for {stored_path}: {e}")

                text_lower = text.lower()
                if "t4" in text_lower:
                    doc_kind = DocumentDocKindEnum.T4
                elif "receipt" in text_lower:
                    doc_kind = DocumentDocKindEnum.receipt
                elif "license" in text_lower or "id" in text_lower or "passport" in text_lower:
                    doc_kind = DocumentDocKindEnum.id
                else:
                    doc_kind = DocumentDocKindEnum.unknown

            document.doc_kind = doc_kind
            session.add(document)

            if doc_kind != DocumentDocKindEnum.unknown:
                checklist_item = session.exec(
                    select(ChecklistItem).where(
                        ChecklistItem.intake_id == document.intake_id,
                        ChecklistItem.doc_kind == doc_kind
                    )
                ).first()
                if checklist_item:
                    checklist_item.status = ChecklistItemStatusEnum.received
                    session.add(checklist_item)

            classified_results.append({
                "document_id": document.id,
                "filename": document.filename,
                "classified_as": doc_kind
            })

        all_items = session.exec(
            select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
        ).all()
        if all(item.status == ChecklistItemStatusEnum.received for item in all_items):
            intake.status = IntakeStatusEnum.done
            session.add(intake)

        session.commit()
        session.refresh(document)

        return {
            "intake_id": intake_id,
            "classified_documents": classified_results,
            "intake_status": intake.status
        }