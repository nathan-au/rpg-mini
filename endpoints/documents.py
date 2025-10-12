
from fastapi import APIRouter
from sqlmodel import Session, select
from database import engine
from models import Document, ChecklistItem, Intake
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum

import pymupdf
import pytesseract
from PIL import Image

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/{document_id}/classify")
def classify_document(document_id: int):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            return {"error": "Document not found"}

        filename = document.filename.lower()
        document_kind = None

        if "t4" in filename:
            document_kind = DocumentDocKindEnum.T4
        elif "receipt" in filename:
            document_kind = DocumentDocKindEnum.receipt
        elif "license" in filename:
            document_kind = DocumentDocKindEnum.id
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
                print(f"OCR/Extraction failed: {e}")

            text_lower = text.lower()

            if "t4" in text_lower:
                document_kind = DocumentDocKindEnum.T4
            elif "receipt" in text_lower:
                document_kind = DocumentDocKindEnum.receipt
            elif "license" in text_lower or "id" in text_lower or "passport" in text_lower:
                document_kind = DocumentDocKindEnum.id
            else:
                document_kind = DocumentDocKindEnum.unknown

        document.doc_kind = document_kind
        session.add(document)

        if document_kind != DocumentDocKindEnum.unknown:
            checklist_item = session.exec(
                select(ChecklistItem).where(
                    ChecklistItem.intake_id == document.intake_id,
                    ChecklistItem.doc_kind == document_kind
                )
            ).first()
            if checklist_item:
                checklist_item.status = ChecklistItemStatusEnum.received
                session.add(checklist_item)

        all_items = session.exec(
            select(ChecklistItem).where(ChecklistItem.intake_id == document.intake_id)
        ).all()
        if all(item.status == ChecklistItemStatusEnum.received for item in all_items):
            intake = session.get(Intake, document.intake_id)
            intake.status = IntakeStatusEnum.done
            session.add(intake)

        session.commit()
        session.refresh(document)

        return {
            "document_id": document.id,
            "filename": document.filename,
            "classified_as": document.doc_kind,
        }