from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tiktoken
from groq import Groq
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import time
from dotenv import load_dotenv

# PDF Generation imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- INIT ----------------
load_dotenv()
app = FastAPI()

# ✅ CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- MODELS ----------------
class PromptRequest(BaseModel):
    prompt: str
    edge_mode: bool = True

class CompareRequest(BaseModel):
    prompt1: str
    prompt2: str

# ---------------- TOKEN COUNTING ----------------
def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

# ---------------- ML: TOKEN IMPORTANCE (ADJUSTED) ----------------
STOPWORDS = {"the", "is", "in", "and", "with", "a", "an", "to", "of", "for", "on", "at", "by", "please", "can", "try"}

def get_token_importance(text):
    words = text.split()
    if len(words) < 2:
        return {word: 1.0 for word in words}

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(words)
    base_scores = dict(zip(vectorizer.get_feature_names_out(), X.toarray().sum(axis=0)))

    scores = {}
    for i, word in enumerate(words):
        w = word.lower()
        score = base_scores.get(w, 0)
        
        # FEATURE: Subject Preservation (Boost last word)
        if i == len(words) - 1:
            score += 0.3
            
        # Complexity bonus
        score += len(word) * 0.02
        
        if w in STOPWORDS:
            score *= 0.1
            
        scores[word] = round(score, 3)
    return scores

# ---------------- VISUALIZATION ----------------
def prepare_visualization_data(text, scores):
    words = text.split()
    visualization = []
    for word in words:
        score = scores.get(word, 0)
        level = "high" if score > 0.3 else "medium" if score > 0.12 else "low"
        visualization.append({"word": word, "score": score, "level": level})
    return visualization

# ---------------- TRIMMING (CONTEXT-AWARE) ----------------
def trim_prompt(text, scores):
    words = text.split()
    # STRICT: Remove stopwords, keep technical/high-value words
    trimmed = [
        w for w in words 
        if w.lower() not in STOPWORDS and (scores.get(w, 0) > 0.12 or len(w) > 4)
    ]
    if len(trimmed) < 2:
        trimmed = words
    return " ".join(trimmed)

# ---------------- CORE ANALYZER LOGIC ----------------
def analyze_prompt_logic(prompt, edge_mode=True):
    start_time = time.time()
    
    # 1. Importance Analysis
    importance_scores = get_token_importance(prompt)
    trimmed_prompt = trim_prompt(prompt, importance_scores)
    
    # 2. Hybrid Decision: Send trimmed or full prompt
    final_prompt = trimmed_prompt if edge_mode else prompt
    
    # 3. Cloud LLM Call
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": final_prompt}]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Cloud Connectivity Error: {str(e)}"

    # 4. Metrics & ROI
    orig_t = count_tokens(prompt)
    final_t = count_tokens(final_prompt)
    resp_t = count_tokens(reply)
    savings_pct = round(((orig_t - final_t) / orig_t) * 100, 1) if orig_t else 0

    return {
        "metrics": {
            "prompt_tokens": orig_t,
            "final_tokens": final_t,
            "response_tokens": resp_t,
            "total_tokens": final_t + resp_t,
            "cost_estimate": round((final_t + resp_t) * 0.000001, 6),
            "tokens_saved": orig_t - final_t,
            "savings_percent": savings_pct
        },
        "rag_breakdown": {
            "system": 56, 
            "context": 409, 
            "query": final_t
        },
        "analysis": {
            "importance_scores": importance_scores,
            "trimmed_prompt": trimmed_prompt,
            "visualization": prepare_visualization_data(prompt, importance_scores)
        },
        "response": reply,
        "latency": round(time.time() - start_time, 3)
    }

# ---------------- PDF GENERATION (SYNCED) ----------------
def generate_pdf(data, filename="tokenscope_report.pdf"):
    if os.path.exists(filename):
        os.remove(filename)

    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("TokenScope: Edge-Hybrid Analysis Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Original Prompt:</b> {data['original_prompt']}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Performance Metrics", styles["Heading2"])
    ]

    metrics = data.get("metrics", {})
    for key, val in metrics.items():
        label = key.replace("_", " ").title()
        content.append(Paragraph(f"• {label}: {val}", styles["Normal"]))
    
    content.append(Spacer(1, 12))
    content.append(Paragraph("Optimized Result", styles["Heading2"]))
    content.append(Paragraph(data['analysis']['trimmed_prompt'], styles["Normal"]))
    doc.build(content)

# ---------------- ENDPOINTS ----------------

@app.get("/")
def home():
    return {"status": "TokenScope Edge-Hybrid Backend Active"}

@app.post("/analyze")
async def analyze(req: PromptRequest):
    return analyze_prompt_logic(req.prompt, True)

@app.post("/download-report")
async def download_report(req: PromptRequest):
    result = analyze_prompt_logic(req.prompt, True)
    
    pdf_payload = {
        "original_prompt": req.prompt,
        "metrics": result["metrics"],
        "analysis": result["analysis"]
    }

    filename = "tokenscope_report.pdf"
    generate_pdf(pdf_payload, filename)
    
    return FileResponse(
        filename, 
        media_type="application/pdf", 
        filename="TokenScope_Report.pdf"
    )

@app.post("/compare")
async def compare(req: CompareRequest):
    res1 = analyze_prompt_logic(req.prompt1, True)
    res2 = analyze_prompt_logic(req.prompt2, True)
    
    winner = "Prompt 1" if res1["metrics"]["total_tokens"] < res2["metrics"]["total_tokens"] else "Prompt 2"
    return {
        "prompt1": {**res1["metrics"], "cost": res1["metrics"]["cost_estimate"]},
        "prompt2": {**res2["metrics"], "cost": res2["metrics"]["cost_estimate"]},
        "result": {"winner": winner}
    }
