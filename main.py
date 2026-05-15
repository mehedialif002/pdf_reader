# main.py - পুরো ফাইল এভাবে দিন

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from dotenv import load_dotenv

load_dotenv()

from processing.extractor import DocumentExtractor
from retrieval.retriever import DocumentRetriever
from generation.drafter import DraftGenerator
from improvement.learner import EditLearner

app = FastAPI(title="Pdf reader and Draft generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extractor = DocumentExtractor()
retriever = DocumentRetriever(persist_dir="./chroma_db")
drafter = DraftGenerator()
learner = EditLearner(db_path="./edits.db")

os.makedirs("./uploads", exist_ok=True)


class DraftRequest(BaseModel):
    query: str = "summarize the key facts"
    draft_type: str = "case_summary"
    n_results: int = 5


class EditRequest(BaseModel):
    original: str
    edited: str
    doc_id: Optional[str] = None
    draft_type: Optional[str] = None


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content={})


@app.get("/", response_class=HTMLResponse)
async def root():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Legal AI System</title>
</head>
<body>

<h1>Legal AI System - Pearson Specter Litt</h1>
<hr>

<h2>1. Upload Document</h2>
<input type="file" id="fileInput" accept=".pdf,.txt">
<button onclick="processDocument()">Process</button>
<div id="processResult"></div>

<hr>

<h2>2. Generate Draft</h2>
<textarea id="query" rows="3" cols="50">summarize the key facts</textarea><br>
<select id="draftType">
    <option value="case_summary">Case Summary</option>
    <option value="legal_memo">Legal Memo</option>
</select><br>
<button onclick="generateDraft(false)">Generate Draft</button>
<button onclick="generateDraft(true)">Generate with Learning</button>
<div id="draftResult"></div>

<hr>

<h2>3. Edit & Improve</h2>
<textarea id="editedDraft" rows="6" cols="50" placeholder="Edit the draft here..."></textarea><br>
<button onclick="submitEdit()">Save Edits</button>
<div id="editResult"></div>

<hr>

<h2>4. System Stats</h2>
<button onclick="loadStats()">Refresh Stats</button>
<div id="stats"></div>

<script>
let currentDraft = "";

async function processDocument() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) {
        alert("Select a file first");
        return;
    }
    
    const formData = new FormData();
    formData.append("file", file);
    
    const response = await fetch("/process", { method: "POST", body: formData });
    const data = await response.json();
    
    document.getElementById("processResult").innerHTML = 
        "<pre>Processed: " + data.pages + " pages, " + data.chars + " characters\\n" +
        "Quality: " + data.quality + "\\n" +
        "Dates: " + (data.structured.dates.join(", ") || "None") + "\\n" +
        "Amounts: " + (data.structured.amounts.join(", ") || "None") + "</pre>";
}

async function generateDraft(useLearning) {
    const query = document.getElementById("query").value;
    const draftType = document.getElementById("draftType").value;
    
    const endpoint = useLearning ? "/improved-draft" : "/draft";
    const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, draft_type: draftType, n_results: 5 })
    });
    
    const data = await response.json();
    currentDraft = data.draft;
    
    let html = "<pre>" + data.draft + "</pre>";
    html += "<p><b>Citations:</b> " + data.citations.join(", ") + "</p>";
    document.getElementById("draftResult").innerHTML = html;
    document.getElementById("editedDraft").value = data.draft;
}

async function submitEdit() {
    const edited = document.getElementById("editedDraft").value;
    
    const response = await fetch("/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            original: currentDraft, 
            edited: edited,
            draft_type: document.getElementById("draftType").value
        })
    });
    
    const data = await response.json();
    document.getElementById("editResult").innerHTML = 
        "<pre>Saved! Learned patterns:\\n" + data.patterns.join("\\n") + "</pre>";
}

async function loadStats() {
    const response = await fetch("/stats");
    const data = await response.json();
    
    document.getElementById("stats").innerHTML = 
        "<pre>" +
        "Total Chunks: " + data.retrieval.total_chunks + "\\n" +
        "Total Edits: " + data.learning.total_edits + "\\n" +
        "Preferences: " + data.learning.preferences.join(", ") +
        "</pre>";
}

loadStats();
</script>

</body>
</html>
    '''


# আপনার API endpoints (আগের মতোই)
@app.post("/process")
async def process(file: UploadFile = File(...)):
    path = f"./uploads/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = extractor.extract(path)
    chunks = retriever.index_document(file.filename, result["pages"])
    return {
        "doc_id": file.filename,
        "pages": result["total_pages"],
        "chars": result["total_chars"],
        "chunks": chunks,
        "quality": result["quality"],
        "structured": result["structured"]
    }


@app.post("/draft")
def draft(req: DraftRequest):
    evidence = retriever.retrieve(req.query, n_results=req.n_results)
    if not evidence:
        raise HTTPException(404, "No documents indexed. Upload first via /process")
    result = drafter.generate(evidence, req.draft_type)
    return result


@app.post("/edit")
def edit(req: EditRequest):
    return learner.save_edit(req.original, req.edited, req.doc_id, req.draft_type)


@app.post("/improved-draft")
def improved_draft(req: DraftRequest):
    evidence = retriever.retrieve(req.query, n_results=req.n_results)
    if not evidence:
        raise HTTPException(404, "No documents indexed. Upload first via /process")
    preferences = learner.get_preferences(req.draft_type)
    result = drafter.generate(evidence, req.draft_type, preferences)
    result["preferences_applied"] = preferences
    return result


@app.get("/stats")
def stats():
    return {"retrieval": retriever.get_stats(), "learning": learner.get_stats()}


@app.get("/edit-history")
def edit_history():
    return {"edits": learner.get_history()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)