from enums import DocumentDocKindEnum, ChecklistItemStatusEnum, IntakeStatusEnum
from uuid import UUID
from sqlmodel import Session, select
from database.models import ChecklistItem, Intake

def mark_checklist_item_received(document_classification: DocumentDocKindEnum, intake_id: UUID, session: Session):
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

def mark_intake_received(intake_id: UUID, session: Session):
    intake_checklist = session.exec( #fetch intake checklist items
        select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
    ).all()
    if all(item.status in [ChecklistItemStatusEnum.received, ChecklistItemStatusEnum.extracted]for item in intake_checklist): #if all intake items are received then intake should be done
        intake = session.get(Intake, intake_id)
        intake.status = IntakeStatusEnum.received
        session.add(intake)

def mark_checklist_item_extracted(extracted_fields: dict | None, document_classification: DocumentDocKindEnum, intake_id: UUID, session: Session):
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
def mark_intake_extracted(intake_id: UUID, session: Session):
    intake_checklist = session.exec( #fetch intake checklist items
        select(ChecklistItem).where(ChecklistItem.intake_id == intake_id)
    ).all()
    if all(item.status == ChecklistItemStatusEnum.extracted for item in intake_checklist): #if all intake items are received then intake should be done
        intake = session.get(Intake, intake_id)
        intake.status = IntakeStatusEnum.done
        session.add(intake)