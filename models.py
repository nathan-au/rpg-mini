from datetime import datetime
from sqlmodel import SQLModel, Field
from enums import ClientComplexityEnum, IntakeStatusEnum, ChecklistItemDocKindEnum, ChecklistItemStatusEnum


class Client(SQLModel, table = True):
    id: int | None = Field(default=None, primary_key=True)    
    name: str
    email: str
    complexity: ClientComplexityEnum
    created_at: datetime = Field(default_factory=datetime.now)

class Intake(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")  # link to Client
    fiscal_year: int
    status: IntakeStatusEnum = Field(default=IntakeStatusEnum.open)
    created_at: datetime = Field(default_factory=datetime.now)

class ChecklistItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    intake_id: int = Field(foreign_key="intake.id")
    doc_kind: ChecklistItemDocKindEnum
    status: ChecklistItemStatusEnum = Field(default=ChecklistItemStatusEnum.missing)
    created_at: datetime = Field(default_factory=datetime.now)



