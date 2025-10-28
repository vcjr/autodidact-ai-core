"""
Test Apify Integration with BotIndexer
=======================================

Test the Apify YouTube crawler integrated into the main indexing pipeline.
Tests with real domain queries: piano tutorials and machine learning courses.
"""

from src.bot.bot_indexer import BotIndexer
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("Testing Apify YouTube Crawler Integration")
print("=" * 70)

# Initialize with Apify
print("\n🚀 Initializing BotIndexer with Apify...\n")
indexer = BotIndexer(use_apify=True, use_mock_crawler=False)

# Test 1: Piano tutorials (beginner)
print("\n" + "=" * 70)
print("Test 1: Piano Tutorials (Beginner)")
print("=" * 70)

stats1 = indexer.index_domain(
    domain_id="MUSIC",
    subdomain_id="PIANO",
    skill_level="beginner",
    num_queries=2,  # Small test
    videos_per_query=2,
    delay_seconds=1.0
)

# Test 2: Machine Learning courses
print("\n" + "=" * 70)
print("Test 2: Machine Learning Courses")
print("=" * 70)

stats2 = indexer.index_domain(
    domain_id="CODING_SOFTWARE",
    subdomain_id="MACHINE_LEARNING",
    skill_level="beginner",
    num_queries=2,  # Small test
    videos_per_query=2,
    delay_seconds=1.0
)

# Final summary
print("\n" + "=" * 70)
print("Overall Test Summary")
print("=" * 70)

total_queries = stats1['queries_generated'] + stats2['queries_generated']
total_videos = stats1['videos_indexed'] + stats2['videos_indexed']

print(f"Total Queries: {total_queries}")
print(f"Total Videos Indexed: {total_videos}")
print(f"Test 1 Success Rate: {stats1['videos_indexed'] / max(stats1['videos_crawled'], 1):.1%}")
print(f"Test 2 Success Rate: {stats2['videos_indexed'] / max(stats2['videos_crawled'], 1):.1%}")

print("\n✅ Integration test complete!")
