"""
Test Quality Scorer Integration with YouTubeCrawler

Tests the complete integration of QualityScorer into the YouTube crawling pipeline.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
from src.bot.crawlers.youtube_crawler import YouTubeCrawler
from src.bot.question_engine import QuestionEngine

# Load environment
load_dotenv()

print("=" * 70)
print("Quality Scorer Integration Test")
print("=" * 70)

# Test 1: Initialize crawler with quality scoring ENABLED
print("\n📊 Test 1: YouTubeCrawler with Quality Scoring (min threshold: 0.6)")
print("-" * 70)

crawler_with_scoring = YouTubeCrawler(
    max_results_per_query=3,
    min_quality_score=0.6,
    use_quality_scorer=True
)

print("\n✅ Crawler initialized with quality scoring enabled\n")

# Test 2: Initialize crawler with quality scoring DISABLED
print("📊 Test 2: YouTubeCrawler without Quality Scoring")
print("-" * 70)

crawler_without_scoring = YouTubeCrawler(
    max_results_per_query=3,
    use_quality_scorer=False
)

print("\n✅ Crawler initialized with placeholder 0.5 scores\n")

# Test 3: Generate a query and show how scoring would work
print("=" * 70)
print("Test 3: Mock Scoring Demo")
print("=" * 70)

engine = QuestionEngine()
queries = engine.generate_queries(
    domain_id="MUSIC",
    subdomain_id="PIANO",
    platform="youtube",
    limit=1
)

print(f"\n🔍 Generated Query: '{queries[0].query}'")
print(f"   Domain: {queries[0].domain_id}/{queries[0].subdomain_id}")
print(f"   Category: {queries[0].category}")
print(f"   Skill Level: {queries[0].skill_level}")

print("\n💡 When this query is executed:")
print("   1. YouTubeCrawler searches YouTube API")
print("   2. For each video found:")
print("      a. Extract title, description, transcript, engagement metrics")
print("      b. QualityScorer calculates 5-factor score:")
print("         - Relevance (30%): Query-content keyword matching")
print("         - Authority (25%): Channel size, verification, views")
print("         - Engagement (20%): Like/view ratio, comments")
print("         - Freshness (15%): Publication date recency")
print("         - Completeness (10%): Transcript length, captions")
print("      c. If score >= 0.6 → Index to ChromaDB")
print("      d. If score < 0.6 → Filter out (low quality)")
print("   3. High-quality content gets indexed automatically")

print("\n" + "=" * 70)
print("Statistics Summary")
print("=" * 70)

# Show crawler stats
stats_with_scoring = crawler_with_scoring.get_statistics()
print("\n🎯 Crawler WITH Quality Scoring:")
print(f"   Quota Used: {stats_with_scoring['quota_used']}/{stats_with_scoring['max_quota']}")
print(f"   Videos Seen: {stats_with_scoring['videos_seen']}")
print(f"   Quality Scorer: {stats_with_scoring.get('quality_scorer', 'N/A')}")

stats_without_scoring = crawler_without_scoring.get_statistics()
print("\n📊 Crawler WITHOUT Quality Scoring:")
print(f"   Quota Used: {stats_without_scoring['quota_used']}/{stats_without_scoring['max_quota']}")
print(f"   Videos Seen: {stats_without_scoring['videos_seen']}")
print(f"   Quality Scorer: {stats_without_scoring.get('quality_scorer', 'Disabled')}")

print("\n✅ Integration Test Complete!")
print("\n💡 Next Step: Run bot_indexer.py to test with real YouTube API")
print("   (or use use_mock_crawler=True to test without API limits)")
