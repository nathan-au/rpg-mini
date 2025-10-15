
from fastapi import APIRouter
from sqlmodel import Session
from database.database import engine
from database.models import Document, Intake
from logic.classification import classify_document, receive_checklist_item, receive_intake
from uuid import UUID
from logic.extraction import extract_document_fields, extract_checklist_item, extract_intake
from enums import DocumentDocKindEnum


router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/{document_id}/classify") #POST endpoint to classify one singular document
def classify_singular_document(document_id: UUID):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            return {"error": "Document not found"}

        document_classification = classify_document(document)

        document.doc_kind = document_classification #set doc_kind in document in Document table to type that it has been classified as
        session.add(document)

        receive_checklist_item(document_classification, document.intake_id, session)
        receive_intake(document.intake_id, session)

        session.commit() #commit document and checklist and intake changes to database
        session.refresh(document)

        intake = session.get(Intake, document.intake_id)  #get intake to return intake status and id
        session.refresh(intake) #refresh intake since we just updated it in update_intake_status()

        return { #return JSON with intake info and classified document info
            "intake_id": intake.id,
            "classified_documents": [
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "classified_as": document.doc_kind
                }
            ],
            "intake_status": intake.status
        }

    
@router.post("/{document_id}/extract")
def extract_singular_document(document_id: UUID):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            return {"error": "Document not found"}
        if document.doc_kind == DocumentDocKindEnum.unknown:
            return {"error": "Document not classified"}


        
        extracted_fields = extract_document_fields(document)
        document.extracted_fields = extracted_fields
        session.add(document)

        extract_checklist_item(extracted_fields, document.doc_kind, document.intake_id, session)
        extract_intake(document.intake_id, session)

        session.commit()
        session.refresh(document)

        intake = session.get(Intake, document.intake_id)  
        session.refresh(intake) 

        return {
            "intake_id": intake.id,
            "extracted_documents": [
                {
                    "document_id": document.id,
                    "document_classification": document.doc_kind,
                    "extracted_fields": document.extracted_fields
                }
            ],
            "intake_status": intake.status
        }