from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlmodel import Session, select
import os
from hashlib import sha256
from database.models import Intake, IntakeCreate, Client, ChecklistItem, Document
from enums import DocumentDocKindEnum
from database.database import engine
from logic.classification import classify_document
from uuid import UUID
from constants import CLIENT_COMPLEXITY_CHECKLIST
from logic.extraction import extract_document_fields 
from config import UPLOAD_DIR
from logic.status import mark_checklist_item_received, mark_intake_received, mark_checklist_item_extracted, mark_intake_extracted

router = APIRouter(prefix="/intakes", tags=["Intakes"])

@router.post("/", status_code=201) #POST endpoint to create new intake
def create_intake(intake_data: IntakeCreate):
    intake = Intake(**intake_data.model_dump())
    with Session(engine) as session:
        client = session.get(Client, intake.client_id) #find client in database with matching client id
        if not client: 
            raise HTTPException(status_code=404, detail="Client not found") #raise HTTP error with code 404 and will show Client not found
        session.add(intake)

        initialized_intake_checklist = [ #creates ChecklistItem object for each item in list of expected checklist items based on client complexity
            ChecklistItem(intake_id=intake.id, doc_kind=expected_checklist_items)
            for expected_checklist_items in CLIENT_COMPLEXITY_CHECKLIST[client.complexity.value]
        ]

        session.add_all(initialized_intake_checklist)
        session.commit() #put new intake and checklist items into database
        session.refresh(intake) 

        intake_checklist = session.exec(
            select(ChecklistItem).where(ChecklistItem.intake_id == intake.id)
        ).all()

        return { #returns JSON response with intake and checklist details
            "intake": {
                "id": intake.id,
                "client_id": intake.client_id,
                "fiscal_year": intake.fiscal_year,
                "status": intake.status,
                "created_at": intake.created_at,
            },
            "intake_checklist": [
                {
                    "checklist_item": {
                        "id": checklist_item.id,
                        "doc_kind": checklist_item.doc_kind, 
                        "status": checklist_item.status,
                        "created_at": checklist_item.created_at
                    }
                }
                for checklist_item in intake_checklist
            ]
        }

@router.post("/{intake_id}/documents", status_code=201) #POST endpoint to upload documents
async def upload_document(intake_id: UUID, file: UploadFile = File(...)): #async def means the function is asynchronous meaning Python will continue while handling file uploads, file is uploaded and validated as UploadFile
    with Session(engine) as session:
        intake = session.get(Intake, intake_id) #get intake id from POST and verify that the intake exists
        if not intake:
            raise HTTPException(status_code=404, detail="Intake not found")
        file_contents = await file.read() #reads file contents (also asynchronous)

        if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}: #verify the file type and return error if uploaded file is an invalid type
            raise HTTPException(status_code=415, detail="Unsupported media type (PDF, PNG and JPG only)")

        file_hash = sha256(file_contents).hexdigest() #calculates SHA-256 hash for uploaded file contents, hexdigest converts hash to hexadecimal string
        
        duplicate_document = session.exec(select(Document).where(Document.intake_id == intake_id, Document.sha256 == file_hash)).first() #searches Document table for any documents with the same hash 
        if duplicate_document:
            raise HTTPException(status_code=409, detail="Duplicate document found") #return error if duplicate file (with same hash) is found

        stored_path = os.path.join(UPLOAD_DIR, f"{intake_id}_{file.filename}") #names file in the form [intake id _ original file name]
        with open(stored_path, "wb") as f: 
            f.write(file_contents) #write binary (wb) contents of uploaded file to stored path (bucket/new name)

        document = Document( #create new SQLModel Document object with relevant fields
            intake_id=intake_id,
            filename=file.filename,
            sha256=file_hash,
            mime_type=file.content_type,
            size_bytes=len(file_contents),
            stored_path=stored_path,
        )

        session.add(document)
        session.commit() #put in Document database
        session.refresh(document)
        
        return { #return JSON with new document info
            "id": document.id,
            "filename": document.filename,
            "sha256": document.sha256,
            "mime_type": document.mime_type,
            "size_bytes": document.size_bytes,
            "stored_path": document.stored_path,
            "uploaded_at": document.uploaded_at,
            "doc_kind": document.doc_kind,
            "extracted_fields": document.extracted_fields
        }

@router.post("/{intake_id}/classify", status_code=200) #POST endpoint to classify all unknown documents of an intake
def classify_all_intake_documents(intake_id: UUID):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            raise HTTPException(status_code=404, detail="Intake not found")

        unknown_documents = session.exec( #get all unknown documents of an intake
            select(Document).where(
                Document.intake_id == intake.id,
                Document.doc_kind == DocumentDocKindEnum.unknown
            )
        ).all()

        classified_documents = []

        for document in unknown_documents: #loop for each document that is unknown
            document_classification = classify_document(document)
            document.doc_kind = document_classification
            session.add(document)
            classified_documents.append({ #add classification document results to classified documents dict to be displayed later
                "classified_document": {
                    "document_id": document.id,
                    "filename": document.filename,
                    "mime_type": document.mime_type,
                    "stored_path": document.stored_path,
                    "doc_kind": document.doc_kind
                }
            })

            mark_checklist_item_received(document.doc_kind, document.intake_id, session)

        mark_intake_received(intake.id, session)
        session.commit()
        session.refresh(intake)

        return {
            "intake": {
                "id": intake.id,
                "status": intake.status,
            },
            "classified_documents": classified_documents,
        }
    
@router.post("/{intake_id}/extract", status_code=200)
def extract_all_intake_documents(intake_id: UUID):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            raise HTTPException(status_code=404, detail="Intake not found")
        pending_documents = session.exec( 
            select(Document).where(
                Document.intake_id == intake_id,
                Document.doc_kind != DocumentDocKindEnum.unknown,
                Document.extracted_fields == "null"
            )
        ).all()

        extracted_documents = []

        for document in pending_documents:
            extracted_fields = extract_document_fields(document)
            document.extracted_fields = extracted_fields
            session.add(document)
            extracted_documents.append({
                "extracted_document": {
                    "document_id": document.id,
                    "filename": document.filename,
                    "mime_type": document.mime_type,
                    "stored_path": document.stored_path,
                    "doc_kind": document.doc_kind,
                    "extracted_fields": document.extracted_fields
                }
            })
            mark_checklist_item_extracted(document.extracted_fields, document.doc_kind, document.intake_id, session)
        mark_intake_extracted(intake.id, session)
        session.commit()
        session.refresh(intake)

        return {
            "intake": {
                "id": intake.id,
                "status": intake.status,
            },
            "extracted_documents": extracted_documents,
        }

@router.get("/{intake_id}/checklist", status_code=200) #GET endpoint for intake status and checklist items
def get_intake_checklist(intake_id: UUID):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id) 
        if not intake: #verify intake exists
            raise HTTPException(status_code=404, detail="Intake not found")

        intake_checklist = session.exec( #get checklist items for intake based on intake id
            select(ChecklistItem).where(ChecklistItem.intake_id == intake.id)
        ).all()

        mark_intake_received(intake.id, session)
        mark_intake_extracted(intake.id, session)
        session.commit()
        session.refresh(intake)

        return { #return checklist items and intake status
            "intake": {
                "id": intake.id,
                "status": intake.status,
            },
            "intake_checklist": [
                {
                    "checklist_item": {
                        "id": checklist_item.id,
                        "doc_kind": checklist_item.doc_kind, 
                        "status": checklist_item.status,
                        "created_at": checklist_item.created_at
                    }
                }
                for checklist_item in intake_checklist
            ]
        }