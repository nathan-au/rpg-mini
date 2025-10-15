
from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from database.database import engine
from database.models import Document, Intake
from logic.classification import classify_document, mark_checklist_item_received, mark_intake_received
from uuid import UUID
from logic.extraction import extract_document_fields, mark_checklist_item_extracted, mark_intake_extracted
from enums import DocumentDocKindEnum


router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/{document_id}/classify", status_code=200) #POST endpoint to classify one singular document
def classify_singular_document(document_id: UUID):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Intake not found")

        document_classification = classify_document(document)
        document.doc_kind = document_classification #set doc_kind in document in Document table to type that it has been classified as
        session.add(document)

        mark_checklist_item_received(document.doc_kind, document.intake_id, session)
        intake = session.get(Intake, document.intake_id)  #get intake to return intake status and id
        mark_intake_received(intake.id, session)

        session.commit() #commit document and checklist and intake changes to database
        session.refresh(document)
        session.refresh(intake) #refresh intake since we just updated it in update_intake_status()

        return { #return JSON with intake info and classified document info
            "intake": {
                "id": intake.id,
                "status": intake.status,
            },
            "classified_documents": [
                {
                    "classified_document": {
                        "document_id": document.id,
                        "filename": document.filename,
                        "mime_type": document.mime_type,
                        "stored_path": document.stored_path,
                        "doc_kind": document.doc_kind
                    }
                }
            ]  
        }

@router.post("/{document_id}/extract")
def extract_singular_document(document_id: UUID):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        if document.doc_kind == DocumentDocKindEnum.unknown:
            raise HTTPException(status_code=422, detail="Unprocessable content (document must be classified before extraction)")

        extracted_fields = extract_document_fields(document)
        document.extracted_fields = extracted_fields
        session.add(document)

        mark_checklist_item_extracted(extracted_fields, document.doc_kind, document.intake_id, session)
        intake = session.get(Intake, document.intake_id)
        mark_intake_extracted(intake.id, session)

        session.commit()
        session.refresh(document)
        session.refresh(intake) 

        return {
            "intake": {
                "id": intake.id,
                "status": intake.status,
            },            
            "extracted_documents": [
                {
                    "extracted_document": {
                        "document_id": document.id,
                        "filename": document.filename,
                        "mime_type": document.mime_type,
                        "stored_path": document.stored_path,
                        "doc_kind": document.doc_kind,
                        "extracted_fields": document.extracted_fields
                    }
                }
            ]
        }