from unidecode import unidecode
from PIL import Image
import pymupdf
import pytesseract
from database.models import Document, ChecklistItem, Intake
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
from constants import RECEIPT_KEYWORDS, T4_KEYWORDS, ID_KEYWORDS
from sqlmodel import Session, select

def classify_document(document: Document) -> DocumentDocKindEnum: #master function to classify documents
    document_classification = classify_document_by_name(document) #first try classifying by name
    if document_classification == DocumentDocKindEnum.unknown: #if still unknown after trying by name then move on to classifying by contents
        document_classification = classify_document_by_contents(document)
    return document_classification

def classify_document_by_name(document: Document) -> DocumentDocKindEnum: #check file name for keywords to classify document
    document_file_name = document.filename
    normalized_file_name = normalize_text(document_file_name)
    return search_keywords_in_text(normalized_file_name)
        
def classify_document_by_contents(document: Document) -> DocumentDocKindEnum: #check file contents for keywords to classify document
    document_stored_path = document.stored_path

    contents = ""
    try:
        if document_stored_path.endswith(".pdf"): #if file is a pdf then use PyMyPDF to get text from file
            with pymupdf.open(document_stored_path) as pdf_file: #use with..as to close file afterwards automatically
                for page in pdf_file: #for each page in pdf file, get page text and add to contents
                    contents += page.get_text("text")
        elif document_stored_path.endswith((".png", ".jpg", ".jpeg")): #if file is an image then use pytesseract OCR (optical character recognition) to convert image to string and add to contents
            with Image.open(document_stored_path) as image_file:
                contents = pytesseract.image_to_string(image_file)
    except Exception as e: #triggers if an Exception occurs inside try
        print(f"Extraction/OCR failed for {document_stored_path}: {e}")

    normalized_contents = normalize_text(contents)
    return search_keywords_in_text(normalized_contents) 

def search_keywords_in_text(text: str) -> DocumentDocKindEnum: 
    #starts with reciept check first because a given intake will only have one t4 and one id but can up to 5 receipts so receipts are more likely
    if any(keyword in text for keyword in RECEIPT_KEYWORDS): #searches text for each keyword in RECIEPT_KEYWORDS
        return DocumentDocKindEnum.receipt #classifies as and returns DocumentDocKindEnum receipt if found
    elif any(keyword in text for keyword in T4_KEYWORDS):
        return DocumentDocKindEnum.T4
    elif any(keyword in text for keyword in ID_KEYWORDS):
        return DocumentDocKindEnum.id
    else:
        return DocumentDocKindEnum.unknown #returns unknown if no keywords are found
    
def normalize_text(text: str) -> str:
    compacted_lowercased_unicoded_text = unidecode(text).lower().replace(" ", "").replace("\n", "") #normalize text for matching by removing non-ASCII characters, converting to lowercase and remove spaces and newlines for matching
    return compacted_lowercased_unicoded_text

def receive_checklist_item(document_classification: DocumentDocKindEnum, intake_id: int, session: Session):
    if document_classification == DocumentDocKindEnum.unknown: #only look for missing checklist item if we have successfully classified the current document
        return
    
    matching_missing_checklist_item = session.exec( #look for checklist item of intake that is still missing and matches the document classification 
        select(ChecklistItem).where(
            ChecklistItem.intake_id == intake_id,
            ChecklistItem.doc_kind == document_classification,
            ChecklistItem.status == ChecklistItemStatusEnum.missing
        )
    ).first()
    if matching_missing_checklist_item: #if missing item exists, we have just received it so mark status as received
        matching_missing_checklist_item.status = ChecklistItemStatusEnum.received
        session.add(matching_missing_checklist_item)

def update_intake_status(intake_id: int, session: Session):

    intake_checklist = session.exec( #fetch intake checklist items
        select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
    ).all()
    if all(item.status == ChecklistItemStatusEnum.received for item in intake_checklist): #if all intake items are received then intake should be done
        intake = session.get(Intake, intake_id)
        intake.status = IntakeStatusEnum.done
        session.add(intake)