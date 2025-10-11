from fastapi import FastAPI, UploadFile, File
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select
from hashlib import sha256
import os


from models import Client,ClientCreate, Intake, IntakeCreate, ChecklistItem, Document
from enums import ClientComplexityEnum, IntakeStatusEnum, ChecklistItemDocKindEnum, ChecklistItemStatusEnum, DocumentDocKindEnum

from database import engine, init_database_tables
from endpoints import clients, intakes

init_database_tables()

app = FastAPI( title="RPG-Mini: Accounting Automation", contact={"name": "Ready Plan Go", "url": "https://readyplango.com/"})
app.include_router(clients.router)
app.include_router(intakes.router)




