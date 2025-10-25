from pydantic import BaseModel
from typing import Optional

# --- Input Models (Requests) ---

class IndexRequest(BaseModel):
    """
    Defines the data needed to index a new video.
    """
    youtube_url: str

class CurriculumRequest(BaseModel):
    """
    Defines the data needed to generate a curriculum.
    """
    query: str

# --- Output Models (Responses) ---

class IndexResponse(BaseModel):
    """
    Defines the response after a successful indexing.
    """
    status: str
    message: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    helpfulness_score: Optional[float] = None

class CurriculumResponse(BaseModel):
    """
    Defines the response containing the generated curriculum.
    """
    curriculum: str
    # We can add more fields later, like source URLs