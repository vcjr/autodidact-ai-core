import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Important for React

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import your orchestrators
from src.orchestrators.indexing_orchestrator import run_indexing_pipeline
from src.agents.question_agent import QuestionAgent # This is our RAG agent

# Import your API data models
from src.models.api_models import IndexRequest, IndexResponse, CurriculumRequest, CurriculumResponse

# --- App Initialization ---
app = FastAPI(
    title="Autodidact AI Backend",
    description="API for indexing YouTube content and generating custom RAG curriculums.",
    version="0.1.0"
)

# --- CORS Middleware ---
# This is CRITICAL for your React app to be able to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins (for development)
    # You can restrict this to your Firebase domain in production:
    # allow_origins=["httpsfs://your-firebase-app.web.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/", tags=["Health"])
async def read_root():
    """
    Health check endpoint to confirm the API is running.
    """
    return {"status": "Autodidact AI API is running!"}


@app.post("/index-video", response_model=IndexResponse, tags=["Indexing"])
async def index_video(request: IndexRequest):
    """
    Endpoint to trigger the full indexing pipeline for a new YouTube video.
    """
    try:
        result = run_indexing_pipeline(request.youtube_url)
        
        if result:
            return IndexResponse(
                status="success",
                message="Video indexed successfully.",
                video_id=result.get("video_id"),
                title=result.get("title"),
                helpfulness_score=result.get("helpfulness_score")
            )
        else:
            # This happens if the video was rejected (e.g., low score)
            raise HTTPException(status_code=422, detail="Indexing rejected or failed. Video may have a low helpfulness score or be unscrapable.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@app.post("/generate-curriculum", response_model=CurriculumResponse, tags=["Curriculum"])
async def generate_curriculum(request: CurriculumRequest):
    """
    Endpoint to generate a custom curriculum using the RAG pipeline.
    """
    try:
        # Initialize the RAG agent
        agent = QuestionAgent()
        
        # Run the full RAG pipeline
        curriculum_text = agent.generate_curriculum(request.query)
        
        if not curriculum_text:
            raise HTTPException(status_code=404, detail="Could not generate curriculum. No relevant, high-quality documents found.")
            
        return CurriculumResponse(curriculum=curriculum_text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")