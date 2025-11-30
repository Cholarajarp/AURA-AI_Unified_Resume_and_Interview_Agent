# AURA - AI Unified Resume & Interview Agent

An intelligent AI-powered application that analyzes resumes against job descriptions and conducts mock interviews with real-time feedback.

## Features

- **Resume Analysis**: Upload PDF resumes and analyze them against job descriptions
- **AI-Powered Matching**: Uses Google Gemini AI to evaluate resume relevance
- **Mock Interviews**: Generate tailored interview questions based on job requirements
- **Real-time Evaluation**: Get instant feedback on interview answers
- **Score Calculation**: Comprehensive scoring combining resume and interview performance
- **Professional UI**: Modern, responsive interface built with React

## Architecture

### Single Unified Service Deployment
- **Frontend**: React + Vite (built into static files)
- **Backend**: FastAPI + Python
- **Deployment**: One domain, one service on Render

```
┌─────────────────────────────────────────┐
│         Single Render Service           │
│  (One Domain: aura-agent.onrender.com)  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    FastAPI Backend              │   │
│  │                                 │   │
│  │  • Serves frontend (HTML/CSS)   │   │
│  │  • API endpoints (/upload, etc) │   │
│  │  • Google Gemini integration    │   │
│  │  • Resume processing            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Project Structure

```
aura_agent_project/
├── render.yaml              # Render deployment config
├── requirements.txt         # Python dependencies
├── Procfile                # Alternative start config
├── LICENSE
├── README.md               # This file
│
├── backend/
│   ├── main.py             # FastAPI app (serves frontend + API)
│   ├── ai_engine.py        # AI logic & Google Gemini integration
│   ├── requirements.txt     # Backend Python dependencies
│   ├── __init__.py
│   ├── build.sh
│   ├── test_gemini_json.py
│   └── data/               # Resume storage
│
└── frontend/
    ├── main.jsx            # React entry point
    ├── AuraAgent.jsx       # Main application component
    ├── vite.config.js      # Vite build configuration
    ├── package.json        # Node.js dependencies
    ├── index.html          # HTML template
    ├── index.css           # Global styles
    ├── postcss.config.js   # PostCSS configuration
    ├── tailwind.config.js  # Tailwind CSS configuration
    └── [build output]      # dist/ (created during build)
```

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- Google Gemini API key (get from [ai.google.dev](https://ai.google.dev))

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Cholarajarp/AURA-AI_Unified_Resume_And_Interview_Agent.git
   cd AURA-AI_Unified_Resume_And_Interview_Agent
   ```

2. **Set up backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up frontend**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

4. **Set environment variables**
   ```bash
   cd ../backend
   # Create .env file
   export GOOGLE_API_KEY=your_api_key_here
   export ENVIRONMENT=development
   ```

5. **Run backend**
   ```bash
   python main.py
   # Backend runs on http://localhost:8000
   ```

6. **Frontend is served automatically**
   - Visit `http://localhost:8000` to access the application

## 🌐 Deployment to Render

### Prerequisites
- GitHub account with repository pushed
- Render account ([render.com](https://render.com))
- Google Gemini API key

### Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Deployment ready"
   git push origin main
   ```

2. **Create Render Service**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render auto-detects `render.yaml`

3. **Configure Environment**
   - In Render dashboard, add environment variable:
     - `GOOGLE_API_KEY`: Your actual Google Gemini API key
     - `LLM_MODEL`: `gemini-2.5-flash` (optional, auto-set)

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~5 minutes)
   - Your app is live! 🎉

### Build Process
```
Render Build:
1. npm install (frontend)
2. npm run build (frontend → dist/)
3. Copy frontend/dist/index.html → backend/templates/
4. Copy frontend/dist/* → backend/static/
5. pip install -r requirements.txt
6. Start: uvicorn backend.main:app
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves frontend (index.html) |
| `/health` | GET | Health check endpoint |
| `/upload` | POST | Upload resume PDF |
| `/analyze` | POST | Analyze resume against job description |
| `/start_interview` | POST | Generate interview questions |
| `/submit_answer` | POST | Submit interview answer for evaluation |
| `/session/{session_id}` | GET | Get session details |
| `/session/{session_id}` | DELETE | Clean up session |

### Example API Call
```bash
# Upload resume
curl -X POST http://localhost:8000/upload \
  -F "file=@resume.pdf"

# Analyze resume
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "job_description": "Senior Python Developer..."
  }'

# Start interview
curl -X POST http://localhost:8000/start_interview \
  -H "Content-Type: application/json" \
  -d '{"session_id": "session-uuid"}'

# Submit answer
curl -X POST http://localhost:8000/submit_answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "question_index": 0,
    "answer": "My answer to the question..."
  }'
```

## AI Features

- **Resume Analysis**: Evaluates skills, experience, and relevance
- **Interview Generation**: Creates contextual questions based on job requirements
- **Answer Evaluation**: Provides scored feedback on interview responses
- **Final Scoring**: Calculates combined resume and interview scores

### Supported Models
- `gemini-2.5-flash` (default, recommended)
- Other Google Gemini models available

## Environment Variables

```env
# Required
GOOGLE_API_KEY=your_google_gemini_api_key

# Optional
ENVIRONMENT=production  # or development
PORT=8000              # Default for Render
HOST=0.0.0.0          # Default
LLM_MODEL=gemini-2.5-flash
```

## 🛠️ Technology Stack

### Frontend
- React 18.2.0
- Vite 5.0.0 (build tool)
- Tailwind CSS 3.3.0
- PostCSS 8.4.31
- Lucide React (icons)

### Backend
- FastAPI 0.104.1
- Uvicorn 0.24.0 (ASGI server)
- Python 3.13
- PyPDF 4.0.1 (PDF processing)
- Google Generative AI 0.3.0
- Python-dotenv 1.0.0

### Deployment
- Render (PaaS)
- GitHub (repository)

## Security Considerations

- API key stored as environment variable (never in code)
- CORS configured for production
- PDF files stored temporarily and cleaned up
- Session-based architecture

## Performance

- **Build Time**: ~3-5 minutes on Render
- **Startup Time**: ~10-30 seconds (cold start on free tier)
- **Response Time**: <1 second for API calls
- **Frontend Load**: Instant (static files)

## Troubleshooting

### Frontend not loading
- Check Render logs for build errors
- Verify `npm run build` completed successfully
- Check if `frontend/dist` was created

### API calls failing
- Verify `GOOGLE_API_KEY` is set in Render dashboard
- Check backend logs for Python errors
- Ensure API endpoint path is correct

### Build failing on Render
- Check that `requirements.txt` exists in root
- Verify `package.json` exists in `frontend/`
- Review Render build logs for specific errors

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Render deployment logs
3. Check Google Gemini API status
4. Open an issue on GitHub

## Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Render Documentation](https://render.com/docs)
- [Google Gemini API](https://ai.google.dev/)

---

**Built with using FastAPI, React, and Render**

**Status**: Ready for production deployment
