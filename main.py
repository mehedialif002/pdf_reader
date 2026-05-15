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

app = FastAPI(title="Legal AI — Pearson Specter Litt")

# CORS middleware যোগ করুন (এটি favicon error সমাধান করে)
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


# favicon.ico error সমাধানের জন্য
@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204, content={})


# Main UI
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal AI System - Pearson Specter Litt</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
        }

        .header h1 {
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 16px;
        }

        .badge {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 25px;
            margin-bottom: 25px;
        }

        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .card h2 {
            color: #333;
            font-size: 22px;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .card h3 {
            color: #555;
            font-size: 18px;
            margin: 20px 0 10px 0;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 14px;
        }

        input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px dashed #ddd;
            border-radius: 8px;
            cursor: pointer;
            background: #fafafa;
        }

        input[type="text"], 
        textarea, 
        select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }

        textarea {
            resize: vertical;
            font-family: 'Courier New', monospace;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            margin-right: 10px;
            margin-top: 10px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .result-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
        }

        .result-box pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
        }

        .evidence-item {
            background: white;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .citation {
            color: #667eea;
            font-weight: bold;
            font-size: 12px;
            margin-bottom: 8px;
        }

        .alert {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                transform: translateY(-10px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            transition: all 0.3s;
        }

        .stat-card:hover {
            transform: scale(1.05);
        }

        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚖️ Legal AI System</h1>
            <p>Pearson Specter Litt - Intelligent Document Processing & Drafting</p>
            <span class="badge">🤖 Claude AI Powered | 📚 Grounded Generation | ✨ Learning from Edits</span>
        </div>

        <!-- Stats Bar -->
        <div class="card">
            <h2>📊 System Status</h2>
            <div id="stats"></div>
        </div>

        <div class="grid">
            <!-- Document Upload Card -->
            <div class="card">
                <h2>📄 1. Upload Document</h2>
                <div class="form-group">
                    <label>Choose legal document (PDF or TXT)</label>
                    <input type="file" id="fileInput" accept=".pdf,.txt">
                </div>
                <button onclick="processDocument()" id="processBtn">🚀 Process Document</button>
                <div id="processResult"></div>
            </div>

            <!-- Draft Generation Card -->
            <div class="card">
                <h2>✍️ 2. Generate Draft</h2>
                <div class="form-group">
                    <label>Query / Drafting Task</label>
                    <textarea id="query" rows="3" placeholder="Example: Summarize the key facts about the breach of contract...">summarize the key facts and legal issues</textarea>
                </div>
                <div class="form-group">
                    <label>Draft Type</label>
                    <select id="draftType">
                        <option value="case_summary">📋 Case Fact Summary</option>
                        <option value="notice_summary">📢 Notice Summary</option>
                        <option value="legal_memo">📝 Legal Memo</option>
                        <option value="document_checklist">✅ Document Checklist</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Number of Evidence Pieces</label>
                    <input type="number" id="nResults" value="5" min="1" max="10">
                </div>
                <button onclick="generateDraft(false)" id="draftBtn">🎯 Generate Draft</button>
                <button onclick="generateDraft(true)" id="improvedBtn" class="btn-secondary">✨ Generate with Learning</button>
                <div id="draftResult"></div>
            </div>
        </div>

        <div class="grid">
            <!-- Edit & Learn Card -->
            <div class="card">
                <h2>✏️ 3. Edit & Improve</h2>
                <div class="form-group">
                    <label>Edit the draft below (simulate operator review)</label>
                    <textarea id="editedDraft" rows="8" placeholder="Edit the generated draft here..."></textarea>
                </div>
                <button onclick="submitEdit()" id="editBtn">💾 Save Edits & Learn</button>
                <div id="editResult"></div>
                
                <h3 style="margin-top: 20px;">📜 Edit History</h3>
                <button onclick="loadEditHistory()" style="width: 100%;">Load History</button>
                <div id="historyResult"></div>
            </div>

            <!-- Evidence Panel -->
            <div class="card">
                <h2>📚 Evidence & Citations</h2>
                <div id="evidencePanel">
                    <p style="color: #999; text-align: center; padding: 20px;">Generate a draft to see evidence here</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentDraft = "";
        let currentEvidence = [];

        async function processDocument() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                showAlert('processResult', 'Please select a file first', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            const btn = document.getElementById('processBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Processing...';

            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                
                if (response.ok) {
                    let html = '<div class="alert alert-success">✅ Document processed successfully!</div>';
                    html += '<div class="result-box">';
                    html += `<strong>📄 Document:</strong> ${data.doc_id}<br>`;
                    html += `<strong>📑 Pages:</strong> ${data.pages}<br>`;
                    html += `<strong>📝 Characters:</strong> ${data.chars}<br>`;
                    html += `<strong>⭐ Quality:</strong> ${data.quality}<br><br>`;
                    html += `<strong>🏷️ Structured Fields:</strong><br>`;
                    html += `📅 Dates: ${data.structured.dates.join(', ') || 'None'}<br>`;
                    html += `💰 Amounts: ${data.structured.amounts.join(', ') || 'None'}<br>`;
                    html += `⚖️ Case Numbers: ${data.structured.case_numbers.join(', ') || 'None'}<br>`;
                    html += `🔑 Key Terms: ${data.structured.key_terms.join(', ') || 'None'}`;
                    html += '</div>';
                    document.getElementById('processResult').innerHTML = html;
                    loadStats();
                } else {
                    showAlert('processResult', `Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert('processResult', `Error: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🚀 Process Document';
            }
        }

        async function generateDraft(useLearning = false) {
            const query = document.getElementById('query').value;
            const draftType = document.getElementById('draftType').value;
            const nResults = parseInt(document.getElementById('nResults').value);

            if (!query) {
                showAlert('draftResult', 'Please enter a query', 'error');
                return;
            }

            const btn = useLearning ? document.getElementById('improvedBtn') : document.getElementById('draftBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Generating...';

            try {
                const endpoint = useLearning ? '/improved-draft' : '/draft';
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: query,
                        draft_type: draftType,
                        n_results: nResults
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    currentDraft = data.draft;
                    currentEvidence = data.evidence_used || [];
                    
                    let draftHtml = '<div class="alert alert-success">✅ Draft generated successfully!</div>';
                    draftHtml += '<div class="result-box">';
                    draftHtml += `<strong>📝 Generated Draft ${useLearning ? '(with Learning)' : '(Default)'}:</strong><br><br>`;
                    draftHtml += `<pre>${data.draft}</pre>`;
                    
                    if (data.preferences_applied && data.preferences_applied.length > 0) {
                        draftHtml += `<br><strong>✨ Preferences Applied:</strong><br>`;
                        data.preferences_applied.forEach(pref => {
                            draftHtml += `• ${pref}<br>`;
                        });
                    }
                    
                    draftHtml += `<br><strong>📌 Citations:</strong> ${data.citations.join(', ')}<br>`;
                    draftHtml += `<strong>🔍 Evidence Pieces:</strong> ${data.evidence_count}`;
                    draftHtml += '</div>';
                    
                    document.getElementById('draftResult').innerHTML = draftHtml;
                    document.getElementById('editedDraft').value = data.draft;
                    displayEvidence(data.evidence_used);
                } else {
                    showAlert('draftResult', `Error: ${data.detail || 'No documents indexed. Please upload a document first.'}`, 'error');
                }
            } catch (error) {
                showAlert('draftResult', `Error: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = useLearning ? '✨ Generate with Learning' : '🎯 Generate Draft';
            }
        }

        async function submitEdit() {
            const editedText = document.getElementById('editedDraft').value;
            
            if (!currentDraft) {
                showAlert('editResult', 'Please generate a draft first', 'error');
                return;
            }
            
            if (!editedText) {
                showAlert('editResult', 'Please edit the draft', 'error');
                return;
            }

            const btn = document.getElementById('editBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Saving...';

            try {
                const response = await fetch('/edit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        original: currentDraft,
                        edited: editedText,
                        doc_id: "current_document",
                        draft_type: document.getElementById('draftType').value
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    let html = '<div class="alert alert-success">✅ Edit saved! Learned patterns:</div>';
                    html += '<div class="result-box">';
                    data.patterns.forEach(pattern => {
                        html += `• ${pattern}<br>`;
                    });
                    html += '</div>';
                    document.getElementById('editResult').innerHTML = html;
                    loadStats();
                    showAlert('editResult', 'Edit saved and patterns learned!', 'success');
                } else {
                    showAlert('editResult', `Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert('editResult', `Error: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '💾 Save Edits & Learn';
            }
        }

        function displayEvidence(evidence) {
            if (!evidence || evidence.length === 0) {
                document.getElementById('evidencePanel').innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No evidence available</p>';
                return;
            }
            
            let html = '';
            evidence.forEach((ev, idx) => {
                html += `
                    <div class="evidence-item">
                        <div class="citation">📖 Page ${ev.page} | Relevance: ${(ev.relevance || 0.5).toFixed(2)}</div>
                        <div style="margin-top: 8px; font-size: 13px;">${ev.text.substring(0, 300)}${ev.text.length > 300 ? '...' : ''}</div>
                    </div>
                `;
            });
            document.getElementById('evidencePanel').innerHTML = html;
        }

        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();
                
                let statsHtml = '<div class="stats-grid">';
                statsHtml += `
                    <div class="stat-card">
                        <div class="stat-number">${data.retrieval.total_chunks}</div>
                        <div class="stat-label">Document Chunks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.learning.total_edits}</div>
                        <div class="stat-label">Edits Learned</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${data.learning.preferences.length}</div>
                        <div class="stat-label">Active Preferences</div>
                    </div>
                `;
                statsHtml += '</div>';
                
                if (data.learning.preferences.length > 0) {
                    statsHtml += '<div class="result-box" style="margin-top: 15px;"><strong>🎯 Learned Preferences:</strong><br>';
                    data.learning.preferences.slice(0, 5).forEach(pref => {
                        statsHtml += `• ${pref}<br>`;
                    });
                    statsHtml += '</div>';
                }
                
                document.getElementById('stats').innerHTML = statsHtml;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        async function loadEditHistory() {
            try {
                const response = await fetch('/edit-history');
                const data = await response.json();
                
                if (data.edits && data.edits.length > 0) {
                    let historyHtml = '<div class="result-box">';
                    data.edits.slice(0, 5).forEach(edit => {
                        historyHtml += `<div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">`;
                        historyHtml += `<strong>✏️ Edit #${edit.id}</strong><br>`;
                        historyHtml += `<small>${new Date(edit.created_at).toLocaleString()}</small><br>`;
                        historyHtml += `<strong>Patterns:</strong> ${edit.patterns.join(', ')}<br>`;
                        historyHtml += `</div>`;
                    });
                    historyHtml += '</div>';
                    document.getElementById('historyResult').innerHTML = historyHtml;
                } else {
                    document.getElementById('historyResult').innerHTML = '<div class="alert alert-info">No edits recorded yet</div>';
                }
            } catch (error) {
                console.error('Error loading history:', error);
            }
        }

        function showAlert(elementId, message, type) {
            const alertClass = type === 'success' ? 'alert-success' : (type === 'error' ? 'alert-error' : 'alert-info');
            const html = `<div class="alert ${alertClass}">${message}</div>`;
            document.getElementById(elementId).innerHTML = html;
            
            setTimeout(() => {
                const alertDiv = document.querySelector(`#${elementId} .alert`);
                if (alertDiv) alertDiv.remove();
            }, 5000);
        }

        // Load stats on page load
        loadStats();
        
        // Auto-refresh stats every 30 seconds
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
    """


# Your existing API endpoints
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
    uvicorn.run(app, host="0.0.0.0", port=8000)