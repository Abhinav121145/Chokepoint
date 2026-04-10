from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import tiktoken
from groq import Groq
from sklearn.feature_extraction.text import TfidfVectorizer
import os
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

class CompareRequest(BaseModel):
    prompt1: str
    prompt2: str


# ---------------- TOKEN COUNTING ----------------
def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


# ---------------- ML: TOKEN IMPORTANCE (TF-IDF) ----------------
STOPWORDS = {"the", "is", "in", "and", "with", "a", "an", "to", "of", "for", "on", "at", "by"}

def get_token_importance(text):
    words = text.split()
    if len(words) < 2:
        return {word: 1.0 for word in words}

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(words)
    base_scores = dict(zip(vectorizer.get_feature_names_out(), X.toarray().sum(axis=0)))

    scores = {}
    for word in words:
        w = word.lower()
        score = base_scores.get(w, 0)
        score += len(word) * 0.02 # Length bonus
        if w in STOPWORDS: score *= 0.3 # Stopword penalty
        if len(word) > 6: score += 0.1 # Complexity bonus
        scores[word] = round(score, 3)
    return scores

# ---------------- HEATMAP CATEGORIZATION ----------------
def prepare_visualization_data(text, scores):
    words = text.split()
    visualization = []
    for word in words:
        score = scores.get(word, 0)
        # Match levels to UI color tags
        if score > 0.25:
            level = "high"
        elif score > 0.15:
            level = "medium"
        else:
            level = "low"
        
        visualization.append({"word": word, "score": score, "level": level})
    return visualization


# ---------------- PROMPT TRIMMING ----------------
def trim_prompt(text, scores):
    words = text.split()
    trimmed = [w for w in words if scores.get(w, 0) > 0.2 and w.lower() not in STOPWORDS]
    if len(trimmed) < 3: trimmed = words[:max(3, len(words)//2)]
    return " ".join(trimmed)


# ---------------- CORE ANALYZER LOGIC ----------------
def analyze_prompt_logic(prompt):
    # Simulated RAG metrics for visual breakdown
    system_tokens = 56 
    context_tokens = 409
    query_tokens = count_tokens(prompt)
    
    # LLM Interaction via Groq
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = response.choices[0].message.content
    response_tokens = count_tokens(reply)
    
    # Analytics
    importance_scores = get_token_importance(prompt)
    trimmed_prompt = trim_prompt(prompt, importance_scores)
    trimmed_tokens = count_tokens(trimmed_prompt)
    total_tokens = query_tokens + response_tokens

    return {
        "metrics": {
            "prompt_tokens": query_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "cost_estimate": round(total_tokens * 0.000001, 6),
            "tokens_saved": query_tokens - trimmed_tokens
        },
        "rag_breakdown": {
            "system": system_tokens,
            "context": context_tokens,
            "query": query_tokens,
            "relevance_percent": 9 
        },
        "analysis": {
            "importance_scores": importance_scores,
            "trimmed_prompt": trimmed_prompt,
            "trimmed_tokens": trimmed_tokens
        },
        "response": reply
    }


# ---------------- PDF GENERATION ----------------
def generate_pdf(data, filename="tokenscope_report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("TokenScope Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"Original Prompt: {data['original_prompt']}", styles["Normal"]),
        Spacer(1, 10),
        Paragraph("Metrics:", styles["Heading2"])
    ]
    for key, value in data["metrics"].items():
        content.append(Paragraph(f"{key}: {value}", styles["Normal"]))
    
    content.append(Spacer(1, 10))
    content.append(Paragraph("Optimized Prompt:", styles["Heading2"]))
    content.append(Paragraph(data["analysis"]["trimmed_prompt"], styles["Normal"]))
    doc.build(content)


# ---------------- ENDPOINTS ----------------

@app.get("/")
def home():
    return {"message": "🚀 TokenScope Backend Running"}


@app.post("/analyze")
async def analyze(req: PromptRequest):
    result = analyze_prompt_logic(req.prompt)
    
    # ⚡ Execute TF-IDF heatmap categorization here
    visualization = prepare_visualization_data(req.prompt, result["analysis"]["importance_scores"])
    
    return {
        "metrics": result["metrics"],
        "rag_breakdown": result["rag_breakdown"],
        "analysis": {
            **result["analysis"],
            "visualization": visualization  # Sent to frontend heatmap builder
        },
        "response": result["response"]
    }


@app.post("/download-report")
async def download_report(req: PromptRequest):
    result = analyze_prompt_logic(req.prompt)
    data = {"original_prompt": req.prompt, "metrics": result["metrics"], "analysis": result["analysis"]}
    filename = "tokenscope_report.pdf"
    generate_pdf(data, filename)
    return FileResponse(filename, media_type="application/pdf", filename=filename)


@app.post("/compare")
async def compare(req: CompareRequest):
    res1 = analyze_prompt_logic(req.prompt1)
    res2 = analyze_prompt_logic(req.prompt2)

    winner = "Prompt 1" if res1["metrics"]["total_tokens"] < res2["metrics"]["total_tokens"] else "Prompt 2"
    if res1["metrics"]["total_tokens"] == res2["metrics"]["total_tokens"]: winner = "Equal"

    return {
        "prompt1": {**res1["metrics"], "total_tokens": res1["metrics"]["total_tokens"], "cost": res1["metrics"]["cost_estimate"]},
        "prompt2": {**res2["metrics"], "total_tokens": res2["metrics"]["total_tokens"], "cost": res2["metrics"]["cost_estimate"]},
        "result": {"winner": winner, "message": f"{winner} is more cost-efficient"}
    }
