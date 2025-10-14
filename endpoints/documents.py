
from fastapi import APIRouter
from sqlmodel import Session
from database.database import engine
from database.models import Document, Intake
from logic.classification import classify_document, receive_checklist_item, update_intake_status
from uuid import UUID

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
        update_intake_status(document.intake_id, session)

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