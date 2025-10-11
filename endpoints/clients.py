from fastapi import APIRouter
from sqlmodel import Session, select
from models import Client, ClientCreate
from database import engine

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/")
def create_client(client_data: ClientCreate):
    client = Client(**client_data.model_dump())
    with Session(engine) as session:
        session.add(client)
        session.commit()
        session.refresh(client)
        return client
    
@router.get("/")
def TEMP_read_clients():
    with Session(engine) as session:
        clients = session.exec(select(Client)).all()
        return clients