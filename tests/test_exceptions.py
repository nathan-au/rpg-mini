from fastapi.testclient import TestClient
from main import app 

client = TestClient(app)

def test_create_client_422():
    test_client_data = {
        "name": "Missing Field Client",
        "email": "missingfieldclient@example.com",
        #"complexity" field is missing
    }

    response = client.post("/clients/", json=test_client_data)
    assert response.status_code == 422 #code for HTTPException validation error
    response_json = response.json()
    assert "detail" in response_json

def test_create_intake_404():
    test_intake_data = {
        "client_id": "00000000-0000-0000-0000-000000000000", #client with this id probably does not exist 
        "fiscal_year": 2025,
    }
    intake_response = client.post("/intakes/", json=test_intake_data)
    assert intake_response.status_code == 404 #not found status code

    intake_response_json = intake_response.json()
    intake_response_json["detail"] = "Client not found"

def test_document_upload_409():
    #create client
    test_client_data = {
        "name": "Test Client",
        "email": "testclient@example.com",
        "complexity": "simple"
    }
    client_response = client.post("/clients/", json=test_client_data)
    assert client_response.status_code == 201
    client_response_json = client_response.json()
    test_client_id = client_response_json["id"]

    #create intake
    test_intake_data = {
        "client_id": test_client_id,
        "fiscal_year": 2025,
    }
    intake_response = client.post("/intakes/", json=test_intake_data)
    assert intake_response.status_code == 201

    intake_response_json = intake_response.json()
    intake_intake_response_json = intake_response_json["intake"]
    test_intake_id = intake_intake_response_json["id"]

    #upload t4
    test_document_1_data = {
        "file_path": "./tests/sample_docs/T4_sample.pdf",
        "filename": "T4_sample.pdf",
        "mime_type": "application/pdf"
    }
    with open(test_document_1_data["file_path"], "rb") as f:
        files = {"file": (test_document_1_data["filename"], f, test_document_1_data["mime_type"])}
        document_1_upload_response = client.post(f"/intakes/{test_intake_id}/documents", files=files)
    assert document_1_upload_response.status_code == 201

    #upload t4 again
    test_document_2_data = {
        "file_path": "./tests/sample_docs/T4_sample.pdf",
        "filename": "T4_sample.pdf",
        "mime_type": "application/pdf"
    }
    with open(test_document_2_data["file_path"], "rb") as f:
        files = {"file": (test_document_2_data["filename"], f, test_document_2_data["mime_type"])}
        document_2_upload_response = client.post(f"/intakes/{test_intake_id}/documents", files=files)
    assert document_2_upload_response.status_code == 409
    document_2_upload_response_json = document_2_upload_response.json()
    assert document_2_upload_response_json["detail"] == "Duplicate document found"


def test_document_upload_415():
    #create client
    test_client_data = {
        "name": "Test Client",
        "email": "testclient@example.com",
        "complexity": "simple"
    }
    client_response = client.post("/clients/", json=test_client_data)
    assert client_response.status_code == 201
    client_response_json = client_response.json()
    test_client_id = client_response_json["id"]

    #create intake
    test_intake_data = {
        "client_id": test_client_id,
        "fiscal_year": 2025,
    }
    intake_response = client.post("/intakes/", json=test_intake_data)
    assert intake_response.status_code == 201

    intake_response_json = intake_response.json()
    intake_intake_response_json = intake_response_json["intake"]
    test_intake_id = intake_intake_response_json["id"]

    #upload mp3
    test_document_1_data = {
        "file_path": "./tests/sample_docs/minecraft_xp.mp3",
        "filename": "minecraft_xp.mp3",
        "mime_type": "audio/mpeg"
    }
    with open(test_document_1_data["file_path"], "rb") as f:
        files = {"file": (test_document_1_data["filename"], f, test_document_1_data["mime_type"])}
        document_1_upload_response = client.post(f"/intakes/{test_intake_id}/documents", files=files)
    
    assert document_1_upload_response.status_code == 415
    document_1_upload_response_json = document_1_upload_response.json()
    assert document_1_upload_response_json["detail"] == "Unsupported media type (PDF, PNG and JPG only)"