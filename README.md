# Pdf reader, draft generator and Learning from edited input

This system reads noisy legal documents (scanned PDFs, handwritten notes, and inconsistent documents) and extracts the useful information, it conducts grounded retrieval and produces structured documents and builds its knowledge over time by learning from the corrections made by the operator.

# Features

- **Text Extraction** : PDF text extraction, OCR fallback, structured field extraction (dates, amounts, case numbers)
Collaborate on the use of evidence with page citations, grounded retrieval using vector search with ChromaDB.
- Draft Generation: Only grounded draft generation based on rules, 100% based on the evidence
- **Introducing New Features**: GUI enhancements, improved reference documentation, preference system, SQLite support, etc.
- **Web UI**: Easy-to-use interface to upload, draft and edit documents
- **Fast API**: Complete API endpoints for programmatic access

# How to Run:

- First clone the repository
- Then run cd Pdf_reader
- Then create virtual environment 
- Run pip install -r requirements.txt
- Run uvicorn main:app --reload --port 8002

