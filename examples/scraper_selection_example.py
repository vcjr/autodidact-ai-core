#!/usr/bin/env python3
"""
Example: YouTube Scraper Selection
====================================

Demonstrates how to select different YouTube transcript scrapers
in the message queue architecture.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator


def example_default_scraper():
    """
    Example 1: Use default scraper (youtube-transcript-api)
    - Free
    - No API key required
    - May fail on geo-blocked videos
    """
    print("\n" + "="*70)
    print("Example 1: Default Scraper (youtube-transcript-api)")
    print("="*70)
    
    orchestrator = IndexingOrchestrator()
    
    # Submit without specifying scraper (uses default)
    orchestrator.submit_video_for_indexing(
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw"
    )
    
    # Or explicitly specify 'default'
    orchestrator.submit_video_for_indexing(
        "https://www.youtube.com/watch?v=example1",
        additional_metadata={'scraper': 'default'}
    )
    
    orchestrator.close()
    print("✅ Submitted videos using default scraper")


def example_apify_scraper():
    """
    Example 2: Use Apify scraper
    - Paid (but cost-effective)
    - Robust, handles geo-blocking
    - Requires APIFY_API_TOKEN
    """
    print("\n" + "="*70)
    print("Example 2: Apify Scraper (robust, production-ready)")
    print("="*70)
    
    if not os.getenv('APIFY_API_TOKEN'):
        print("⚠️  APIFY_API_TOKEN not set - skipping this example")
        print("   Set it with: export APIFY_API_TOKEN=your_token_here")
        return
    
    orchestrator = IndexingOrchestrator()
    
    # Submit with Apify scraper
    orchestrator.submit_video_for_indexing(
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw",
        additional_metadata={'scraper': 'apify'}
    )
    
    orchestrator.close()
    print("✅ Submitted video using Apify scraper")


def example_youtube_api_scraper():
    """
    Example 3: Use YouTube Data API v3 scraper
    - Free tier (10k requests/day)
    - Comprehensive metadata
    - Requires YOUTUBE_API_KEY
    """
    print("\n" + "="*70)
    print("Example 3: YouTube Data API v3 (comprehensive metadata)")
    print("="*70)
    
    if not os.getenv('YOUTUBE_API_KEY'):
        print("⚠️  YOUTUBE_API_KEY not set - skipping this example")
        print("   Set it with: export YOUTUBE_API_KEY=your_key_here")
        return
    
    orchestrator = IndexingOrchestrator()
    
    # Submit with YouTube API scraper
    orchestrator.submit_video_for_indexing(
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw",
        additional_metadata={'scraper': 'api'}
    )
    
    orchestrator.close()
    print("✅ Submitted video using YouTube Data API scraper")


def example_environment_variable():
    """
    Example 4: Use environment variable to set default scraper
    """
    print("\n" + "="*70)
    print("Example 4: Using YOUTUBE_SCRAPER Environment Variable")
    print("="*70)
    
    # Set environment variable
    os.environ['YOUTUBE_SCRAPER'] = 'apify'  # or 'default' or 'api'
    
    print(f"Set YOUTUBE_SCRAPER={os.environ['YOUTUBE_SCRAPER']}")
    print("All workers will now use this scraper by default")
    print()
    print("In production, set this in:")
    print("  - .env file")
    print("  - docker-compose.yml environment section")
    print("  - Kubernetes ConfigMap")
    

def example_batch_with_different_scrapers():
    """
    Example 5: Submit batch with different scrapers per video
    """
    print("\n" + "="*70)
    print("Example 5: Batch Submission with Different Scrapers")
    print("="*70)
    
    orchestrator = IndexingOrchestrator()
    
    # Manually publish messages with different scrapers
    videos = [
        {
            'url': 'https://www.youtube.com/watch?v=video1',
            'scraper': 'default'
        },
        {
            'url': 'https://www.youtube.com/watch?v=video2',
            'scraper': 'apify'  # Use robust scraper for important video
        },
        {
            'url': 'https://www.youtube.com/watch?v=video3',
            'scraper': 'api'  # Need comprehensive metadata
        },
    ]
    
    for video in videos:
        orchestrator.submit_video_for_indexing(
            video['url'],
            additional_metadata={'scraper': video['scraper']}
        )
        print(f"  Submitted {video['url']} with {video['scraper']} scraper")
    
    orchestrator.close()
    print("✅ Submitted batch with mixed scrapers")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("YouTube Scraper Selection Examples")
    print("="*70)
    print()
    print("This script demonstrates how to select different YouTube")
    print("transcript scrapers in the message queue architecture.")
    print()
    
    # Run examples
    example_default_scraper()
    example_apify_scraper()
    example_youtube_api_scraper()
    example_environment_variable()
    example_batch_with_different_scrapers()
    
    print("\n" + "="*70)
    print("Examples Complete!")
    print("="*70)
    print()
    print("💡 Monitor processing:")
    print("  - RabbitMQ UI: http://localhost:15672")
    print("  - Worker logs: docker-compose logs -f transcription_worker")
    print()
    print("📚 Scraper Comparison:")
    print("  default: Free, simple, may fail on geo-blocked videos")
    print("  apify:   Paid, robust, handles geo-blocking (recommended for production)")
    print("  api:     Free tier, comprehensive metadata, quota limits")
    print()


if __name__ == '__main__':
    main()
