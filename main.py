from fastapi import FastAPI
from database import init_database_tables
from endpoints import clients, intakes, documents
init_database_tables()

app = FastAPI( title="RPG-Mini: Accounting Automation", contact={"name": "Ready Plan Go", "url": "https://readyplango.com/"})

app.include_router(clients.router)
app.include_router(intakes.router)
app.include_router(documents.router)
