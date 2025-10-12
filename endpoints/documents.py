
from fastapi import APIRouter
from sqlmodel import Session, select
from database import engine
from models import Document, ChecklistItem, Intake
from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum

import pymupdf #for pdf text extraction
import pytesseract #for image text extraction
from PIL import Image #for image handling

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/{document_id}/classify") #POST endpoint to classify one singular document
def classify_document(document_id: int):
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if not document:
            return {"error": "Document not found"}

        filename = document.filename.lower() #convert file name to lowercase to ignore case for matching
        document_kind = None #create variable to store classification

        #classification step 1 checks file name for keywords to classify documents
        if "t4" in filename: #if t4 is found in file name then document is classified as DocumentDocKindEnum T4
            document_kind = DocumentDocKindEnum.T4
        elif "receipt" in filename:
            document_kind = DocumentDocKindEnum.receipt
        elif "license" in filename:
            document_kind = DocumentDocKindEnum.id
        else:
            #if step 1 does not work, classification step 2 checks file contents for keywords to classify documents
            stored_path = document.stored_path #file path of uploaded document from database
            text = "" #empty text variable to store file contents

            try:
                if stored_path.endswith(".pdf"): #if file is pdf then use PyMuPDF to get text from file 
                    pdf = pymupdf.open(stored_path)
                    for page in pdf:
                        text += page.get_text("text") #iterate over all pages in the pdf and put in text variable
                    pdf.close() #save system resources by closing file afterwards
                elif stored_path.endswith((".png", ".jpg", ".jpeg")): #if file is image then use pytesseract OCR (optical character recognition) to convert image to string
                    img = Image.open(stored_path) #open image with PIL.Image
                    text = pytesseract.image_to_string(img)
            except Exception as e: #triggers if an Exception occurs inside try
                print(f"Extraction/OCR failed: {e}")

            text_lower = text.lower() #convert file contents to lowercase 
            if "t4" in text_lower: #search for keywords in file contents to classify document
                document_kind = DocumentDocKindEnum.T4
            elif "receipt" in text_lower:
                document_kind = DocumentDocKindEnum.receipt
            elif "license" in text_lower:
                document_kind = DocumentDocKindEnum.id
            else:
                document_kind = DocumentDocKindEnum.unknown #if document cant be classified then DocumentDocKindEnum unknown

        document.doc_kind = document_kind #set doc_kind in document in Document table to type that it has been classified as
        session.add(document)

        if document_kind != DocumentDocKindEnum.unknown: #if document successfully classified then look at intake checklist for missing documents of same classification and still missing then set to received
            checklist_item = session.exec(
                select(ChecklistItem).where(
                    ChecklistItem.intake_id == document.intake_id,
                    ChecklistItem.doc_kind == document_kind,
                    ChecklistItem.status == ChecklistItemStatusEnum.missing
                )
            ).first()
            if checklist_item:
                checklist_item.status = ChecklistItemStatusEnum.received
                session.add(checklist_item)

        all_items = session.exec( #fetch all checklist items for intake
            select(ChecklistItem).where(ChecklistItem.intake_id == document.intake_id)
        ).all()
        if all(item.status == ChecklistItemStatusEnum.received for item in all_items): #if every item is received then intake status set to done
            intake = session.get(Intake, document.intake_id)
            intake.status = IntakeStatusEnum.done
            session.add(intake)

        session.commit() #commit document and checklist and intake changes to database
        session.refresh(document)

        return { #return JSON
            "document_id": document.id,
            "filename": document.filename,
            "classified_as": document.doc_kind,
        }