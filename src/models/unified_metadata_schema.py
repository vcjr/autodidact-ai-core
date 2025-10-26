"""
Unified Metadata Schema for Autodidact AI Core
==============================================

This schema bridges the existing RAG system (IntakeAgent, ScopeAgent, QuestionAgent)
with the new bot crawler system, ensuring both can work with the same ChromaDB data.

Key Design Decisions:
- Backward compatible with existing 'instrument_id' field
- Supports new bot fields: domain_id, subdomain_id, platform, quality metrics
- All fields validated with Pydantic for type safety
- Schema version tracking for future migrations
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum


class Platform(str, Enum):
    """Supported content platforms"""
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    QUORA = "quora"
    BLOG = "blog"
    MANUAL = "manual"  # For user-uploaded content


class ContentType(str, Enum):
    """Type of educational content"""
    VIDEO = "video"
    ARTICLE = "article"
    DISCUSSION = "discussion"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"


class Difficulty(str, Enum):
    """Learning difficulty level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class UnifiedMetadata(BaseModel):
    """
    Universal metadata schema for both bot indexing and RAG retrieval.
    
    This schema ensures compatibility between:
    1. Existing RAG agents (IntakeAgent, ScopeAgent, QuestionAgent)
    2. New bot crawlers (YouTube, Reddit, Quora, Blog)
    
    Usage:
        # Bot crawler
        metadata = UnifiedMetadata(
            domain_id="MUSIC",
            subdomain_id="PIANO",
            source="https://youtube.com/watch?v=abc123",
            platform=Platform.YOUTUBE,
            difficulty=Difficulty.INTERMEDIATE,
            text_length=2500,
            helpfulness_score=0.87
        )
        
        # RAG agent
        filter = {
            "instrument_id": "MUSIC_PIANO",
            "difficulty": "intermediate",
            "helpfulness_score": {"$gte": 0.8}
        }
    """
    
    # SCHEMA VERSION (for future migrations)
    schema_version: str = Field(
        default="1.0.0",
        description="Schema version (semver format)"
    )
    
    # PRIMARY IDENTIFIERS (Required for both bot + RAG)
    domain_id: str = Field(
        ...,
        description="Top-level learning domain (e.g., MUSIC, CODING_SOFTWARE, LANGUAGES)",
        min_length=1,
        max_length=100
    )
    
    subdomain_id: Optional[str] = Field(
        default=None,
        description="Specific subdomain/instrument (e.g., PIANO, PYTHON, SPANISH)",
        max_length=100
    )
    
    # LEGACY COMPATIBILITY (Auto-generated for existing RAG agents)
    instrument_id: Optional[str] = Field(
        default=None,
        description="Legacy field: {domain_id}_{subdomain_id} or just {domain_id}"
    )
    
    # CONTENT METADATA (Required)
    source: str = Field(
        ...,
        description="URL or document identifier (must be unique)",
        min_length=1
    )
    
    platform: Platform = Field(
        default=Platform.MANUAL,
        description="Content source platform"
    )
    
    content_type: ContentType = Field(
        default=ContentType.ARTICLE,
        description="Type of educational content"
    )
    
    # AUTHOR & TIMESTAMPS (Optional but recommended)
    author: Optional[str] = Field(
        default=None,
        description="Content creator username or name",
        max_length=200
    )
    
    created_at: Optional[datetime] = Field(
        default=None,
        description="Original content publication date"
    )
    
    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when content was indexed by bot/agent"
    )
    
    # LEARNING METADATA (Required)
    difficulty: Difficulty = Field(
        ...,
        description="Learning difficulty level"
    )
    
    skill_level: Optional[str] = Field(
        default=None,
        description="Alias for difficulty (auto-populated)"
    )
    
    technique: Optional[str] = Field(
        default=None,
        description="Specific technique, concept, or skill taught",
        max_length=200
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Freeform tags for additional categorization"
    )
    
    # QUALITY METRICS (Required)
    helpfulness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score (used by RAG filtering >= 0.8)"
    )
    
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Alias for helpfulness_score (auto-populated)"
    )
    
    quality_breakdown: Optional[Dict[str, float]] = Field(
        default=None,
        description="5-factor quality breakdown from bot scorer"
    )
    
    # ENGAGEMENT METRICS (Optional, populated by bot)
    engagement_metrics: Optional[Dict[str, int]] = Field(
        default=None,
        description="Platform-specific engagement (views, likes, upvotes, etc.)"
    )
    
    # DOCUMENT STATS (Required)
    text_length: int = Field(
        ...,
        ge=0,
        description="Character count of the content"
    )
    
    # ADDITIONAL FIELDS (Optional)
    language: str = Field(
        default="en",
        description="Content language (ISO 639-1 code)",
        max_length=5
    )
    
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Required knowledge before learning this content"
    )
    
    learning_outcomes: List[str] = Field(
        default_factory=list,
        description="Skills/knowledge gained from this content"
    )
    
    @field_validator('schema_version')
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        """Ensure schema version follows semver format"""
        supported_versions = ["1.0.0"]
        if v not in supported_versions:
            raise ValueError(
                f"Unsupported schema version: {v}. "
                f"Supported versions: {supported_versions}"
            )
        return v
    
    @field_validator('quality_breakdown')
    @classmethod
    def validate_quality_breakdown(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate 5-factor quality breakdown structure"""
        if v is None:
            return v
        
        required_factors = ["relevance", "authority", "engagement", "freshness", "completeness"]
        
        # Check all factors present
        if set(v.keys()) != set(required_factors):
            raise ValueError(
                f"quality_breakdown must contain exactly: {required_factors}. "
                f"Got: {list(v.keys())}"
            )
        
        # Check all values in [0, 1]
        for factor, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(
                    f"Quality factor '{factor}' must be between 0.0 and 1.0. "
                    f"Got: {score}"
                )
        
        return v
    
    @model_validator(mode='after')
    def populate_derived_fields(self) -> 'UnifiedMetadata':
        """Auto-populate derived fields for backward compatibility"""
        
        # Auto-generate instrument_id if not provided
        if self.instrument_id is None:
            if self.subdomain_id:
                self.instrument_id = f"{self.domain_id}_{self.subdomain_id}"
            else:
                self.instrument_id = self.domain_id
        
        # Sync skill_level with difficulty
        if self.skill_level is None:
            self.skill_level = self.difficulty.value
        
        # Sync quality_score with helpfulness_score
        if self.quality_score is None:
            self.quality_score = self.helpfulness_score
        
        return self
    
    def to_chroma_metadata(self) -> Dict[str, Any]:
        """
        Convert to ChromaDB-compatible metadata dict.
        
        ChromaDB metadata constraints:
        - Keys must be strings
        - Values must be str, int, float, or bool (no nested dicts/lists in older versions)
        - For nested data, serialize to JSON string
        
        Returns:
            Flat dictionary suitable for ChromaDB metadata
        """
        import json
        
        return {
            "schema_version": self.schema_version,
            "domain_id": self.domain_id,
            "subdomain_id": self.subdomain_id or "",
            "instrument_id": self.instrument_id or "",
            "source": self.source,
            "platform": self.platform.value,
            "content_type": self.content_type.value,
            "author": self.author or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "indexed_at": self.indexed_at.isoformat(),
            "difficulty": self.difficulty.value,
            "skill_level": self.skill_level or self.difficulty.value,
            "technique": self.technique or "",
            "tags": json.dumps(self.tags),  # Serialize list to JSON
            "helpfulness_score": self.helpfulness_score,
            "quality_score": self.quality_score or self.helpfulness_score,
            "quality_breakdown": json.dumps(self.quality_breakdown) if self.quality_breakdown else "",
            "engagement_metrics": json.dumps(self.engagement_metrics) if self.engagement_metrics else "",
            "text_length": self.text_length,
            "language": self.language,
            "prerequisites": json.dumps(self.prerequisites),
            "learning_outcomes": json.dumps(self.learning_outcomes)
        }
    
    @classmethod
    def from_chroma_metadata(cls, metadata: Dict[str, Any]) -> 'UnifiedMetadata':
        """
        Reconstruct UnifiedMetadata from ChromaDB metadata.
        
        Args:
            metadata: Flat metadata dict from ChromaDB
            
        Returns:
            UnifiedMetadata instance
        """
        import json
        
        # Parse JSON fields
        tags = json.loads(metadata.get("tags", "[]"))
        quality_breakdown = json.loads(metadata["quality_breakdown"]) if metadata.get("quality_breakdown") else None
        engagement_metrics = json.loads(metadata["engagement_metrics"]) if metadata.get("engagement_metrics") else None
        prerequisites = json.loads(metadata.get("prerequisites", "[]"))
        learning_outcomes = json.loads(metadata.get("learning_outcomes", "[]"))
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else None
        indexed_at = datetime.fromisoformat(metadata["indexed_at"]) if metadata.get("indexed_at") else datetime.utcnow()
        
        return cls(
            schema_version=metadata.get("schema_version", "1.0.0"),
            domain_id=metadata["domain_id"],
            subdomain_id=metadata.get("subdomain_id") or None,
            instrument_id=metadata.get("instrument_id") or None,
            source=metadata["source"],
            platform=Platform(metadata.get("platform", "manual")),
            content_type=ContentType(metadata.get("content_type", "article")),
            author=metadata.get("author") or None,
            created_at=created_at,
            indexed_at=indexed_at,
            difficulty=Difficulty(metadata["difficulty"]),
            skill_level=metadata.get("skill_level"),
            technique=metadata.get("technique") or None,
            tags=tags,
            helpfulness_score=float(metadata["helpfulness_score"]),
            quality_score=float(metadata.get("quality_score", metadata["helpfulness_score"])),
            quality_breakdown=quality_breakdown,
            engagement_metrics=engagement_metrics,
            text_length=int(metadata["text_length"]),
            language=metadata.get("language", "en"),
            prerequisites=prerequisites,
            learning_outcomes=learning_outcomes
        )
    
    model_config = ConfigDict(
        use_enum_values=False,  # Keep enum types in model
        json_schema_extra={
            "example": {
                "schema_version": "1.0.0",
                "domain_id": "MUSIC",
                "subdomain_id": "PIANO",
                "instrument_id": "MUSIC_PIANO",
                "source": "https://youtube.com/watch?v=abc123",
                "platform": "youtube",
                "content_type": "video",
                "author": "PianoTutorials",
                "created_at": "2024-01-15T10:00:00Z",
                "indexed_at": "2024-01-20T15:30:00Z",
                "difficulty": "intermediate",
                "skill_level": "intermediate",
                "technique": "chord progressions",
                "tags": ["jazz", "improvisation", "theory"],
                "helpfulness_score": 0.87,
                "quality_score": 0.87,
                "quality_breakdown": {
                    "relevance": 0.92,
                    "authority": 0.85,
                    "engagement": 0.88,
                    "freshness": 0.75,
                    "completeness": 0.95
                },
                "engagement_metrics": {
                    "views": 15000,
                    "likes": 850,
                    "comments": 120
                },
                "text_length": 2500,
                "language": "en",
                "prerequisites": ["basic music theory", "can read sheet music"],
                "learning_outcomes": ["understand jazz chord progressions", "improvise over ii-V-I"]
            }
        }
    )


# Convenience functions for common use cases

def create_bot_metadata(
    domain_id: str,
    source: str,
    platform: Platform,
    difficulty: Difficulty,
    text_length: int,
    helpfulness_score: float,
    subdomain_id: Optional[str] = None,
    **kwargs
) -> UnifiedMetadata:
    """
    Helper function for bot crawlers to create metadata quickly.
    
    Example:
        metadata = create_bot_metadata(
            domain_id="MUSIC",
            subdomain_id="GUITAR",
            source="https://youtube.com/watch?v=xyz",
            platform=Platform.YOUTUBE,
            difficulty=Difficulty.BEGINNER,
            text_length=1500,
            helpfulness_score=0.92,
            author="GuitarLessons",
            quality_breakdown={
                "relevance": 0.95,
                "authority": 0.90,
                "engagement": 0.88,
                "freshness": 0.85,
                "completeness": 0.92
            }
        )
    """
    return UnifiedMetadata(
        domain_id=domain_id,
        subdomain_id=subdomain_id,
        source=source,
        platform=platform,
        difficulty=difficulty,
        text_length=text_length,
        helpfulness_score=helpfulness_score,
        **kwargs
    )


def create_manual_metadata(
    instrument_id: str,
    source: str,
    difficulty: Difficulty,
    text_length: int,
    helpfulness_score: float,
    **kwargs
) -> UnifiedMetadata:
    """
    Helper function for manual content ingestion (existing IntakeAgent).
    
    Intelligently parses instrument_id to handle multi-part domain names:
    - "MUSIC_PIANO" → domain="MUSIC", subdomain="PIANO"
    - "CODING_SOFTWARE_JAVASCRIPT" → domain="CODING_SOFTWARE", subdomain="JAVASCRIPT"
    - "DATA_SCIENCE_PYTHON" → domain="DATA_SCIENCE", subdomain="PYTHON"
    
    Example:
        metadata = create_manual_metadata(
            instrument_id="MUSIC_PIANO",
            source="manual_upload_001.pdf",
            difficulty=Difficulty.ADVANCED,
            text_length=3200,
            helpfulness_score=0.85,
            technique="bebop scales"
        )
    """
    # Known multi-word domains (from domains.json)
    MULTI_WORD_DOMAINS = {
        "CODING_SOFTWARE", "DATA_SCIENCE", "VISUAL_ARTS", "DIGITAL_DESIGN",
        "FILM_VIDEO", "FOREIGN_LANGUAGES", "HEALTH_FITNESS", "HOME_IMPROVEMENT",
        "PERSONAL_FINANCE", "BUSINESS_ENTREPRENEURSHIP", "CREATIVE_WRITING",
        "PUBLIC_SPEAKING", "GAME_DEVELOPMENT", "WEB_DEVELOPMENT", "MOBILE_DEVELOPMENT",
        "CYBER_SECURITY", "CLOUD_COMPUTING", "MACHINE_LEARNING", "ARTIFICIAL_INTELLIGENCE",
        "NETWORK_ENGINEERING", "SYSTEM_ADMINISTRATION", "DATABASE_MANAGEMENT",
        "QUANTUM_COMPUTING", "POLITICAL_SCIENCE", "SOCIAL_SCIENCES", "ENVIRONMENTAL_SCIENCE",
        "COMPUTER_SCIENCE", "MATERIALS_SCIENCE", "LIFE_SCIENCES", "EARTH_SCIENCES"
    }
    
    # Try to match against known multi-word domains first
    domain_id = None
    subdomain_id = None
    
    for multi_domain in MULTI_WORD_DOMAINS:
        if instrument_id.startswith(multi_domain + "_"):
            domain_id = multi_domain
            subdomain_id = instrument_id[len(multi_domain) + 1:]  # Everything after "DOMAIN_"
            break
    
    # If no multi-word match, use simple split
    if domain_id is None:
        parts = instrument_id.split("_", 1)
        domain_id = parts[0]
        subdomain_id = parts[1] if len(parts) > 1 else None
    
    return UnifiedMetadata(
        domain_id=domain_id,
        subdomain_id=subdomain_id,
        instrument_id=instrument_id,
        source=source,
        platform=Platform.MANUAL,
        difficulty=difficulty,
        text_length=text_length,
        helpfulness_score=helpfulness_score,
        **kwargs
    )
