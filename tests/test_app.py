from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_app_201():
    #create client
    test_client_data = {
        "name": "Test Client",
        "email": "testclient@example.com",
        "complexity": "simple"
    }
    client_response = client.post("/clients/", json=test_client_data)
    assert client_response.status_code == 201
    client_response_json = client_response.json()
    assert "id" in client_response_json
    assert client_response_json["name"] == test_client_data["name"]
    assert client_response_json["email"] == test_client_data["email"]
    assert client_response_json["complexity"] == test_client_data["complexity"]
    assert "created_at" in client_response_json
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
    assert "id" in intake_intake_response_json
    assert intake_intake_response_json["client_id"] == test_intake_data["client_id"]
    assert intake_intake_response_json["fiscal_year"] == test_intake_data["fiscal_year"]
    assert intake_intake_response_json["status"] == "open"
    assert "created_at" in intake_intake_response_json

    intake_checklist_intake_response_json = intake_response_json["intake_checklist"]
    for intake_checklist_item in intake_checklist_intake_response_json:
        checklist_item = intake_checklist_item["checklist_item"]
        assert "id" in checklist_item
        assert checklist_item["doc_kind"] in ["T4", "id"]
        assert checklist_item["status"] == "missing"
        assert "created_at" in checklist_item

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
    document_1_upload_response_json = document_1_upload_response.json()

    assert "id" in document_1_upload_response_json
    assert document_1_upload_response_json["filename"] == test_document_1_data["filename"]
    assert "sha256" in document_1_upload_response_json
    assert document_1_upload_response_json["mime_type"] == test_document_1_data["mime_type"]
    assert "size_bytes" in document_1_upload_response_json
    assert "stored_path" in document_1_upload_response_json
    assert "uploaded_at" in document_1_upload_response_json
    assert document_1_upload_response_json["doc_kind"] == "unknown"
    assert document_1_upload_response_json["extracted_fields"] == None

    #upload id
    test_document_2_data = {
        "file_path": "./tests/sample_docs/drivers_license.jpg",

        "filename": "drivers_license.jpg",
        "mime_type": "image/jpeg"
    }
    with open(test_document_2_data["file_path"], "rb") as f:
        files = {"file": (test_document_2_data["filename"], f, test_document_2_data["mime_type"])}
        document_2_upload_response = client.post(f"/intakes/{test_intake_id}/documents", files=files)
    assert document_2_upload_response.status_code == 201
    document_2_upload_response_json = document_2_upload_response.json()

    assert "id" in document_2_upload_response_json
    assert document_2_upload_response_json["filename"] == test_document_2_data["filename"]
    assert "sha256" in document_2_upload_response_json
    assert document_2_upload_response_json["mime_type"] == test_document_2_data["mime_type"]
    assert "size_bytes" in document_2_upload_response_json
    assert "stored_path" in document_2_upload_response_json
    assert "uploaded_at" in document_2_upload_response_json
    assert document_2_upload_response_json["doc_kind"] == "unknown"
    assert document_2_upload_response_json["extracted_fields"] == None

    #classify documents
    classification_response = client.post(f"/intakes/{test_intake_id}/classify")
    assert classification_response.status_code == 200

    classification_response_json = classification_response.json()

    intake_classification_response_json = classification_response_json["intake"]
    assert "id" in intake_classification_response_json
    assert intake_classification_response_json["status"] == "received"

    classified_documents = classification_response_json["classified_documents"]
    assert len(classified_documents) == 2

    classified_document_1 = classified_documents[0]["classified_document"]
    assert "document_id" in classified_document_1
    assert classified_document_1["filename"] == test_document_1_data["filename"]
    assert classified_document_1["mime_type"] == test_document_1_data["mime_type"]
    assert classified_document_1["doc_kind"] == "T4"
    assert "stored_path" in classified_document_1

    classified_document_2 = classified_documents[1]["classified_document"]
    assert "document_id" in classified_document_2
    assert classified_document_2["filename"] == test_document_2_data["filename"]
    assert classified_document_2["mime_type"] == test_document_2_data["mime_type"]
    assert classified_document_2["doc_kind"] == "id"
    assert "stored_path" in classified_document_2

    #extract documents
    extraction_response = client.post(f"/intakes/{test_intake_id}/extract")
    assert extraction_response.status_code == 200

    extraction_response_json = extraction_response.json()

    intake_extraction_response_json = extraction_response_json["intake"]
    assert "id" in intake_extraction_response_json
    assert intake_extraction_response_json["status"] == "done"

    extracted_documents = extraction_response_json["extracted_documents"]
    assert len(extracted_documents) == 2
    
    extracted_document_1 = extracted_documents[0]["extracted_document"]
    assert "document_id" in extracted_document_1
    assert extracted_document_1["filename"] == test_document_1_data["filename"]
    assert extracted_document_1["mime_type"] == test_document_1_data["mime_type"]
    assert extracted_document_1["doc_kind"] == classified_document_1["doc_kind"]
    assert "stored_path" in extracted_document_1
    extracted_fields_extracted_document_1 = extracted_document_1["extracted_fields"]
    assert "employer_name" in extracted_fields_extracted_document_1
    assert "box_14_employment_income" in extracted_fields_extracted_document_1
    assert "box_22_income_tax_deducted" in extracted_fields_extracted_document_1

    extracted_document_2 = extracted_documents[1]["extracted_document"]
    assert "document_id" in extracted_document_2
    assert extracted_document_2["filename"] == test_document_2_data["filename"]
    assert extracted_document_2["mime_type"] == test_document_2_data["mime_type"]
    assert extracted_document_2["doc_kind"] == classified_document_2["doc_kind"]
    assert "stored_path" in extracted_document_2
    extracted_fields_extracted_document_2 = extracted_document_2["extracted_fields"]
    assert "full_name" in extracted_fields_extracted_document_2
    assert "date_of_birth" in extracted_fields_extracted_document_2
    assert "id_number" in extracted_fields_extracted_document_2
