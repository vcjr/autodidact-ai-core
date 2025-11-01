#!/usr/bin/env python3
"""
Quick MVP Indexing - Using Message Queue System
================================================

This script integrates BotIndexer's search capabilities with the message queue
for async, scalable processing.

Flow:
1. QuestionEngine generates search queries
2. ApifyCrawler searches for videos (just URLs, no transcripts yet)
3. Submit video URLs to RabbitMQ queue
4. Workers process asynchronously (transcription → quality → embedding)

Time: 30-45 minutes total
  - Search: 5-10 min (fast)
  - Queue processing: 20-30 min (async, workers handle it)
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator
from src.bot.question_engine import QuestionEngine, SearchQuery
from src.bot.crawlers.apify_youtube_crawler import ApifyYouTubeCrawler
from typing import List


def search_videos_for_queue(
    crawler: ApifyYouTubeCrawler,
    query: SearchQuery,
    max_results: int = 5
) -> List[dict]:
    """
    Search for videos and return URLs + metadata (no transcripts).
    
    Args:
        crawler: Apify YouTube crawler
        query: Search query from QuestionEngine
        max_results: Max videos to return
        
    Returns:
        List of dicts with {url, metadata}
    """
    print(f"🔍 Searching: '{query.query}'")
    
    # Use Apify to search (it returns metadata + transcripts)
    videos = crawler.search_videos(query.query, max_results=max_results)
    
    # Extract just URLs and metadata (we'll get transcripts from workers)
    results = []
    for video in videos:
        results.append({
            'url': f"https://www.youtube.com/watch?v={video['video_id']}",
            'metadata': {
                'domain_id': query.domain_id,
                'subdomain_id': query.subdomain_id or query.domain_id,
                'difficulty': query.skill_level,
                'platform': 'youtube',
                'category': query.category,
                'search_query': query.query
            }
        })
    
    return results


def quick_mvp_index_with_queue():
    """
    Index core domains using message queue for async processing.
    """
    
    print("\n" + "="*70)
    print("MVP Quick Indexing Script (Message Queue)")
    print("="*70)
    print("\nThis will search for videos and submit to queue for async processing.")
    print("Make sure services are running:")
    print("  docker-compose up -d\n")
    print("Estimated time:")
    print("  - Search & submit: 5-10 minutes")
    print("  - Queue processing: 20-30 minutes (happens in background)")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    input()
    
    # Initialize components
    orchestrator = IndexingOrchestrator()
    question_engine = QuestionEngine()
    
    # Use Apify for reliable searching (set use_quality_scorer=False since workers will do it)
    crawler = ApifyYouTubeCrawler(
        max_results_per_query=5,
        use_quality_scorer=False  # Workers will handle quality scoring
    )
    
    # Define MVP content strategy
    mvp_domains = [
        {'domain_id': 'MUSIC', 'subdomain_id': 'PIANO', 'skill_level': 'beginner', 'num_queries': 3},
        {'domain_id': 'MUSIC', 'subdomain_id': 'PIANO', 'skill_level': 'intermediate', 'num_queries': 2},
        {'domain_id': 'MUSIC', 'subdomain_id': 'PIANO', 'skill_level': 'advanced', 'num_queries': 2},
        
        {'domain_id': 'MUSIC', 'subdomain_id': 'GUITAR', 'skill_level': 'beginner', 'num_queries': 2},
        {'domain_id': 'MUSIC', 'subdomain_id': 'GUITAR', 'skill_level': 'intermediate', 'num_queries': 2},
        
        {'domain_id': 'CODING_SOFTWARE', 'subdomain_id': 'PYTHON', 'skill_level': 'beginner', 'num_queries': 3},
        {'domain_id': 'CODING_SOFTWARE', 'subdomain_id': 'PYTHON', 'skill_level': 'intermediate', 'num_queries': 2},
    ]
    
    total_searched = 0
    total_submitted = 0
    
    for i, config in enumerate(mvp_domains, 1):
        print("\n" + "="*70)
        print(f"Domain {i}/{len(mvp_domains)}: {config['domain_id']} / {config['subdomain_id']} ({config['skill_level']})")
        print("="*70)
        
        # Generate queries
        queries = question_engine.generate_queries(
            domain_id=config['domain_id'],
            subdomain_id=config['subdomain_id'],
            skill_level=config['skill_level'],
            limit=config['num_queries']
        )
        
        print(f"\n📝 Generated {len(queries)} queries:")
        for q in queries:
            print(f"   - {q.query}")
        
        # Search for videos
        print(f"\n🎬 Searching for videos...")
        
        for query in queries:
            try:
                videos = search_videos_for_queue(crawler, query, max_results=3)
                total_searched += len(videos)
                
                # Submit to queue
                for video in videos:
                    success = orchestrator.submit_video_for_indexing(
                        video['url'],
                        video['metadata']
                    )
                    
                    if success:
                        total_submitted += 1
                        print(f"   ✅ Submitted: {video['url']}")
                    else:
                        print(f"   ❌ Failed: {video['url']}")
                
            except Exception as e:
                print(f"   ❌ Error searching '{query.query}': {e}")
    
    # Print final summary
    print("\n" + "="*70)
    print("MVP Indexing Complete!")
    print("="*70)
    print(f"🔍 Total Videos Found: {total_searched}")
    print(f"📤 Total Submitted to Queue: {total_submitted}")
    print(f"📊 Success Rate: {(total_submitted / max(total_searched, 1) * 100):.1f}%")
    
    print("\n🎯 Next Steps:")
    print("   1. Monitor queue: http://localhost:15672 (autodidact/rabbitmq_password)")
    print("   2. Watch workers: docker-compose logs -f transcription_worker")
    print("   3. Wait for processing (~20-30 min)")
    print("   4. Build graph: python scripts/build_knowledge_graph.py")
    print("   5. Test: python -m src.agents.question_agent_v2")
    print("="*70 + "\n")
    
    # Close connection
    orchestrator.close()


if __name__ == "__main__":
    quick_mvp_index_with_queue()
