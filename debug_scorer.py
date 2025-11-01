#!/usr/bin/env python3
"""
Debug Quality Scorer
Test what score is produced with minimal/empty data
"""
import sys
import os
sys.path.insert(0, '/Users/victorcrispin/Dev/autodidact-ai-core')

from src.bot.quality_scorer import QualityScorer, ContentMetrics
from datetime import datetime

# Test with minimal data (like what's in the worker)
metrics = ContentMetrics(
    title="Test Video",
    description="Test description",
    transcript="Test transcript",
    query='',  # EMPTY QUERY - This is the problem!
    tags=[],
    channel_name="Test Channel",
    subscriber_count=0,  # No data
    is_verified=False,
    view_count=0,  # No data
    like_count=0,
    comment_count=0,
    published_at=None,
    duration_seconds=0,
    has_captions=True,
)

scorer = QualityScorer()
score = scorer.score_content(metrics)

print("Score with EMPTY query and minimal data:")
print(score)
print()
print(f"Overall: {score.overall}")
print(f"Expected: 0.244 (what you're seeing)")
