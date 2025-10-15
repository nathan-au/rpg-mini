from database.models import Document, ChecklistItem, Intake
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
from ollama import generate
import json
import re
from uuid import UUID
from sqlmodel import Session, select

def extract_document_fields(document: Document) -> dict | None:
    document_contents = extract_document_contents(document)
    extraction_prompt = select_extraction_prompt(document, document_contents)
    extracted_fields = run_extraction_model(extraction_prompt)
    return extracted_fields
    

def extract_document_contents(document: Document) -> str:
    document_stored_path = document.stored_path
    document_contents = ""
    try:
        if document_stored_path.lower().endswith(".pdf"):
            pdf_image = convert_from_path(document_stored_path, dpi=300)
            document_contents = pytesseract.image_to_string(pdf_image[0])
        elif document_stored_path.lower().endswith((".png", ".jpg", ".jpeg")): 
            with Image.open(document_stored_path) as image_file:
                document_contents = pytesseract.image_to_string(image_file)
    except Exception as e: 
        print(f"Conversion/OCR failed for {document_stored_path}: {e}")

    return document_contents

def select_extraction_prompt(document: Document, document_contents: str) -> str:
    document_classification = document.doc_kind

    if document_classification == DocumentDocKindEnum.receipt:
        extraction_prompt = f"""
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
        {document_contents}
        """
    elif document_classification == DocumentDocKindEnum.T4:
        extraction_prompt = f"""
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
        {document_contents}
        """
    elif document_classification == DocumentDocKindEnum.id:
        extraction_prompt = f"""
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
        {document_contents}
        """

    return extraction_prompt

def run_extraction_model(extraction_prompt: str) -> dict | None:
    model = "gemma3" #model that will be used to extract fields
    try: 
        model_output = generate(model=model, prompt=extraction_prompt) #generate model output with model and prompt
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
    return extracted_fields

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
