# backend/main.py
import os
import uuid
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import aiofiles  # async file operations

# Optional relative import for ai_engine
try:
    from . import ai_engine as engine
except ImportError:
    import ai_engine as engine

# Load env if you use dotenv in runtime (only if installed)
from dotenv import load_dotenv
load_dotenv()

# ENV
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000) or 8000)

# App
app = FastAPI(title="AURA Backend - AI Unified Resume & Interview Agent")

# CORS — in production set explicit origins instead of "*"
if ENVIRONMENT == "production":
    allowed_origins = ["*"]  # TODO: change to your frontend origin e.g. https://your-frontend.onrender.com
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
BASE_DIR = Path(__file__).parent
STORAGE = (BASE_DIR / "data").resolve()
TEMPLATES_DIR = (BASE_DIR / "templates").resolve()
STATIC_DIR = (BASE_DIR / "static").resolve()

# Ensure directories exist
STORAGE.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Templates for serving index.html
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory session store (ephemeral)
sessions: Dict[str, Dict[str, Any]] = {}

# Small upload guards
ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB (adjust as needed)


# Utility: run sync function in threadpool
async def run_blocking(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


# Root: serve index.html (templates/index.html preferred, fallback to frontend/dist/index.html)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Prefer backend/templates/index.html
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        return templates.TemplateResponse("index.html", {"request": request})

    # Fallback to frontend/dist/index.html (if your build is not copied into backend)
    frontend_dist = (BASE_DIR.parent / "frontend" / "dist" / "index.html").resolve()
    if frontend_dist.exists():
        return FileResponse(str(frontend_dist))

    # Nothing found — return helpful status page
    return HTMLResponse(
        """
        <html>
        <head><title>AURA Backend</title></head>
        <body>
          <h1>AURA Backend Active</h1>
          <p>No frontend build found. Ensure frontend was built and copied into <code>backend/templates</code> & <code>backend/static</code>.</p>
          <p>API health: <a href="/health">/health</a></p>
        </body>
        </html>
        """
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "backend": "running", "ready": True}


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload resume (expects PDF). Saves to backend/data and extracts text via ai_engine.
    """
    # Basic content-type check
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Read stream incrementally and limit size
    session_id = str(uuid.uuid4())
    safe_name = f"resume_{session_id}.pdf"
    out_path = STORAGE / safe_name

    # write file asynchronously and enforce MAX_UPLOAD_BYTES
    total = 0
    try:
        async with aiofiles.open(out_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    await f.close()
                    try:
                        out_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="File too large.")
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")

    # Extract text using engine (potentially blocking) — run in threadpool
    try:
        resume_text = await run_blocking(engine.extract_text_from_pdf, str(out_path))
    except Exception as exc:
        # cleanup on failure
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {exc}")

    # Save session
    sessions[session_id] = {
        "resume_text": resume_text,
        "job_description": "",
        "analysis": None,
        "interview_questions": [],
        "interview_answers": [],
        "final_score": None,
        "file_path": str(out_path),
    }

    return {"status": "success", "session_id": session_id, "preview": resume_text[:200]}


class AnalyzeRequestModel(dict):
    pass  # kept simple — your Pydantic model can be used as earlier


@app.post("/analyze")
async def analyze(payload: dict):
    """
    Analyze resume against job description.
    Expects JSON { "session_id": "...", "job_description": "..." }
    """
    sid = payload.get("session_id")
    job_description = payload.get("job_description", "")

    if not sid or sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    sessions[sid]["job_description"] = job_description
    resume_text = sessions[sid].get("resume_text", "")

    if not resume_text or not resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty")

    # Use engine.analyze_resume_with_llm in threadpool if blocking
    try:
        analysis = await run_blocking(engine.analyze_resume_with_llm, resume_text, job_description)
        sessions[sid]["analysis"] = analysis
        return {"status": "success", "analysis": analysis}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {exc}")


@app.post("/start_interview")
async def start_interview(payload: dict):
    sid = payload.get("session_id")
    if not sid or sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    analysis = sessions[sid].get("analysis")
    job_desc = sessions[sid].get("job_description", "")

    if not analysis:
        raise HTTPException(status_code=400, detail="Must analyze resume first")

    try:
        questions = await run_blocking(engine.generate_interview_questions, job_desc, analysis)
        sessions[sid]["interview_questions"] = questions
        return {"status": "success", "questions": questions, "total": len(questions)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/submit_answer")
async def submit_answer(payload: dict):
    sid = payload.get("session_id")
    q_idx = payload.get("question_index")
    answer = payload.get("answer", "")

    if not sid or sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    questions = sessions[sid].get("interview_questions", [])
    if q_idx is None or q_idx < 0 or q_idx >= len(questions):
        raise HTTPException(status_code=400, detail="Invalid question index")

    question = questions[q_idx]

    # Evaluate answer via engine (offload to threadpool)
    try:
        evaluation = await run_blocking(engine.evaluate_answer, question, answer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")

    sessions[sid]["interview_answers"].append({
        "question_index": q_idx,
        "question": question,
        "answer": answer,
        "score": evaluation.get("score", 75),
        "feedback": evaluation.get("feedback", ""),
    })

    # If complete, compute final score
    is_complete = len(sessions[sid]["interview_answers"]) == len(questions)
    if is_complete:
        interview_scores = [a["score"] for a in sessions[sid]["interview_answers"]]
        avg_interview_score = sum(interview_scores) / len(interview_scores) if interview_scores else 0
        resume_score = sessions[sid]["analysis"].get("overallScore", 75) if sessions[sid]["analysis"] else 75
        final_score = (resume_score * 0.5 + avg_interview_score * 0.5)

        if avg_interview_score > 75 and resume_score > 80:
            recommendation = "Strong Yes"
        elif avg_interview_score > 65:
            recommendation = "Yes"
        else:
            recommendation = "Maybe"

        final_result = {
            "resumeScore": resume_score,
            "interviewScore": avg_interview_score,
            "finalScore": round(final_score, 1),
            "recommendation": recommendation,
            "summary": f"Candidate demonstrates strong technical skills with relevant experience. Interview responses show {'excellent' if avg_interview_score > 75 else 'good'} problem-solving ability and communication skills."
        }
        sessions[sid]["final_score"] = final_result

    return {
        "status": "success",
        "evaluation": evaluation,
        "question_index": q_idx,
        "is_complete": is_complete,
        "final_score": sessions[sid].get("final_score")
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    sess = sessions[session_id]
    return {
        "status": "success",
        "session_id": session_id,
        "has_analysis": sess.get("analysis") is not None,
        "interview_progress": len(sess.get("interview_answers", [])),
        "final_score": sess.get("final_score")
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        session = sessions.pop(session_id, None)
        if session and session.get("file_path"):
            try:
                os.remove(session["file_path"])
            except Exception:
                pass
    return {"status": "success", "message": "Session deleted"}


# Mount frontend static assets to /static so API endpoints are reachable at root (/)
# If you previously copied build output into backend/static, this will serve assets at /static/*
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Optionally mount frontend/dist for local dev if not copied into backend/static
frontend_dist = (BASE_DIR.parent / "frontend" / "dist").resolve()
if frontend_dist.exists() and frontend_dist.is_dir():
    # serve development build under /static-dev (optional)
    app.mount("/static-dev", StaticFiles(directory=str(frontend_dist)), name="static-dev")


# If running as script
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=(ENVIRONMENT != "production"))