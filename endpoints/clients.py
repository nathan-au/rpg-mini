from fastapi import APIRouter
from sqlmodel import Session, select
from models import Client, ClientCreate
from database import engine

router = APIRouter(prefix="/clients", tags=["Clients"]) #APIRouter allows endpoints to be grouped together instead of everything in one file, prefix /clients means all endpoints in this router will start with /clients, tags for grouping in docs

@router.post("/") #POST endpoint to create new client
def create_client(client_data: ClientCreate): #input is validated against ClientCreate model
    client = Client(**client_data.model_dump())  #convert Pydantic ClientCreate model into SQLModel Client object, model_dump "unpacks" client data
    with Session(engine) as session: #opens engine (database) session
        session.add(client) #kind of like git, session add will stage new changes
        session.commit() #also like git, commit will actually make the change
        session.refresh(client) #refresh to retrive auto generated fields
        return client #returns new client as JSON
    
@router.get("/") #GET endpoint to fetch all clients
def TEMP_read_clients():
    with Session(engine) as session:
        clients = session.exec(select(Client)).all() #.exec to execute SQL SELECT * FROM Client table
        return clients