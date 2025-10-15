from fastapi.testclient import TestClient
from main import app

client = TestClient(app) #TestClient allows for testing in FastAPI without running live server (uvicorn)

def test_root():
    root_response = client.get("/") #tests root endpoint of app
    assert root_response.status_code == 200 #makes sure status code returns 200
    root_response_json = root_response.json()
    assert root_response_json["message"] == "Welcome to RPG-Mini" #makes sure message in response json is Welcome to RPG-Mini
    assert root_response_json["docs_url"] == "/docs" #makes sure docs_url is /docs