from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from database.models import Client, ClientCreate
from database.database import engine

router = APIRouter(prefix="/clients", tags=["Clients"]) #APIRouter allows endpoints to be grouped together instead of everything in one file, prefix /clients means all endpoints in this router will start with /clients, tags for grouping in docs

@router.post("/", status_code=201) #POST endpoint to create new client
def create_client(client_data: ClientCreate): #input is validated against ClientCreate model
    client = Client(**client_data.model_dump())  #convert Pydantic ClientCreate model into SQLModel Client object, model_dump "unpacks" client data
    with Session(engine) as session: #opens engine (database) session
        session.add(client) #kind of like git, session add will stage new changes
        session.commit() #also like git, commit will actually make the change
        session.refresh(client) #refresh to retrive auto generated fields
        return { #returns new client as JSON
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "complexity": client.complexity,
            "created_at": client.created_at
        }