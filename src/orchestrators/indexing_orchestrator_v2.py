"""
Indexing Orchestrator - Message Producer
Refactored to publish tasks to RabbitMQ instead of directly executing the pipeline.
This allows for asynchronous, scalable processing by independent worker services.
"""
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.workers.rabbitmq_utils import (
    get_rabbitmq_connection,
    setup_all_queues,
    QUEUE_VIDEO_NEW,
)
import pika


class IndexingOrchestrator:
    """
    The orchestrator is now a producer that publishes video URLs to the message queue.
    Worker services consume from the queue and process each stage asynchronously.
    """
    
    def __init__(self):
        """Initialize the orchestrator with RabbitMQ connection."""
        self.connection = None
        self.channel = None
        self._connect()
    
    def _connect(self):
        """Establish connection to RabbitMQ and set up queues."""
        try:
            self.connection = get_rabbitmq_connection()
            self.channel = self.connection.channel()
            setup_all_queues(self.channel)
            print("✅ Orchestrator connected to RabbitMQ")
        except Exception as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    def submit_video_for_indexing(self, youtube_url: str, additional_metadata: dict = None) -> bool:
        """
        Submit a video URL for asynchronous indexing.
        
        Args:
            youtube_url: The YouTube URL to process
            additional_metadata: Optional metadata to include with the task
            
        Returns:
            bool: True if successfully published to queue, False otherwise
        """
        try:
            # Prepare message
            message = {
                'youtube_url': youtube_url,
                'additional_metadata': additional_metadata or {},
            }
            
            # Publish to queue
            self.channel.basic_publish(
                exchange='',
                routing_key=QUEUE_VIDEO_NEW,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                )
            )
            
            print(f"✅ Submitted video for indexing: {youtube_url}")
            print(f"   Message published to queue: {QUEUE_VIDEO_NEW}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to submit video: {e}")
            return False
    
    def submit_batch(self, youtube_urls: list) -> dict:
        """
        Submit multiple videos for indexing.
        
        Args:
            youtube_urls: List of YouTube URLs to process
            
        Returns:
            dict: Summary of submission results
        """
        results = {
            'total': len(youtube_urls),
            'successful': 0,
            'failed': 0,
        }
        
        print(f"\n{'='*60}")
        print(f"📤 Submitting batch of {len(youtube_urls)} videos")
        print(f"{'='*60}\n")
        
        for url in youtube_urls:
            if self.submit_video_for_indexing(url):
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        print(f"\n{'='*60}")
        print(f"📊 Batch Submission Summary:")
        print(f"   Total: {results['total']}")
        print(f"   Successful: {results['successful']}")
        print(f"   Failed: {results['failed']}")
        print(f"{'='*60}\n")
        
        return results
    
    def close(self):
        """Close the RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            print("🔌 Orchestrator disconnected from RabbitMQ")


def submit_video(youtube_url: str) -> bool:
    """
    Convenience function to submit a single video for indexing.
    
    Args:
        youtube_url: The YouTube URL to process
        
    Returns:
        bool: True if successfully submitted, False otherwise
    """
    orchestrator = IndexingOrchestrator()
    try:
        return orchestrator.submit_video_for_indexing(youtube_url)
    finally:
        orchestrator.close()


def submit_batch(youtube_urls: list) -> dict:
    """
    Convenience function to submit multiple videos for indexing.
    
    Args:
        youtube_urls: List of YouTube URLs to process
        
    Returns:
        dict: Summary of submission results
    """
    orchestrator = IndexingOrchestrator()
    try:
        return orchestrator.submit_batch(youtube_urls)
    finally:
        orchestrator.close()


# --- TESTING ---
if __name__ == "__main__":
    print("="*60)
    print("TESTING INDEXING ORCHESTRATOR (PRODUCER MODE)")
    print("="*60)
    
    # Test URLs
    test_urls = [
        "https://www.youtube.com/watch?v=vpn4qv4A1Aw",  # Should pass validation
        "https://www.youtube.com/watch?v=afRiqumTOPA",  # Might be pending review
    ]
    
    # Submit batch
    results = submit_batch(test_urls)
    
    print("\n✅ Test complete!")
    print("⏳ Videos are now being processed asynchronously by worker services.")
    print("💡 Check worker logs to see progress through the pipeline.")
