"""
Quality Scorer for Educational Content

Implements a 5-factor quality assessment algorithm to score content on a 0.0-1.0 scale:
- Relevance (30%): Query-content alignment, keyword matching
- Authority (25%): Channel/source credibility, verification, audience size
- Engagement (20%): Like/view ratio, comment activity, user interaction
- Freshness (15%): Publication date, content recency
- Completeness (10%): Content depth, transcript length, metadata richness

Author: Autodidact AI
Created: October 26, 2025
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re
import math


@dataclass
class ContentMetrics:
    """Raw metrics used for quality scoring."""
    # Relevance metrics
    title: str
    description: str
    transcript: str
    query: str
    tags: List[str] = None
    
    # Authority metrics
    channel_name: str = ""
    subscriber_count: int = 0
    is_verified: bool = False
    view_count: int = 0
    
    # Engagement metrics
    like_count: int = 0
    comment_count: int = 0
    
    # Freshness metrics
    published_at: Optional[datetime] = None
    
    # Completeness metrics
    duration_seconds: int = 0
    has_captions: bool = False
    
    def __post_init__(self):
        """Initialize optional fields."""
        if self.tags is None:
            self.tags = []


@dataclass
class QualityScore:
    """Detailed quality score breakdown."""
    overall: float  # 0.0 - 1.0
    relevance: float  # 0.0 - 1.0
    authority: float  # 0.0 - 1.0
    engagement: float  # 0.0 - 1.0
    freshness: float  # 0.0 - 1.0
    completeness: float  # 0.0 - 1.0
    
    # Weights (should sum to 1.0)
    WEIGHTS = {
        'relevance': 0.30,
        'authority': 0.25,
        'engagement': 0.20,
        'freshness': 0.15,
        'completeness': 0.10
    }
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for logging/storage."""
        return {
            'overall': round(self.overall, 3),
            'relevance': round(self.relevance, 3),
            'authority': round(self.authority, 3),
            'engagement': round(self.engagement, 3),
            'freshness': round(self.freshness, 3),
            'completeness': round(self.completeness, 3)
        }
    
    def __str__(self) -> str:
        """Human-readable score summary."""
        return (
            f"Quality Score: {self.overall:.2f}\n"
            f"  Relevance:    {self.relevance:.2f} (30%)\n"
            f"  Authority:    {self.authority:.2f} (25%)\n"
            f"  Engagement:   {self.engagement:.2f} (20%)\n"
            f"  Freshness:    {self.freshness:.2f} (15%)\n"
            f"  Completeness: {self.completeness:.2f} (10%)"
        )


class QualityScorer:
    """
    Intelligent content quality assessment system.
    
    Evaluates educational content across 5 dimensions to produce
    a comprehensive quality score (0.0 - 1.0).
    """
    
    def __init__(
        self,
        min_score_threshold: float = 0.0,
        relevance_boost: float = 1.0,
        authority_boost: float = 1.0
    ):
        """
        Initialize quality scorer.
        
        Args:
            min_score_threshold: Minimum overall score to pass (0.0 - 1.0)
            relevance_boost: Multiplier for relevance score (default 1.0)
            authority_boost: Multiplier for authority score (default 1.0)
        """
        self.min_score_threshold = min_score_threshold
        self.relevance_boost = relevance_boost
        self.authority_boost = authority_boost
        
        # Statistics
        self.scores_calculated = 0
        self.scores_above_threshold = 0
        self.average_score = 0.0
    
    def score_content(self, metrics: ContentMetrics) -> QualityScore:
        """
        Calculate comprehensive quality score for content.
        
        Args:
            metrics: ContentMetrics with all available data
            
        Returns:
            QualityScore with breakdown by factor
        """
        # Calculate individual factor scores
        relevance = self._score_relevance(metrics) * self.relevance_boost
        authority = self._score_authority(metrics) * self.authority_boost
        engagement = self._score_engagement(metrics)
        freshness = self._score_freshness(metrics)
        completeness = self._score_completeness(metrics)
        
        # Clamp boosted scores to [0, 1]
        relevance = min(1.0, max(0.0, relevance))
        authority = min(1.0, max(0.0, authority))
        
        # Calculate weighted overall score
        overall = (
            relevance * QualityScore.WEIGHTS['relevance'] +
            authority * QualityScore.WEIGHTS['authority'] +
            engagement * QualityScore.WEIGHTS['engagement'] +
            freshness * QualityScore.WEIGHTS['freshness'] +
            completeness * QualityScore.WEIGHTS['completeness']
        )
        
        # Update statistics
        self.scores_calculated += 1
        if overall >= self.min_score_threshold:
            self.scores_above_threshold += 1
        self.average_score = (
            (self.average_score * (self.scores_calculated - 1) + overall) /
            self.scores_calculated
        )
        
        return QualityScore(
            overall=overall,
            relevance=relevance,
            authority=authority,
            engagement=engagement,
            freshness=freshness,
            completeness=completeness
        )
    
    def passes_threshold(self, score: QualityScore) -> bool:
        """Check if score meets minimum threshold."""
        return score.overall >= self.min_score_threshold
    
    # ========================================================================
    # RELEVANCE SCORING (30%)
    # ========================================================================
    
    def _score_relevance(self, metrics: ContentMetrics) -> float:
        """
        Score query-content alignment (0.0 - 1.0).
        
        Factors:
        - Keyword overlap between query and title (40%)
        - Keyword overlap with description (30%)
        - Keyword overlap with transcript (20%)
        - Tag relevance (10%)
        """
        query_keywords = self._extract_keywords(metrics.query)
        
        # Title relevance (most important)
        title_keywords = self._extract_keywords(metrics.title)
        title_overlap = self._keyword_overlap(query_keywords, title_keywords)
        title_score = min(1.0, title_overlap / max(1, len(query_keywords)))
        
        # Description relevance
        desc_keywords = self._extract_keywords(metrics.description)
        desc_overlap = self._keyword_overlap(query_keywords, desc_keywords)
        desc_score = min(1.0, desc_overlap / max(1, len(query_keywords)))
        
        # Transcript relevance (deeper content check)
        # Sample first 500 chars to avoid processing huge transcripts
        transcript_sample = metrics.transcript[:500] if metrics.transcript else ""
        transcript_keywords = self._extract_keywords(transcript_sample)
        transcript_overlap = self._keyword_overlap(query_keywords, transcript_keywords)
        transcript_score = min(1.0, transcript_overlap / max(1, len(query_keywords)))
        
        # Tag relevance
        tag_keywords = set()
        for tag in (metrics.tags or []):
            tag_keywords.update(self._extract_keywords(tag))
        tag_overlap = self._keyword_overlap(query_keywords, tag_keywords)
        tag_score = min(1.0, tag_overlap / max(1, len(query_keywords))) if query_keywords else 0.0
        
        # Weighted combination
        relevance = (
            title_score * 0.40 +
            desc_score * 0.30 +
            transcript_score * 0.20 +
            tag_score * 0.10
        )
        
        return relevance
    
    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text."""
        if not text:
            return set()
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and split
        words = re.findall(r'\b[a-z0-9]+\b', text)
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just'
        }
        
        # Filter and return
        keywords = {w for w in words if len(w) > 2 and w not in stop_words}
        return keywords
    
    def _keyword_overlap(self, set1: set, set2: set) -> int:
        """Count overlapping keywords between two sets."""
        return len(set1 & set2)
    
    # ========================================================================
    # AUTHORITY SCORING (25%)
    # ========================================================================
    
    def _score_authority(self, metrics: ContentMetrics) -> float:
        """
        Score source credibility and reach (0.0 - 1.0).
        
        Factors:
        - Subscriber count (40%)
        - Verification status (30%)
        - View count (30%)
        """
        # Subscriber score (logarithmic scale)
        # 1K subs = 0.3, 10K = 0.5, 100K = 0.7, 1M+ = 0.9+
        if metrics.subscriber_count > 0:
            subscriber_score = min(1.0, math.log10(metrics.subscriber_count) / 6.5)
        else:
            subscriber_score = 0.0
        
        # Verification boost
        verification_score = 1.0 if metrics.is_verified else 0.5
        
        # View count score (logarithmic scale)
        # 1K views = 0.3, 10K = 0.5, 100K = 0.7, 1M+ = 0.9+
        if metrics.view_count > 0:
            view_score = min(1.0, math.log10(metrics.view_count) / 6.5)
        else:
            view_score = 0.0
        
        # Weighted combination
        authority = (
            subscriber_score * 0.40 +
            verification_score * 0.30 +
            view_score * 0.30
        )
        
        return authority
    
    # ========================================================================
    # ENGAGEMENT SCORING (20%)
    # ========================================================================
    
    def _score_engagement(self, metrics: ContentMetrics) -> float:
        """
        Score user interaction and engagement (0.0 - 1.0).
        
        Factors:
        - Like/view ratio (60%)
        - Comment activity (40%)
        """
        # Like ratio (aim for 3-5% as "good")
        if metrics.view_count > 0:
            like_ratio = metrics.like_count / metrics.view_count
            # 5%+ = 1.0, 3% = 0.8, 1% = 0.5, <0.5% = lower
            like_score = min(1.0, like_ratio / 0.05)
        else:
            like_score = 0.0
        
        # Comment activity (logarithmic scale)
        # 10 comments = 0.3, 100 = 0.6, 1000+ = 0.9+
        if metrics.comment_count > 0:
            comment_score = min(1.0, math.log10(metrics.comment_count + 1) / 3.5)
        else:
            comment_score = 0.0
        
        # Weighted combination
        engagement = (
            like_score * 0.60 +
            comment_score * 0.40
        )
        
        return engagement
    
    # ========================================================================
    # FRESHNESS SCORING (15%)
    # ========================================================================
    
    def _score_freshness(self, metrics: ContentMetrics) -> float:
        """
        Score content recency (0.0 - 1.0).
        
        Factors:
        - Age of content (decay curve)
        - < 1 month = 1.0
        - < 6 months = 0.9
        - < 1 year = 0.7
        - < 2 years = 0.5
        - > 3 years = 0.3
        """
        if not metrics.published_at:
            return 0.5  # Unknown age = neutral score
        
        age = datetime.now() - metrics.published_at
        age_days = age.total_seconds() / 86400
        
        if age_days < 30:
            return 1.0
        elif age_days < 180:  # 6 months
            return 0.9
        elif age_days < 365:  # 1 year
            return 0.7
        elif age_days < 730:  # 2 years
            return 0.5
        elif age_days < 1095:  # 3 years
            return 0.3
        else:
            return 0.2
    
    # ========================================================================
    # COMPLETENESS SCORING (10%)
    # ========================================================================
    
    def _score_completeness(self, metrics: ContentMetrics) -> float:
        """
        Score content depth and metadata richness (0.0 - 1.0).
        
        Factors:
        - Transcript length (40%)
        - Duration (30%)
        - Caption availability (20%)
        - Description richness (10%)
        """
        # Transcript completeness
        # 500+ words = 1.0, 200-500 = 0.7, <100 = 0.3
        transcript_words = len(metrics.transcript.split()) if metrics.transcript else 0
        if transcript_words >= 500:
            transcript_score = 1.0
        elif transcript_words >= 200:
            transcript_score = 0.7
        elif transcript_words >= 100:
            transcript_score = 0.5
        else:
            transcript_score = 0.3
        
        # Duration (for video content)
        # 10-30 min = 1.0, 5-10 min = 0.8, <5 min = 0.5, >60 min = 0.7
        duration_min = metrics.duration_seconds / 60 if metrics.duration_seconds else 0
        if 10 <= duration_min <= 30:
            duration_score = 1.0
        elif 5 <= duration_min < 10:
            duration_score = 0.8
        elif 30 < duration_min <= 60:
            duration_score = 0.9
        elif duration_min < 5:
            duration_score = 0.5
        else:
            duration_score = 0.7
        
        # Caption availability
        caption_score = 1.0 if metrics.has_captions else 0.3
        
        # Description richness
        desc_words = len(metrics.description.split()) if metrics.description else 0
        if desc_words >= 50:
            desc_score = 1.0
        elif desc_words >= 20:
            desc_score = 0.7
        else:
            desc_score = 0.4
        
        # Weighted combination
        completeness = (
            transcript_score * 0.40 +
            duration_score * 0.30 +
            caption_score * 0.20 +
            desc_score * 0.10
        )
        
        return completeness
    
    # ========================================================================
    # STATISTICS & UTILITIES
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scorer statistics."""
        return {
            'scores_calculated': self.scores_calculated,
            'scores_above_threshold': self.scores_above_threshold,
            'pass_rate': (
                self.scores_above_threshold / self.scores_calculated
                if self.scores_calculated > 0 else 0.0
            ),
            'average_score': round(self.average_score, 3),
            'min_threshold': self.min_score_threshold
        }
    
    def reset_statistics(self):
        """Reset scorer statistics."""
        self.scores_calculated = 0
        self.scores_above_threshold = 0
        self.average_score = 0.0


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    print("=" * 70)
    print("Quality Scorer Demo")
    print("=" * 70)
    
    # Initialize scorer with 0.6 minimum threshold
    scorer = QualityScorer(min_score_threshold=0.6)
    
    # Test Case 1: High-quality educational video
    print("\n📊 Test Case 1: High-Quality Educational Video")
    print("-" * 70)
    
    high_quality = ContentMetrics(
        query="learn piano for beginners",
        title="Piano Basics: Complete Beginner's Guide to Piano",
        description="Comprehensive 30-minute tutorial covering hand position, note reading, scales, and your first songs. Perfect for absolute beginners starting their piano journey.",
        transcript="Welcome to piano basics. In this video we'll cover everything you need to know as a beginner. First, let's talk about hand position and proper posture..." * 20,  # ~400 words
        tags=["piano", "beginner", "tutorial", "music education"],
        channel_name="Piano Academy",
        subscriber_count=250000,
        is_verified=True,
        view_count=50000,
        like_count=2500,  # 5% like ratio
        comment_count=300,
        published_at=datetime.now() - timedelta(days=15),
        duration_seconds=1800,  # 30 minutes
        has_captions=True
    )
    
    score1 = scorer.score_content(high_quality)
    print(score1)
    print(f"\n✅ Passes Threshold: {scorer.passes_threshold(score1)}")
    
    # Test Case 2: Low-quality spam video
    print("\n\n📊 Test Case 2: Low-Quality Spam Video")
    print("-" * 70)
    
    low_quality = ContentMetrics(
        query="learn piano for beginners",
        title="CLICK HERE FOR FREE STUFF!!!",
        description="Subscribe now!",
        transcript="Hey guys, don't forget to like and subscribe!",
        tags=["viral", "trending"],
        channel_name="RandomUser123",
        subscriber_count=50,
        is_verified=False,
        view_count=100,
        like_count=2,  # 2% like ratio
        comment_count=1,
        published_at=datetime.now() - timedelta(days=1000),  # 3 years old
        duration_seconds=120,  # 2 minutes
        has_captions=False
    )
    
    score2 = scorer.score_content(low_quality)
    print(score2)
    print(f"\n❌ Passes Threshold: {scorer.passes_threshold(score2)}")
    
    # Test Case 3: Medium-quality video
    print("\n\n📊 Test Case 3: Medium-Quality Video")
    print("-" * 70)
    
    medium_quality = ContentMetrics(
        query="learn piano for beginners",
        title="My Piano Learning Journey",
        description="Sharing my experience learning piano over the past 6 months.",
        transcript="Hi everyone, today I want to talk about my piano journey. I started 6 months ago and here's what I've learned. Practice is really important and you should try to practice every day..." * 10,  # ~200 words
        tags=["piano", "learning", "personal"],
        channel_name="Music Enthusiast",
        subscriber_count=5000,
        is_verified=False,
        view_count=1000,
        like_count=30,  # 3% like ratio
        comment_count=15,
        published_at=datetime.now() - timedelta(days=60),  # 2 months old
        duration_seconds=600,  # 10 minutes
        has_captions=True
    )
    
    score3 = scorer.score_content(medium_quality)
    print(score3)
    print(f"\n⚠️  Passes Threshold: {scorer.passes_threshold(score3)}")
    
    # Final statistics
    print("\n\n" + "=" * 70)
    print("Scorer Statistics")
    print("=" * 70)
    stats = scorer.get_statistics()
    print(f"Total Scores Calculated: {stats['scores_calculated']}")
    print(f"Scores Above Threshold: {stats['scores_above_threshold']}")
    print(f"Pass Rate: {stats['pass_rate']:.1%}")
    print(f"Average Score: {stats['average_score']:.3f}")
    print(f"Minimum Threshold: {stats['min_threshold']:.2f}")
