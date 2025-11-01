#!/usr/bin/env python3
"""
Transcription Worker
Consumes video URLs from the 'tasks.video.new' queue, scrapes transcripts,
and publishes results to the 'tasks.video.transcribed' queue.
"""
import sys
import os
import json
import pika

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.workers.rabbitmq_utils import (
    get_rabbitmq_connection,
    declare_queue,
    QUEUE_VIDEO_NEW,
    QUEUE_VIDEO_TRANSCRIBED,
)
from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
from autodidact.database import database_utils


def process_transcription(message_data: dict) -> dict:
    """
    Process a video transcription task.
    
    Args:
        message_data: Dictionary containing 'youtube_url' and optional 'scraper' selection
        
    Returns:
        Dictionary with transcription results
    """
    youtube_url = message_data.get('youtube_url')
    scraper = message_data.get('scraper')  # Optional: 'default', 'apify', or 'api'
    
    print(f"🎬 Transcribing video: {youtube_url}")
    if scraper:
        print(f"   Using scraper: {scraper}")
    
    # Get transcript and metadata using the unified fetcher
    content, metadata = get_youtube_transcript(youtube_url, scraper=scraper)
    
    if not content or not metadata:
        raise ValueError(f"Failed to scrape content or metadata for {youtube_url}")
    
    # Log to database
    try:
        database_utils.log_channel_and_video(metadata)
        print(f"✅ Logged video '{metadata.get('title')}' to database")
    except Exception as e:
        print(f"❌ Failed to log video to database: {e}")
        raise
    
    return {
        'youtube_url': youtube_url,
        'content': content,
        'metadata': metadata,
        'video_id': metadata.get('video_id'),
    }


def callback(ch, method, properties, body):
    """
    Callback function for processing messages from the queue.
    """
    try:
        print(f"\n{'='*60}")
        print("📥 Received new transcription task")
        
        # Parse message
        message_data = json.loads(body)
        
        # Get retry count from message headers
        headers = properties.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        max_retries = 3
        
        # Process transcription
        result = process_transcription(message_data)
        
        # Publish to next queue
        ch.basic_publish(
            exchange='',
            routing_key=QUEUE_VIDEO_TRANSCRIBED,
            body=json.dumps(result),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
            )
        )
        
        print(f"✅ Transcription complete, published to '{QUEUE_VIDEO_TRANSCRIBED}'")
        print(f"{'='*60}\n")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except ValueError as e:
        # ValueError indicates no transcript available - don't retry
        print(f"⚠️  Skipping video (no transcript): {e}")
        print(f"{'='*60}\n")
        # Acknowledge and discard the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error processing transcription: {e}")
        
        # Check retry count
        headers = properties.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        max_retries = 3
        
        if retry_count < max_retries:
            # Increment retry count and requeue
            print(f"🔄 Retrying... (attempt {retry_count + 1}/{max_retries})")
            headers['x-retry-count'] = retry_count + 1
            
            ch.basic_publish(
                exchange='',
                routing_key=QUEUE_VIDEO_NEW,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    headers=headers,
                )
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            # Max retries exceeded, acknowledge and discard
            print(f"❌ Max retries exceeded ({max_retries}), discarding message")
            print(f"{'='*60}\n")
            ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    """
    Main worker loop.
    """
    print("🚀 Starting Transcription Worker...")
    
    # Connect to RabbitMQ
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare queues
    declare_queue(channel, QUEUE_VIDEO_NEW)
    declare_queue(channel, QUEUE_VIDEO_TRANSCRIBED)
    
    # Configure QoS - process one message at a time
    channel.basic_qos(prefetch_count=1)
    
    # Start consuming
    print(f"👂 Listening on queue: {QUEUE_VIDEO_NEW}")
    channel.basic_consume(
        queue=QUEUE_VIDEO_NEW,
        on_message_callback=callback,
    )
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping Transcription Worker...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
