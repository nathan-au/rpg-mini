# rpg-mini: AI-Powered Tax Accounting Automation

![rpg-mini](https://github.com/user-attachments/assets/d3dfa410-5bff-4fbc-8630-e05ef96bdf86)

## Project Overview

RPG-Mini is an end-to-end backend framework designed to support accounting professionals who manage numerous clients and document intakes. The system automates repetitive administrative tasks, such as document collection, categorization, and field extraction, to allow accountants to focus on review and decision-making rather than manual data entry.

## Key Features

- **Client & Intake Management:** Manage clients by complexity and create separate intakes for each fiscal year to maintain organized tracking.  
- **Smart Document Uploads:** Upload multiple files that are automatically validated, stored, and linked to the correct client intake.  
- **Automated Document Classification:** Identify document types using OCR and keyword-based detection to eliminate manual sorting and accelerate intake verification.  
- **Data Fields Extraction:** Extract information from scanned or photographed documents into structured data fields in the database.
- **Dynamic Checklist Tracking:** Automatically update intake and checklist statuses as documents are classified and extracted.
- **Batch and Single Processing:** Run classification or extraction on all intake documents at once or handle them individually for precise control.  

## Architecture

The architecture follows a linear workflow: Client -> Intake -> Document Upload -> Classification -> Extraction -> Checklist. Each stage is tied to domain models and API endpoints for automation and integration with downstream accounting processes.

### 1. Client Creation
**Endpoint:** `POST /clients/`  
A client is created with basic information (name, email) and a complexity level (simple, average, complex). The complexity determines the number and types of expected documents for all future intakes and is permanent once set. For example, a "simple" client only requires a T4 and id, while a "complex" client also requires 5 receipts.

### 2. Intake Creation
**Endpoint:** `POST /intakes/`  
An intake represents a fiscal-year accounting case for a client. Upon intake creation, RPG-Mini generates a dynamic checklist based on the client's complexity and sets the intake status to open.

### 3. Document Upload
**Endpoint:** `POST /intakes/{intake_id}/documents`  
Documents can be uploaded in PDF, JPG, or PNG formats. Each file is validated, stored in an upload directory, and assigned a SHA256 hash to prevent duplicate uploads. Metadata such as file size, MIME type, and upload timestamp is also recorded.

### 4. Document Classification
**Endpoints:**  
Batch: `POST /intakes/{intake_id}/classify`  
Single: `POST /documents/{document_id}/classify`
<br>
RPG-Mini reads text using OCR (PyMuPDF + pytesseract) and applies rule-based logic for keyword matching. The algorithm first attempts to classify based on the filename. If this initial attempt is not successful, the document's content is then extracted using OCR and scanned for keywords. The document is ultimately classified as one of the known types (T4, receipt, or ID), or marked as unknown if neither layer provides a match. This two-step process ensures both efficiency for clearly named files and robustness for files that require content-based inspection.

### 5. Data Extraction
**Endpoints:**  
Batch: `POST /intakes/{intake_id}/extract`  
Single: `POST /documents/{document_id}/extract`
<br>
After classification, the program performs data extraction. OCR text is fed into a lightweight LLM (currently gemma3) with customized prompts to identify structured fields such as names, dates, income amounts, and employer details. The extracted values are saved to the database for reporting or export to accounting software. This step converts unstructured data (like a scanned T4) into structured, machine-readable form (JSON).

### 6. Checklist Management and Intake Completion
**Endpoint:** `GET /intakes/{intake_id}/checklist`  
Each intake has a dynamic checklist that updates as documents are classified and extracted. When all required items are marked complete, the intake status automatically changes to "done". Throughout the process: "open" means intake created but no files yet, "received" means files uploaded and classified, and "done" meanas all expected documents extracted and checklist items completed.

## Technologies Used
- **Python** - Core programming language for all backend logic.
- **FastAPI** - Python web framework used for all API endpoints.  
- **SQLModel** - ORM for defining and managing relational data models.  
- **SQLite** - Database for storing clients, intakes, documents, and extracted data.  
- **pytesseract** - OCR engine for reading text from scanned images and PDFs.  
- **ollama** - Local model runner used for structured field extraction from OCR text.  
- **Uvicorn** - ASGI server for local or production deployment of the FastAPI app.

## Installation

Follow these steps to install and run RPG-Mini locally.

### 1. Clone the Repository
```bash
git clone https://github.com/nathan-au/rpg-mini.git
cd rpg-mini
```
### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```
### 3. Install Required Packages
```bash
pip install fastapi uvicorn sqlmodel pydantic pymupdf pytesseract pdf2image unidecode pytest ollama
```
### 4. Install Tesseract OCR 
macOS:
```bash
brew install tesseract
```
Ubuntu/Debian:
```bash
sudo apt install tesseract-ocr
```
Windows: 
<br>
Download and install from [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)
<br>

Verify the installation:
```bash
tesseract --version
```
### 5. Install Ollama 
Download and install from [https://ollama.com/download](https://ollama.com/download)
<br>
<br>
Verify the installation:
```bash
ollama --version
```
Pull the Gemma3 model
```bash
ollama pull gemma3
```
Check that the model is available:
```bash
ollama list
```
Ollama usually runs automatically after installation. If it is not active, start it manually:
```bash
ollama serve
```
### 6. Run the FastAPI Application
Start the development server:
```bash
uvicorn main:app --reload
```
Access the API:
```bash
http://localhost:8000
```
Open the interactive API documentation
```bash
http://localhost:8000/docs
```
### 7. Try Example Workflow
1.	Create a client -> POST /clients/ <br>
2.	Create an intake -> POST /intakes/ <br>
3.	Upload documents -> POST /intakes/{intake_id}/documents <br>
4.	Classify documents -> POST /intakes/{intake_id}/classify <br>
5.	Extract data -> POST /intakes/{intake_id}/extract <br>
6.	Check progress -> GET /intakes/{intake_id}/checklist <br>

### 8. Run Tests (optional)
```bash
pytest -v
```

## Future Improvements
- **ML Document Classification/Extraction** - Integrate machine learning models for more precise classification and extraction (maybe using LayoutLM, transformers or Donut).  
- **User Authentication/Authorization** - Add role-based access for clients/staff/admins with secure authentication and authorization.  
- **Web-based Frontend** – Build a Vue.js interface for management of client/intake creation, document uploads, classification/extraction processes, and status checking with a nice UI.  
- **Cloud Storage Integration** - Connect a cloud storage service for scalable backend document/data storage.  
- **Isolated Testing Pipeline** - Create a dedicated test database and continuous integration pipeline for unit and integration testing.
