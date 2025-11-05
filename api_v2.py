"""
Enhanced API for Autodidact AI - Frontend Integration
======================================================

This API provides endpoints for:
1. Curriculum generation (with knowledge graph)
2. Video indexing (message queue)
3. User progress tracking
4. Domain/subdomain discovery

Frontend integration:
- React/Next.js: Use fetch() or axios
- Authentication: JWT tokens (optional)
- Real-time updates: WebSocket for queue status
"""

import sys
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import components
from src.agents.question_agent_v2 import QuestionAgentV2
from src.agents.question_agent import QuestionAgent
from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator
from src.knowledge_graph.concept_graph import ConceptGraph
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection

# Initialize FastAPI
app = FastAPI(
    title="Autodidact AI API",
    description="API for generating personalized learning curricula",
    version="2.0.0"
)

# CORS - Configure for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "https://your-app.vercel.app",  # Production (update this)
        "https://your-app.web.app",  # Firebase hosting (update this)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents (lazy loading for performance)
_question_agent_v1 = None
_question_agent_v2 = None
_concept_graph = None
_indexing_orchestrator = None


def get_question_agent_v1():
    """Lazy load QuestionAgent V1"""
    global _question_agent_v1
    if _question_agent_v1 is None:
        _question_agent_v1 = QuestionAgent()
    return _question_agent_v1


def get_question_agent_v2():
    """Lazy load QuestionAgent V2 (with knowledge graph)"""
    global _question_agent_v2
    if _question_agent_v2 is None:
        _question_agent_v2 = QuestionAgentV2()
    return _question_agent_v2


def get_concept_graph():
    """Lazy load concept graph"""
    global _concept_graph
    if _concept_graph is None:
        _concept_graph = ConceptGraph()
        if not _concept_graph.load_cache():
            # Build if cache doesn't exist
            client = get_chroma_client()
            collection = get_or_create_collection(client, "autodidact_ai_core_v2")
            _concept_graph.build_from_chroma(collection)
            _concept_graph.save_cache()
    return _concept_graph


def get_indexing_orchestrator():
    """Lazy load indexing orchestrator"""
    global _indexing_orchestrator
    if _indexing_orchestrator is None:
        _indexing_orchestrator = IndexingOrchestrator()
    return _indexing_orchestrator


# ============================================================================
# PYDANTIC MODELS (API Request/Response Schemas)
# ============================================================================

class CurriculumVersion(str, Enum):
    """Curriculum generation version"""
    v1 = "v1"  # Basic RAG
    v2 = "v2"  # Graph-enhanced (recommended)


class CurriculumRequest(BaseModel):
    """Request for curriculum generation"""
    query: str = Field(..., description="User's learning goal", example="I want to learn advanced piano")
    version: CurriculumVersion = Field(default=CurriculumVersion.v2, description="Algorithm version")
    user_level: Optional[str] = Field(None, description="Current skill level", example="beginner")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "I want to learn advanced piano techniques, starting from scratch",
                "version": "v2",
                "user_level": "beginner"
            }
        }


class CurriculumResponse(BaseModel):
    """Response with generated curriculum"""
    curriculum: str = Field(..., description="Generated curriculum in markdown format")
    version: str = Field(..., description="Version used for generation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class VideoIndexRequest(BaseModel):
    """Request to index a video"""
    url: str = Field(..., description="YouTube video URL")
    domain_id: Optional[str] = Field(None, description="Domain ID", example="MUSIC")
    subdomain_id: Optional[str] = Field(None, description="Subdomain ID", example="PIANO")
    difficulty: Optional[str] = Field(None, description="Difficulty level", example="beginner")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=vpn4qv4A1Aw",
                "domain_id": "MUSIC",
                "subdomain_id": "PIANO",
                "difficulty": "beginner"
            }
        }


class PlaylistIndexRequest(BaseModel):
    """Request to index an entire YouTube playlist (MVP feature)"""
    playlist_url: str = Field(..., description="YouTube playlist URL")
    domain_id: str = Field(..., description="Domain ID", example="MUSIC")
    subdomain_id: str = Field(..., description="Subdomain ID", example="PIANO")
    difficulty: str = Field(..., description="Difficulty level", example="beginner")
    category: str = Field(default="general", description="Category/topic")
    max_videos: Optional[int] = Field(None, description="Maximum videos to index (None = all)")
    min_quality: float = Field(default=0.55, description="Minimum quality score (0.0-1.0)")
    generate_roadmap: bool = Field(default=True, description="Generate learning roadmap after indexing")
    
    class Config:
        schema_extra = {
            "example": {
                "playlist_url": "https://www.youtube.com/playlist?list=PLxxx",
                "domain_id": "MUSIC",
                "subdomain_id": "PIANO",
                "difficulty": "beginner",
                "category": "music theory",
                "max_videos": 50,
                "min_quality": 0.55,
                "generate_roadmap": True
            }
        }


class PlaylistIndexResponse(BaseModel):
    """Response after indexing playlist"""
    success: bool
    message: str
    playlist_url: str
    total_videos: int
    indexed_videos: int
    filtered_videos: int
    skipped_videos: int
    roadmap: Optional[str] = Field(None, description="Generated learning roadmap (if requested)")


class VideoIndexResponse(BaseModel):
    """Response after submitting video for indexing"""
    success: bool
    message: str
    video_url: str
    queue_position: Optional[int] = None


class LearningPathRequest(BaseModel):
    """Request for learning path"""
    target_concept: str = Field(..., description="Target concept ID", example="MUSIC_PIANO_advanced")
    current_knowledge: Optional[List[str]] = Field(None, description="Known concept IDs")


class LearningPathResponse(BaseModel):
    """Response with learning path"""
    path: List[str] = Field(..., description="Ordered list of concept IDs")
    concepts: List[Dict[str, Any]] = Field(..., description="Concept details")


class StatsResponse(BaseModel):
    """System statistics"""
    total_videos: int
    total_concepts: int
    total_domains: int
    graph_nodes: int
    graph_edges: int


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "online",
        "version": "2.0.0",
        "message": "Autodidact AI API is running"
    }


@app.get("/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """Get system statistics"""
    try:
        # ChromaDB stats
        client = get_chroma_client()
        collection = get_or_create_collection(client, "autodidact_ai_core_v2")
        total_videos = collection.count()
        
        # Concept graph stats
        graph = get_concept_graph()
        graph_nodes = graph.graph.number_of_nodes()
        graph_edges = graph.graph.number_of_edges()
        
        # Count unique domains
        domains = set()
        for _, data in graph.graph.nodes(data=True):
            domains.add(data.get('domain_id', 'UNKNOWN'))
        
        return StatsResponse(
            total_videos=total_videos,
            total_concepts=graph_nodes,
            total_domains=len(domains),
            graph_nodes=graph_nodes,
            graph_edges=graph_edges
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.post("/curriculum/generate", response_model=CurriculumResponse, tags=["Curriculum"])
async def generate_curriculum(request: CurriculumRequest):
    """
    Generate personalized learning curriculum.
    
    This is the main endpoint your frontend will call.
    """
    try:
        # Select agent version
        if request.version == CurriculumVersion.v2:
            agent = get_question_agent_v2()
            curriculum = agent.generate_curriculum(request.query, request.user_level)
            version = "v2 (graph-enhanced)"
        else:
            agent = get_question_agent_v1()
            curriculum = agent.generate_curriculum(request.query)
            version = "v1 (basic RAG)"
        
        return CurriculumResponse(
            curriculum=curriculum,
            version=version,
            metadata={
                "query": request.query,
                "user_level": request.user_level
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum generation failed: {str(e)}")


@app.post("/videos/index", response_model=VideoIndexResponse, tags=["Indexing"])
async def index_video(request: VideoIndexRequest, background_tasks: BackgroundTasks):
    """
    Submit a video for indexing (async via message queue).
    
    The video will be processed by workers in the background.
    """
    try:
        orchestrator = get_indexing_orchestrator()
        
        # Build metadata
        metadata = {}
        if request.domain_id:
            metadata['domain_id'] = request.domain_id
        if request.subdomain_id:
            metadata['subdomain_id'] = request.subdomain_id
        if request.difficulty:
            metadata['difficulty'] = request.difficulty
        
        # Submit to queue
        success = orchestrator.submit_video_for_indexing(
            request.url,
            metadata if metadata else None
        )
        
        if success:
            return VideoIndexResponse(
                success=True,
                message="Video submitted for indexing",
                video_url=request.url,
                queue_position=None  # TODO: Get actual queue position from RabbitMQ
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to submit video to queue")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.post("/playlists/index", response_model=PlaylistIndexResponse, tags=["Indexing"])
async def index_playlist(request: PlaylistIndexRequest):
    """
    🚀 MVP FEATURE: Index entire YouTube playlist and generate learning roadmap.
    
    This is perfect for bootstrapping the knowledge base:
    1. User provides their curated learning playlist
    2. System scrapes all videos with quality filtering
    3. Optionally generates a personalized roadmap
    
    This makes users the content curators - they bring expertise,
    we provide structure and intelligent learning paths.
    """
    try:
        from src.bot.crawlers.apify_youtube_crawler import ApifyYouTubeCrawler
        from src.bot.quality_scorer import QualityScorer, ContentMetrics
        from src.models.unified_metadata_schema import Difficulty
        from datetime import datetime
        
        print(f"📋 Indexing playlist: {request.playlist_url}")
        
        # Initialize crawler with quality scoring
        crawler = ApifyYouTubeCrawler(
            max_results_per_query=200,
            min_quality_score=request.min_quality,
            use_quality_scorer=True
        )
        
        # Fetch playlist videos
        videos = crawler.get_playlist_videos(
            request.playlist_url,
            max_videos=request.max_videos
        )
        
        if not videos:
            raise HTTPException(status_code=404, detail="No videos found in playlist")
        
        # Initialize ChromaDB
        client = get_chroma_client()
        collection = get_or_create_collection(client, "autodidact_ai_core_v2")
        
        # Process videos with quality scoring
        indexed_count = 0
        filtered_count = 0
        skipped_count = 0
        
        scorer = QualityScorer(min_score_threshold=request.min_quality)
        
        for video in videos:
            # Check if already indexed
            existing = collection.get(
                where={"source": video['url']},
                limit=1
            )
            
            if existing['ids']:
                skipped_count += 1
                continue
            
            # Require transcript
            if not video.get('transcript'):
                filtered_count += 1
                continue
            
            # Parse published date
            published_at = video.get('published_at')
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = None
            
            # Get channel details
            channel_id = video.get('channel_id')
            subscriber_count = 0
            is_verified = False
            
            if channel_id:
                channel_info = crawler.fetch_channel_details(channel_id)
                if channel_info:
                    subscriber_count = channel_info.get('subscriber_count', 0)
                    is_verified = channel_info.get('is_verified', False)
            
            # Calculate quality
            metrics = ContentMetrics(
                query=f"{request.domain_id} {request.subdomain_id} {request.difficulty}",
                title=video.get('title', ''),
                description=video.get('description', ''),
                transcript=video.get('transcript', ''),
                tags=[],
                channel_name=video.get('channel_title', ''),
                subscriber_count=subscriber_count,
                is_verified=is_verified,
                view_count=video.get('view_count', 0) or 0,
                like_count=video.get('like_count', 0) or 0,
                comment_count=video.get('comment_count', 0) or 0,
                published_at=published_at,
                duration_seconds=video.get('duration', 0) or 0,
                has_captions=True
            )
            
            quality_score = scorer.score_content(metrics)
            
            # Filter by quality
            if not scorer.passes_threshold(quality_score):
                filtered_count += 1
                continue
            
            # Create metadata
            metadata = UnifiedMetadata(
                source=video['url'],
                content_type="video",
                domain_id=request.domain_id,
                subdomain_id=request.subdomain_id,
                skill_level=request.difficulty,
                category=request.category,
                technique=video['title'],
                author=video.get('channel_title'),
                channel_id=video.get('channel_id'),
                channel_url=f"https://www.youtube.com/channel/{video.get('channel_id')}" if video.get('channel_id') else None,
                created_at=video.get('published_at'),
                difficulty=Difficulty(request.difficulty.lower()),
                helpfulness_score=quality_score.overall,
                text_length=len(video['transcript']),
                quality_breakdown=quality_score.to_dict()
            )
            
            # Create content
            content = f"""Title: {video['title']}

Channel: {video['channel_title']}

Description: {video.get('description', '')[:500]}

Transcript:
{video['transcript']}"""
            
            # Add to ChromaDB
            collection.add(
                documents=[content],
                metadatas=[metadata.to_dict()],
                ids=[f"video_{video['video_id']}"]
            )
            indexed_count += 1
        
        # Generate roadmap if requested
        roadmap = None
        if request.generate_roadmap and indexed_count > 0:
            try:
                agent = get_question_agent_v2()
                query = f"Create a learning roadmap for {request.subdomain_id} in {request.domain_id} at {request.difficulty} level"
                roadmap = agent.generate_curriculum(query, request.difficulty)
            except Exception as e:
                print(f"⚠️  Roadmap generation failed: {e}")
        
        return PlaylistIndexResponse(
            success=True,
            message=f"Successfully indexed {indexed_count} videos from playlist",
            playlist_url=request.playlist_url,
            total_videos=len(videos),
            indexed_videos=indexed_count,
            filtered_videos=filtered_count,
            skipped_videos=skipped_count,
            roadmap=roadmap
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playlist indexing failed: {str(e)}")


@app.post("/learning-path", response_model=LearningPathResponse, tags=["Learning Path"])
async def get_learning_path(request: LearningPathRequest):
    """
    Get optimal learning path to a target concept.
    
    Useful for showing users their learning journey.
    """
    try:
        graph = get_concept_graph()
        
        # Find path
        path = graph.find_learning_path(
            target_concept=request.target_concept,
            current_knowledge=request.current_knowledge
        )
        
        # Get concept details
        concepts = []
        for concept_id in path:
            concept = graph.get_concept_info(concept_id)
            if concept:
                concepts.append({
                    'id': concept.id,
                    'domain': concept.domain_id,
                    'subdomain': concept.subdomain_id,
                    'difficulty': concept.difficulty,
                    'quality': concept.avg_quality,
                    'resources': concept.resource_count
                })
        
        return LearningPathResponse(
            path=path,
            concepts=concepts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Path finding failed: {str(e)}")


@app.get("/domains", tags=["Discovery"])
async def get_domains():
    """Get all available domains"""
    try:
        graph = get_concept_graph()
        
        domains = {}
        for node_id, data in graph.graph.nodes(data=True):
            domain_id = data.get('domain_id', 'UNKNOWN')
            subdomain_id = data.get('subdomain_id', 'UNKNOWN')
            
            if domain_id not in domains:
                domains[domain_id] = {
                    'id': domain_id,
                    'subdomains': set(),
                    'concept_count': 0
                }
            
            domains[domain_id]['subdomains'].add(subdomain_id)
            domains[domain_id]['concept_count'] += 1
        
        # Convert sets to lists for JSON
        result = []
        for domain_id, info in domains.items():
            result.append({
                'id': domain_id,
                'subdomains': sorted(list(info['subdomains'])),
                'concept_count': info['concept_count']
            })
        
        return {'domains': sorted(result, key=lambda x: x['id'])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch domains: {str(e)}")


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    print("🚀 Autodidact AI API starting up...")
    print("   Loading knowledge graph...")
    get_concept_graph()
    print("✅ API ready to serve requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🔌 Shutting down API...")
    if _indexing_orchestrator:
        _indexing_orchestrator.close()
    print("✅ Shutdown complete")


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_v2:app",
        host="0.0.0.0",
        port=8001,
        reload=True  # Auto-reload on code changes (dev only)
    )
