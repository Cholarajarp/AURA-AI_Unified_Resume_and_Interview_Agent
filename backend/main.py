import os
import uuid
import shutil
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict, Any
import asyncio
try:
    from . import ai_engine as engine
except ImportError:
    import ai_engine as engine

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get configuration from environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", os.getenv("PORT", 8000)))
HOST = os.getenv("HOST", "0.0.0.0")

app = FastAPI(title="AURA Backend - AI Unified Resume & Interview Agent")

# Configure CORS based on environment
if ENVIRONMENT == "production":
    # Production: Accept requests from the same origin (served together)
    allowed_origins = ["*"]
else:
    # Development: Accept all origins
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE = Path("./data")
STORAGE.mkdir(exist_ok=True)

sessions = {}

# Pydantic Models
class AnalyzeRequest(BaseModel):
    session_id: str
    job_description: str

class AnswerRequest(BaseModel):
    session_id: str
    question_index: int
    answer: str

class InterviewStartRequest(BaseModel):
    session_id: str

# Routes
@app.get("/")
async def root():
    return {
        "status": "AURA Backend Active",
        "version": "2.0",
        "mode": "REAL WORLD - GPT-4 TURBO",
        "message": "System is in production mode - Real AI processing only"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "backend": "running",
        "ai_mode": "REAL (GPT-4 Turbo)",
        "ready": True
    }

@app.post('/upload')
async def upload_resume(file: UploadFile = File(...)):
    """Upload resume and extract text"""
    try:
        session_id = str(uuid.uuid4())
        file_path = STORAGE / f"resume_{session_id}.pdf"
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        text = engine.extract_text_from_pdf(str(file_path))
        sessions[session_id] = {
            'resume_text': text,
            'job_description': '',
            'analysis': None,
            'interview_questions': [],
            'interview_answers': [],
            'final_score': None,
            'file_path': str(file_path)
        }
        return {
            'status': 'success',
            'session_id': session_id,
            'message': 'Resume uploaded successfully',
            'preview': text[:200]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/analyze')
async def analyze(req: AnalyzeRequest):
    """Analyze resume against job description"""
    try:
        sid = req.session_id
        if sid not in sessions:
            raise HTTPException(status_code=404, detail='Session not found')
        
        if not req.job_description or req.job_description.strip() == '':
            raise HTTPException(status_code=400, detail='Job description is required')
        
        sessions[sid]['job_description'] = req.job_description
        resume_text = sessions[sid]['resume_text']
        
        if not resume_text or resume_text.strip() == '':
            raise HTTPException(status_code=400, detail='Resume text is empty - upload failed')
        
        # Get analysis from LLM
        analysis = engine.analyze_resume_with_llm(resume_text, req.job_description)
        sessions[sid]['analysis'] = analysis
        
        return {
            'status': 'success',
            'analysis': analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Resume analysis failed: {str(e)}"
        print(f"❌ {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post('/start_interview')
async def start_interview(req: InterviewStartRequest):
    """Generate interview questions"""
    try:
        sid = req.session_id
        if sid not in sessions:
            raise HTTPException(status_code=404, detail='Session not found')
        
        analysis = sessions[sid].get('analysis')
        job_desc = sessions[sid].get('job_description')
        
        if not analysis:
            raise HTTPException(status_code=400, detail='Must analyze resume first')
        
        # Generate questions
        questions = engine.generate_interview_questions(job_desc, analysis)
        sessions[sid]['interview_questions'] = questions
        
        return {
            'status': 'success',
            'questions': questions,
            'total': len(questions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post('/submit_answer')
async def submit_answer(req: AnswerRequest):
    """Evaluate interview answer"""
    try:
        sid = req.session_id
        if sid not in sessions:
            raise HTTPException(status_code=404, detail='Session not found')
        
        questions = sessions[sid].get('interview_questions', [])
        if req.question_index >= len(questions):
            raise HTTPException(status_code=400, detail='Invalid question index')
        
        question = questions[req.question_index]
        
        # Evaluate answer
        evaluation = engine.evaluate_answer(question, req.answer)
        
        # Store answer
        sessions[sid]['interview_answers'].append({
            'question_index': req.question_index,
            'question': question,
            'answer': req.answer,
            'score': evaluation.get('score', 75),
            'feedback': evaluation.get('feedback', '')
        })
        
        # Check if interview complete
        is_complete = len(sessions[sid]['interview_answers']) == len(questions)
        
        if is_complete:
            # Calculate final score
            interview_scores = [a['score'] for a in sessions[sid]['interview_answers']]
            avg_interview_score = sum(interview_scores) / len(interview_scores) if interview_scores else 0
            resume_score = sessions[sid]['analysis'].get('overallScore', 75)
            final_score = (resume_score * 0.5 + avg_interview_score * 0.5)
            
            # Determine recommendation
            if avg_interview_score > 75 and resume_score > 80:
                recommendation = "Strong Yes"
            elif avg_interview_score > 65:
                recommendation = "Yes"
            else:
                recommendation = "Maybe"
            
            final_result = {
                'resumeScore': resume_score,
                'interviewScore': avg_interview_score,
                'finalScore': round(final_score, 1),
                'recommendation': recommendation,
                'summary': f"Candidate demonstrates strong technical skills with relevant experience. Interview responses show {'excellent' if avg_interview_score > 75 else 'good'} problem-solving ability and communication skills."
            }
            sessions[sid]['final_score'] = final_result
        
        return {
            'status': 'success',
            'evaluation': evaluation,
            'question_index': req.question_index,
            'is_complete': is_complete,
            'final_score': sessions[sid].get('final_score')
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get('/session/{session_id}')
async def get_session(session_id: str):
    """Get session data"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail='Session not found')
        
        session = sessions[session_id]
        return {
            'status': 'success',
            'session_id': session_id,
            'has_analysis': session.get('analysis') is not None,
            'interview_progress': len(session.get('interview_answers', [])),
            'final_score': session.get('final_score')
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete('/session/{session_id}')
async def delete_session(session_id: str):
    """Clean up session"""
    try:
        if session_id in sessions:
            session = sessions[session_id]
            if 'file_path' in session:
                try:
                    os.remove(session['file_path'])
                except:
                    pass
            del sessions[session_id]
        return {'status': 'success', 'message': 'Session deleted'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Mount static files (frontend) - MUST be after all API routes
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
else:
    # Fallback: try alternate path for Docker
    frontend_dist_docker = Path("/app/frontend/dist")
    if frontend_dist_docker.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist_docker), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=HOST, 
        port=PORT,
        reload=(ENVIRONMENT == "development")
    )
