"""
Test suite for UnifiedMetadata schema
======================================

Run with: pytest tests/test_unified_metadata.py -v
"""

import pytest
from datetime import datetime
from src.models.unified_metadata_schema import (
    UnifiedMetadata,
    Platform,
    ContentType,
    Difficulty,
    create_bot_metadata,
    create_manual_metadata
)


class TestUnifiedMetadata:
    """Test UnifiedMetadata schema validation and methods"""
    
    def test_minimal_valid_metadata(self):
        """Test creation with only required fields"""
        metadata = UnifiedMetadata(
            domain_id="MUSIC",
            source="https://youtube.com/watch?v=test123",
            difficulty=Difficulty.BEGINNER,
            text_length=1000,
            helpfulness_score=0.85
        )
        
        assert metadata.domain_id == "MUSIC"
        assert metadata.instrument_id == "MUSIC"  # Auto-generated
        assert metadata.skill_level == "beginner"  # Auto-synced
        assert metadata.quality_score == 0.85  # Auto-synced
    
    def test_full_metadata_with_subdomain(self):
        """Test creation with subdomain and all optional fields"""
        metadata = UnifiedMetadata(
            domain_id="MUSIC",
            subdomain_id="PIANO",
            source="https://youtube.com/watch?v=abc123",
            platform=Platform.YOUTUBE,
            content_type=ContentType.VIDEO,
            author="PianoMaestro",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            difficulty=Difficulty.INTERMEDIATE,
            technique="chord progressions",
            tags=["jazz", "theory", "improvisation"],
            helpfulness_score=0.92,
            quality_breakdown={
                "relevance": 0.95,
                "authority": 0.90,
                "engagement": 0.88,
                "freshness": 0.85,
                "completeness": 0.92
            },
            engagement_metrics={
                "views": 50000,
                "likes": 2500,
                "comments": 340
            },
            text_length=3200,
            language="en",
            prerequisites=["basic music theory"],
            learning_outcomes=["understand jazz progressions"]
        )
        
        assert metadata.instrument_id == "MUSIC_PIANO"  # Auto-generated
        assert metadata.platform == Platform.YOUTUBE
        assert metadata.quality_breakdown["relevance"] == 0.95
        assert metadata.engagement_metrics["views"] == 50000
    
    def test_invalid_helpfulness_score(self):
        """Test that helpfulness_score must be between 0 and 1"""
        with pytest.raises(ValueError):
            UnifiedMetadata(
                domain_id="MUSIC",
                source="test",
                difficulty=Difficulty.BEGINNER,
                text_length=100,
                helpfulness_score=1.5  # Invalid: > 1.0
            )
    
    def test_invalid_quality_breakdown(self):
        """Test that quality_breakdown must have exactly 5 factors"""
        with pytest.raises(ValueError, match="must contain exactly"):
            UnifiedMetadata(
                domain_id="MUSIC",
                source="test",
                difficulty=Difficulty.BEGINNER,
                text_length=100,
                helpfulness_score=0.8,
                quality_breakdown={
                    "relevance": 0.9,
                    "authority": 0.8
                    # Missing 3 factors
                }
            )
    
    def test_quality_breakdown_values_range(self):
        """Test that all quality factors must be 0-1"""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            UnifiedMetadata(
                domain_id="MUSIC",
                source="test",
                difficulty=Difficulty.BEGINNER,
                text_length=100,
                helpfulness_score=0.8,
                quality_breakdown={
                    "relevance": 1.5,  # Invalid: > 1.0
                    "authority": 0.8,
                    "engagement": 0.9,
                    "freshness": 0.7,
                    "completeness": 0.85
                }
            )
    
    def test_schema_version_validation(self):
        """Test that unsupported schema versions are rejected"""
        with pytest.raises(ValueError, match="Unsupported schema version"):
            UnifiedMetadata(
                schema_version="2.0.0",  # Not yet supported
                domain_id="MUSIC",
                source="test",
                difficulty=Difficulty.BEGINNER,
                text_length=100,
                helpfulness_score=0.8
            )


class TestChromaDBSerialization:
    """Test conversion to/from ChromaDB metadata format"""
    
    def test_to_chroma_metadata(self):
        """Test conversion to flat ChromaDB-compatible dict"""
        metadata = UnifiedMetadata(
            domain_id="CODING_SOFTWARE",
            subdomain_id="PYTHON",
            source="https://blog.example.com/python-async",
            platform=Platform.BLOG,
            content_type=ContentType.ARTICLE,
            difficulty=Difficulty.ADVANCED,
            tags=["async", "concurrency", "performance"],
            helpfulness_score=0.88,
            text_length=4500
        )
        
        chroma_dict = metadata.to_chroma_metadata()
        
        # Check required fields
        assert chroma_dict["domain_id"] == "CODING_SOFTWARE"
        assert chroma_dict["subdomain_id"] == "PYTHON"
        assert chroma_dict["instrument_id"] == "CODING_SOFTWARE_PYTHON"
        assert chroma_dict["platform"] == "blog"
        assert chroma_dict["difficulty"] == "advanced"
        assert chroma_dict["helpfulness_score"] == 0.88
        
        # Check JSON-serialized fields
        import json
        tags = json.loads(chroma_dict["tags"])
        assert tags == ["async", "concurrency", "performance"]
    
    def test_from_chroma_metadata(self):
        """Test reconstruction from ChromaDB metadata"""
        chroma_dict = {
            "schema_version": "1.0.0",
            "domain_id": "MUSIC",
            "subdomain_id": "GUITAR",
            "instrument_id": "MUSIC_GUITAR",
            "source": "https://youtube.com/watch?v=xyz",
            "platform": "youtube",
            "content_type": "video",
            "author": "GuitarPro",
            "created_at": "2024-01-15T10:00:00",
            "indexed_at": "2024-01-20T15:30:00",
            "difficulty": "beginner",
            "skill_level": "beginner",
            "technique": "power chords",
            "tags": '["rock", "metal", "beginner"]',
            "helpfulness_score": 0.85,
            "quality_score": 0.85,
            "quality_breakdown": "",
            "engagement_metrics": '{"views": 10000, "likes": 500}',
            "text_length": 2000,
            "language": "en",
            "prerequisites": "[]",
            "learning_outcomes": '["play basic rock songs"]'
        }
        
        metadata = UnifiedMetadata.from_chroma_metadata(chroma_dict)
        
        assert metadata.domain_id == "MUSIC"
        assert metadata.subdomain_id == "GUITAR"
        assert metadata.instrument_id == "MUSIC_GUITAR"
        assert metadata.platform == Platform.YOUTUBE
        assert metadata.difficulty == Difficulty.BEGINNER
        assert metadata.tags == ["rock", "metal", "beginner"]
        assert metadata.engagement_metrics["views"] == 10000
        assert metadata.learning_outcomes == ["play basic rock songs"]
    
    def test_round_trip_serialization(self):
        """Test that metadata survives round-trip to/from ChromaDB format"""
        original = UnifiedMetadata(
            domain_id="LANGUAGES",
            subdomain_id="SPANISH",
            source="https://reddit.com/r/Spanish/comments/xyz",
            platform=Platform.REDDIT,
            content_type=ContentType.DISCUSSION,
            author="SpanishLearner42",
            difficulty=Difficulty.INTERMEDIATE,
            technique="subjunctive mood",
            tags=["grammar", "verbs"],
            helpfulness_score=0.79,
            quality_breakdown={
                "relevance": 0.85,
                "authority": 0.70,
                "engagement": 0.80,
                "freshness": 0.90,
                "completeness": 0.65
            },
            text_length=1500,
            prerequisites=["present tense", "past tense"],
            learning_outcomes=["use subjunctive in conversations"]
        )
        
        # Convert to ChromaDB format
        chroma_dict = original.to_chroma_metadata()
        
        # Convert back
        reconstructed = UnifiedMetadata.from_chroma_metadata(chroma_dict)
        
        # Verify key fields match
        assert reconstructed.domain_id == original.domain_id
        assert reconstructed.subdomain_id == original.subdomain_id
        assert reconstructed.instrument_id == original.instrument_id
        assert reconstructed.platform == original.platform
        assert reconstructed.difficulty == original.difficulty
        assert reconstructed.helpfulness_score == original.helpfulness_score
        assert reconstructed.tags == original.tags
        assert reconstructed.quality_breakdown == original.quality_breakdown
        assert reconstructed.prerequisites == original.prerequisites


class TestHelperFunctions:
    """Test convenience helper functions"""
    
    def test_create_bot_metadata(self):
        """Test create_bot_metadata helper"""
        metadata = create_bot_metadata(
            domain_id="MUSIC",
            subdomain_id="DRUMS",
            source="https://youtube.com/watch?v=drums101",
            platform=Platform.YOUTUBE,
            difficulty=Difficulty.BEGINNER,
            text_length=1800,
            helpfulness_score=0.91,
            author="DrumMaster",
            quality_breakdown={
                "relevance": 0.95,
                "authority": 0.92,
                "engagement": 0.88,
                "freshness": 0.85,
                "completeness": 0.90
            }
        )
        
        assert metadata.instrument_id == "MUSIC_DRUMS"
        assert metadata.platform == Platform.YOUTUBE
        assert metadata.author == "DrumMaster"
    
    def test_create_manual_metadata(self):
        """Test create_manual_metadata helper for legacy IntakeAgent"""
        metadata = create_manual_metadata(
            instrument_id="CODING_SOFTWARE_JAVASCRIPT",
            source="manual_upload_react_hooks.pdf",
            difficulty=Difficulty.INTERMEDIATE,
            text_length=5000,
            helpfulness_score=0.87,
            technique="React Hooks",
            tags=["react", "hooks", "useState", "useEffect"]
        )
        
        assert metadata.domain_id == "CODING_SOFTWARE"
        assert metadata.subdomain_id == "JAVASCRIPT"
        assert metadata.instrument_id == "CODING_SOFTWARE_JAVASCRIPT"
        assert metadata.platform == Platform.MANUAL
        assert metadata.technique == "React Hooks"


class TestBackwardCompatibility:
    """Test backward compatibility with existing RAG system"""
    
    def test_instrument_id_auto_generation(self):
        """Test that instrument_id is auto-generated for RAG compatibility"""
        # With subdomain
        m1 = UnifiedMetadata(
            domain_id="MUSIC",
            subdomain_id="VIOLIN",
            source="test",
            difficulty=Difficulty.BEGINNER,
            text_length=100,
            helpfulness_score=0.8
        )
        assert m1.instrument_id == "MUSIC_VIOLIN"
        
        # Without subdomain
        m2 = UnifiedMetadata(
            domain_id="MUSIC",
            source="test",
            difficulty=Difficulty.BEGINNER,
            text_length=100,
            helpfulness_score=0.8
        )
        assert m2.instrument_id == "MUSIC"
    
    def test_skill_level_sync(self):
        """Test that skill_level is synced with difficulty"""
        metadata = UnifiedMetadata(
            domain_id="MUSIC",
            source="test",
            difficulty=Difficulty.ADVANCED,
            text_length=100,
            helpfulness_score=0.8
        )
        
        assert metadata.skill_level == "advanced"
    
    def test_quality_score_sync(self):
        """Test that quality_score mirrors helpfulness_score"""
        metadata = UnifiedMetadata(
            domain_id="MUSIC",
            source="test",
            difficulty=Difficulty.BEGINNER,
            text_length=100,
            helpfulness_score=0.93
        )
        
        assert metadata.quality_score == 0.93


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
