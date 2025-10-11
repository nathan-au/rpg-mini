from sqlmodel import Session, select
from models import Client, Intake, Document
from main import engine

with Session(engine) as session:
    clients = session.exec(select(Client)).all()
    intakes = session.exec(select(Intake)).all()
    documents = session.exec(select(Document)).all()

print(clients, intakes, documents)