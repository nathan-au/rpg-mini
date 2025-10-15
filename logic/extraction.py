from database.models import Document
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from enums import DocumentDocKindEnum
from ollama import generate
import json
import re

def extract_document_fields(document: Document) -> dict | None:
    document_contents = extract_document_contents(document) #first extracts document contents
    extraction_prompt = select_extraction_prompt(document, document_contents) #then picks prompt based on doc_kind
    extracted_fields = run_extraction_model(extraction_prompt) #extracts document fields
    return extracted_fields
    

def extract_document_contents(document: Document) -> str:
    document_stored_path = document.stored_path
    document_contents = ""
    try:
        if document_stored_path.lower().endswith(".pdf"): #convert pdf to image because for some reason image OCR is better than getting text from pdf
            pdf_image = convert_from_path(document_stored_path, dpi=300) #dpi is dots per inch and is basically like resolution
            document_contents = pytesseract.image_to_string(pdf_image[0]) #only convert the first page of the pdf (t4) because second page has too much info (overwhelms model)
        elif document_stored_path.lower().endswith((".png", ".jpg", ".jpeg")): 
            with Image.open(document_stored_path) as image_file:
                document_contents = pytesseract.image_to_string(image_file)
    except Exception as e: 
        print(f"{document.filename} could not be processed: {e}")

    return document_contents

def select_extraction_prompt(document: Document, document_contents: str) -> str: #choose different prompt to extract different fields depending on what doc kind it is
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