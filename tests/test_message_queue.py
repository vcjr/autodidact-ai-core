#!/usr/bin/env python3
"""
Test script for the new message queue architecture.
This script submits test videos and monitors their progress through the pipeline.
"""
import sys
import os
import time

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator
from src.workers.rabbitmq_utils import get_rabbitmq_connection


def get_queue_stats():
    """Get statistics for all queues."""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        queues = [
            'tasks.video.new',
            'tasks.video.transcribed',
            'tasks.video.validated',
            'tasks.video.ingested',
        ]
        
        stats = {}
        for queue_name in queues:
            try:
                queue = channel.queue_declare(queue=queue_name, passive=True)
                stats[queue_name] = queue.method.message_count
            except Exception as e:
                stats[queue_name] = f"Error: {e}"
        
        connection.close()
        return stats
    except Exception as e:
        return {"error": str(e)}


def display_queue_stats(stats):
    """Display queue statistics in a formatted way."""
    print("\n" + "="*60)
    print("📊 QUEUE STATISTICS")
    print("="*60)
    for queue_name, count in stats.items():
        print(f"  {queue_name}: {count} messages")
    print("="*60 + "\n")


def test_single_video():
    """Test submitting a single video."""
    print("\n" + "="*60)
    print("TEST 1: Single Video Submission")
    print("="*60 + "\n")
    
    orchestrator = IndexingOrchestrator()
    
    test_url = "https://www.youtube.com/watch?v=vpn4qv4A1Aw"
    print(f"Submitting: {test_url}")
    
    success = orchestrator.submit_video_for_indexing(test_url)
    
    if success:
        print("✅ Video submitted successfully")
    else:
        print("❌ Failed to submit video")
    
    orchestrator.close()
    
    # Show queue stats
    time.sleep(1)
    stats = get_queue_stats()
    display_queue_stats(stats)


def test_batch_submission():
    """Test submitting multiple videos."""
    print("\n" + "="*60)
    print("TEST 2: Batch Submission")
    print("="*60 + "\n")
    
    test_urls = [
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw",
        "https://www.youtube.com/watch?v=afRiqumTOPA",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Example
    ]
    
    orchestrator = IndexingOrchestrator()
    
    print(f"Submitting batch of {len(test_urls)} videos...")
    results = orchestrator.submit_batch(test_urls)
    
    print(f"\n📈 Batch Results:")
    print(f"   Total: {results['total']}")
    print(f"   Successful: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    
    orchestrator.close()
    
    # Show queue stats
    time.sleep(1)
    stats = get_queue_stats()
    display_queue_stats(stats)


def monitor_queue_processing():
    """Monitor queue processing for a period of time."""
    print("\n" + "="*60)
    print("TEST 3: Queue Processing Monitor")
    print("="*60 + "\n")
    
    print("Monitoring queues for 30 seconds...")
    print("(Make sure workers are running: docker-compose up -d)\n")
    
    for i in range(6):
        stats = get_queue_stats()
        print(f"[{i*5}s] Queue depths:")
        for queue_name, count in stats.items():
            print(f"  {queue_name}: {count}")
        print()
        
        if i < 5:
            time.sleep(5)
    
    print("✅ Monitoring complete")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" "*15 + "MESSAGE QUEUE ARCHITECTURE TEST SUITE")
    print("="*70)
    
    print("\nThis test suite will:")
    print("  1. Submit a single video to the queue")
    print("  2. Submit a batch of videos to the queue")
    print("  3. Monitor queue processing over time")
    print("\n⚠️  Make sure RabbitMQ and workers are running:")
    print("    docker-compose up -d")
    print()
    
    input("Press Enter to continue...")
    
    try:
        # Test 1: Single video
        test_single_video()
        time.sleep(2)
        
        # Test 2: Batch submission
        test_batch_submission()
        time.sleep(2)
        
        # Test 3: Monitor processing
        monitor_queue_processing()
        
        print("\n" + "="*70)
        print(" "*20 + "ALL TESTS COMPLETE")
        print("="*70)
        print("\n💡 Next steps:")
        print("  - Check worker logs: docker-compose logs -f transcription_worker")
        print("  - View RabbitMQ UI: http://localhost:15672")
        print("  - Check database: SELECT * FROM videos ORDER BY created_at DESC;")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
