#!/usr/bin/env python3
"""
Minimal MVP Indexing - Using Message Queue
===========================================

Uses the RabbitMQ message queue system for async, scalable indexing.
This is the RECOMMENDED approach for MVP.

Time: ~5-10 minutes for 15-20 videos (processed asynchronously)
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator
from src.bot.question_engine import QuestionEngine


def minimal_index_with_queue():
    """
    Minimal indexing using message queue for quick testing.
    
    Strategy:
    - Generate search queries using QuestionEngine
    - Search for videos (you'll need to implement search)
    - Submit video URLs to message queue
    - Workers process asynchronously
    """
    
    print("\n" + "="*70)
    print("Minimal MVP Indexing (Message Queue)")
    print("="*70)
    print("\nThis will submit videos to the queue for async processing...")
    print("Make sure RabbitMQ and workers are running:")
    print("  docker-compose up -d\n")
    
    # Initialize components
    orchestrator = IndexingOrchestrator()
    question_engine = QuestionEngine()
    
    # Generate queries for Piano learning
    queries = question_engine.generate_queries(
        domain_id='MUSIC',
        subdomain_id='PIANO',
        skill_level='beginner',
        limit=5
    )
    
    print(f"\n📝 Generated {len(queries)} search queries")
    
    # TODO: You need a YouTube search function here
    # For now, here are some example piano beginner videos
    example_videos = [
        # Beginner piano videos
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw",  # Piano basics
        "https://www.youtube.com/watch?v=IcB8VkXr5nw",  # Piano for beginners
        "https://www.youtube.com/watch?v=L6K_nHKBgKk",  # Learn piano in 4 minutes
        
        # Intermediate piano
        "https://www.youtube.com/watch?v=AR4D47Wqhz0",  # Piano chords
        "https://www.youtube.com/watch?v=3EG3-C8zDvQ",  # Piano scales
        
        # Advanced piano
        "https://www.youtube.com/watch?v=67Ix5zexYZ0",  # Advanced techniques
    ]
    
    print(f"\n📤 Submitting {len(example_videos)} videos to queue...")
    
    submitted = 0
    for i, url in enumerate(example_videos, 1):
        # Extract metadata based on position
        if i <= 3:
            difficulty = 'beginner'
        elif i <= 5:
            difficulty = 'intermediate'
        else:
            difficulty = 'advanced'
        
        metadata = {
            'domain_id': 'MUSIC',
            'subdomain_id': 'PIANO',
            'difficulty': difficulty,
            'platform': 'youtube'
        }
        
        success = orchestrator.submit_video_for_indexing(url, metadata)
        if success:
            submitted += 1
            print(f"   ✅ {i}/{len(example_videos)}: {url[:50]}... ({difficulty})")
        else:
            print(f"   ❌ {i}/{len(example_videos)}: Failed")
    
    print(f"\n✅ Submitted {submitted}/{len(example_videos)} videos to queue")
    
    print("\n🎯 Next Steps:")
    print("   1. Monitor processing: docker-compose logs -f transcription_worker")
    print("   2. Check RabbitMQ UI: http://localhost:15672 (autodidact/rabbitmq_password)")
    print("   3. Wait for processing to complete (~5-10 min)")
    print("   4. Build graph: python scripts/build_knowledge_graph.py")
    print("   5. Test: python -m src.agents.question_agent_v2")
    print("="*70 + "\n")
    
    # Close connection
    orchestrator.close()


if __name__ == "__main__":
    minimal_index_with_queue()
