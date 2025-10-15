from fastapi import FastAPI
from database.database import create_database_tables
from endpoints import clients, intakes, documents

create_database_tables() #call function to create database tables 

app = FastAPI( #creates new FastAPI app instance
    title="RPG-Mini: Accounting Automation", #title shown in docs
    description="Developed by Nathan Au" #description shown in docs
)

app.include_router(clients.router) #include routers from endpoints
app.include_router(intakes.router)
app.include_router(documents.router)

@app.get("/")
def hello_rpg_mini():
    return {"Hello": "RPG-Mini"}