from pydantic import BaseModel
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from enums import ClientComplexityEnum, IntakeStatusEnum, ChecklistItemDocKindEnum, ChecklistItemStatusEnum, DocumentDocKindEnum #import enums from enums.py to have access to fixed choices in models
import uuid

class Client(SQLModel, table=True): #defines SQLModel Client class and indicates corresponding database table
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True) #client id is type UUID, UUID is auto generated, default_factory is used when function is called to set value (default is used when static value is set), primary key means the unique identifier for row in table
    name: str #client name is type string
    email: str 
    complexity: ClientComplexityEnum #use ClientComplexityEnum to set fixed options for client complexity
    created_at: datetime = Field(default_factory=datetime.now) #datetime is auto generated

class ClientCreate(BaseModel): #ClientCreate BaseModel is used to validate client creation input, id and created_at excluded since they are auto generated
    name: str
    email: str
    complexity: ClientComplexityEnum

class Intake(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="client.id") #foreign key links an intake to a specific client by client id
    fiscal_year: int
    status: IntakeStatusEnum = Field(default=IntakeStatusEnum.open) #intake status is set to default to open (using IntakeStatusEnum)
    created_at: datetime = Field(default_factory=datetime.now)

class IntakeCreate(BaseModel):
    client_id: uuid.UUID #client id is used to verify that the client actually exits when creating an intake for them
    fiscal_year: int

class ChecklistItem(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    intake_id: uuid.UUID = Field(foreign_key="intake.id")
    doc_kind: ChecklistItemDocKindEnum
    status: ChecklistItemStatusEnum = Field(default=ChecklistItemStatusEnum.missing)
    created_at: datetime = Field(default_factory=datetime.now)

class Document(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    intake_id: uuid.UUID = Field(foreign_key="intake.id")
    filename: str
    sha256: str = Field(max_length=64) #SHA-256 hash always returns 64 characters in hexadecimal
    mime_type: str
    size_bytes: int
    stored_path: str
    uploaded_at: datetime = Field(default_factory=datetime.now)
    doc_kind: DocumentDocKindEnum = Field(default=DocumentDocKindEnum.unknown)
    extracted_fields: dict | None = Field(default=None, sa_column=Column(JSON))