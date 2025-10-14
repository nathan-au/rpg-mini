
from fastapi import APIRouter
from sqlmodel import Session
from database.database import engine
from database.models import Document, Intake
from logic.classification import classify_document, receive_checklist_item, receive_intake
from uuid import UUID

import pytesseract
from PIL import Image
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
import json
from ollama import generate
import re
from pdf2image import convert_from_path
from database.models import ChecklistItem
from sqlmodel import select


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
        
        document_stored_path = document.stored_path

        contents = ""
        try:
            if document_stored_path.lower().endswith(".pdf"):
                pdf_image = convert_from_path(document_stored_path, dpi=300)
                contents = pytesseract.image_to_string(pdf_image[0])
            elif document_stored_path.lower().endswith((".png", ".jpg", ".jpeg")): 
                with Image.open(document_stored_path) as image_file:
                    contents = pytesseract.image_to_string(image_file)
        except Exception as e: 
            print(f"Conversion/OCR failed for {document_stored_path}: {e}")

        document_classification = document.doc_kind

        if document_classification == DocumentDocKindEnum.receipt:
            prompt = f"""
            You are a precise extractor.

            Goal: extract two fields from the text:
            1) merchant_name (STRING) = the name of the store, vendor, or service provider as shown on the receipt
            2) total_amount (FLOAT) = the total amount charged or paid as printed on the receipt

            Return ONLY a single valid JSON object in this exact form:
            {{
            "merchant_name": "STRING or null",
            "total_amount": FLOAT or null
            }}

            Text to analyze:
            {contents}
            """
        elif document_classification == DocumentDocKindEnum.T4:
            prompt = f"""
            You are a precise extractor.

            Goal: extract three fields from the text:
            1) employer_name (STRING) = the name of the employer listed on the T4 slip
            2) box_14_employment_income (FLOAT) = the total employment income reported in Box 14 of the T4 slip
            3) box_22_income_tax_deducted (FLOAT) = the income tax deducted as reported in Box 22 of the T4 slip

            Return ONLY a single valid JSON object in this exact form:
            {{
                "employer_name": "STRING or null",
                "box_14_employment_income": FLOAT or null,
                "box_22_income_tax_deducted": FLOAT or null
            }}

            Text to analyze:
            {contents}
            """
        elif document_classification == DocumentDocKindEnum.id:
            prompt = f"""
            You are a precise extractor.

            Goal: extract three fields from the text:
            1) full_name (STRING) = the full legal name as printed on the ID document
            2) date_of_birth (STRING) = the date of birth of the individual as shown on the ID document
            3) id_number (STRING) = the identification number, e.g., driver's license number or passport number

            Return ONLY a single valid JSON object in this exact form:
            {{
                "full_name": "STRING or null",
                "date_of_birth": "STRING or null",
                "id_number": "STRING or null"
            }}

            Text to analyze:
            {contents}
            """
        
        model = "gemma3" #model that will be used to extract fields
        try: 
            model_output = generate(model=model, prompt=prompt) #generate model output with model and prompt
            response = model_output['response'] #get the response part of the model output
            extracted_fields = None
            try:
                json_pattern = r"\{.*\}" #regex pattern for content between two curly brackets
                json_match = re.search(json_pattern, response, re.DOTALL) #search for json pattern in response and DOTALL means the . in the json pattern will match across multiple lines (like multi-line JSON)
                json_string = json_match.group(0) #get json string from regex match object
                extracted_fields = json.loads(json_string) #convert json string into python dictionary (real JSON)
            except Exception as e:
                print(f"Error retreiving JSON from {response}: {e}")
        except Exception as e:
            print(f"Error running {model}: {e}")


        document.extracted_fields = extracted_fields
        session.add(document)

        def extract_checklist_item(extracted_fields: dict | None, document_classification: DocumentDocKindEnum, intake_id: UUID, session: Session):
        
            if extracted_fields == None:
                return
            
            matching_received_checklist_item = session.exec(
                select(ChecklistItem).where(
                    ChecklistItem.intake_id == intake_id,
                    ChecklistItem.doc_kind == document_classification,
                    ChecklistItem.status == ChecklistItemStatusEnum.received
                )
            ).first()
            if matching_received_checklist_item:
                matching_received_checklist_item.status = ChecklistItemStatusEnum.extracted
                session.add(matching_received_checklist_item)

        def extract_intake(intake_id: UUID, session: Session):

            intake_checklist = session.exec( #fetch intake checklist items
                select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
            ).all()
            if all(item.status == ChecklistItemStatusEnum.extracted for item in intake_checklist): #if all intake items are received then intake should be done
                intake = session.get(Intake, intake_id)
                intake.status = IntakeStatusEnum.done
                session.add(intake)


        extract_checklist_item(extracted_fields, document_classification, document.intake_id, session)
        extract_intake(document.intake_id, session)

        session.commit()
        session.refresh(document)



        return {
            "document_id": document.id,
            "document_classification": document.doc_kind,
            "extracted_fields": document.extracted_fields
        }