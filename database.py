from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///database.db"
engine = create_engine(DATABASE_URL)

def init_database_tables():
    SQLModel.metadata.create_all(engine)