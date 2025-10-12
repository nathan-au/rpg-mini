from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///database.db" #SQLite database will be stored in database.db
engine = create_engine(DATABASE_URL) #SQLAlchemy Engine allows for database interaction

def create_database_tables():
    SQLModel.metadata.create_all(engine) #creates SQLModel defined tables (that dont already exist) and adds to database