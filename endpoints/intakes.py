from fastapi import APIRouter, UploadFile, File
from sqlmodel import Session, select
import os
from hashlib import sha256
from models import Intake, IntakeCreate, Client, ChecklistItem, Document
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
from database import engine
from classification import classify_document, receive_checklist_item, update_intake_status

from constants import CLIENT_COMPLEXITY_CHECKLIST, T4_KEYWORDS, ID_KEYWORDS, RECEIPT_KEYWORDS

router = APIRouter(prefix="/intakes", tags=["Intakes"])

@router.get("/") #GET endpoint to get list of intakes
def TEMP_read_intakes():
    with Session(engine) as session:
        intakes = session.exec(select(Intake)).all()
        return intakes
    
@router.post("/") #POST endpoint to create new intake
def create_intake(intake_data: IntakeCreate):
    intake = Intake(**intake_data.model_dump())
    with Session(engine) as session:
        client = session.get(Client, intake.client_id) #find client in database with matching client id
        if not client: 
            return {"error": "Client not found"} #return error message if matching client not found
        session.add(intake)
        session.commit() #put new intake intto database
        session.refresh(intake) 

        expected_documents = CLIENT_COMPLEXITY_CHECKLIST[client.complexity.value] #get list of expected checklist items based on client complexity

        checklist_items = [ #creates ChecklistItem object for each expected item
            ChecklistItem(intake_id=intake.id, doc_kind=document)
            for document in expected_documents
        ]

        session.add_all(checklist_items)
        session.commit() #stage and commit all checklist items to database

        return { #returns JSON response with intake and checklist details
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
    
UPLOAD_DIR = "bucket" #define upload directory called bucket to store uploaded files
os.makedirs(UPLOAD_DIR, exist_ok=True) #if bucket does not exist, create bucket

@router.post("/{intake_id}/documents") #POST endpoint to upload documents
async def upload_document(intake_id: int, file: UploadFile = File(...)): #async def means the function is asynchronous meaning Python will continue while handling file uploads, file is uploaded and validated as UploadFile
    with Session(engine) as session:
        intake = session.get(Intake, intake_id) #get intake id from POST and verify that the intake exists
        if not intake:
            return {"error": "Intake not found"}
        
        file_contents = await file.read() #reads file contents (also asynchronous)

        if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}: #verify the file type and return error if uploaded file is an invalid type
            return {"error": "Invalid file type (only PDF, PNG, and JPG allowed)"}

        file_hash = sha256(file_contents).hexdigest() #calculates SHA-256 hash for uploaded file contents, hexdigest converts hash to hexadecimal string
        
        duplicate_document = session.exec(select(Document).where(Document.intake_id == intake_id, Document.sha256 == file_hash)).first() #searches Document table for any documents with the same hash 
        if duplicate_document:
            return {"error": "Duplicate document found"} #return error if duplicate file (with same hash) is found

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
            doc_kind=DocumentDocKindEnum.unknown,  
        )

        session.add(document)
        session.commit() #put in Document database
        session.refresh(document)
        
        return { #return JSON with new document info
            "document_id": document.id, 
            "filename": document.filename, 
            "doc_kind": document.doc_kind
        }

@router.get("/{intake_id}/checklist") #GET endpoint for intake status and checklist items
def get_intake_checklist(intake_id: int):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id) 
        if not intake: #verify intake exists
            return {"error": "Intake not found"}

        checklist_items = session.exec( #get checklist items for intake based on intake id
            select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
        ).all()

        checklist = [
            {"doc_kind": item.doc_kind, "status": item.status} for item in checklist_items
        ]

        return { #return checklist items and intake status
            "intake status": intake.status,
            "checklist": checklist
        }

@router.post("/{intake_id}/classify") #POST endpoint to classify all unknown documents of an intake
def classify_all_intake_documents(intake_id: int):
    with Session(engine) as session:
        intake = session.get(Intake, intake_id)
        if not intake:
            return {"error": "Intake not found"}

        unknown_documents = session.exec( #get all unknown documents of an intake
            select(Document).where(
                Document.intake_id == intake_id,
                Document.doc_kind == DocumentDocKindEnum.unknown
            )
        ).all()

        classification_results = []

        for document in unknown_documents: #loop for each document that is unknown
            
            document_classification = classify_document(document)

            document.doc_kind = document_classification
            session.add(document)

            classification_results.append({ #add classification results to classified results to be displayed later
                "document_id": document.id,
                "filename": document.filename,
                "classified_as": document.doc_kind
            })

            receive_checklist_item(document_classification, document.intake_id, session)

        update_intake_status(intake_id, session)
        session.commit()
        session.refresh(intake)

        return {
            "intake_id": intake_id,
            "classified_documents": classification_results,
            "intake_status": intake.status
        }