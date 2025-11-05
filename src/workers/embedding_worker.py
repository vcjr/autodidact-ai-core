#!/usr/bin/env python3
"""
Embedding Worker
Consumes validated videos from 'tasks.video.validated' queue,
generates embeddings and stores them in ChromaDB,
and publishes completion status to 'tasks.video.ingested' queue.
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
    QUEUE_VIDEO_VALIDATED,
    QUEUE_VIDEO_INGESTED,
)
from src.agents.intake_agent import IntakeAgent
from autodidact.database import database_utils


def process_embedding(message_data: dict) -> dict:
    """
    Process video embedding and ingestion into vector store.
    
    Args:
        message_data: Dictionary containing 'content', 'metadata', and 'youtube_url'
        
    Returns:
        Dictionary with ingestion results
    """
    youtube_url = message_data.get('youtube_url')
    content = message_data.get('content')
    metadata = message_data.get('metadata')
    video_id = message_data.get('video_id')
    
    print(f"🧮 Embedding and ingesting video: {metadata.get('title')}")
    
    # Ingest into ChromaDB
    ingestor = IntakeAgent()
    first_chunk_id = ingestor.process_and_add_document(
        content=content,
        source_url=youtube_url,
        metadata=metadata
    )
    
    if not first_chunk_id:
        database_utils.update_video_status(
            video_id, 
            'error_ingestion', 
            reason="IntakeAgent failed to ingest document"
        )
        raise ValueError("IntakeAgent failed to ingest document")
    
    # Update status
    database_utils.update_video_status(video_id, 'ingested')
    
    print(f"✅ Document ingested successfully. First chunk ID: {first_chunk_id}")
    
    return {
        'youtube_url': youtube_url,
        'video_id': video_id,
        'first_chunk_id': first_chunk_id,
        'status': 'ingested',
        'metadata': metadata,
    }


def callback(ch, method, properties, body):
    """
    Callback function for processing messages from the queue.
    """
    try:
        print(f"\n{'='*60}")
        print("📥 Received embedding task")
        
        # Parse message
        message_data = json.loads(body)
        
        # Process embedding
        result = process_embedding(message_data)
        
        # Publish to completion queue
        ch.basic_publish(
            exchange='',
            routing_key=QUEUE_VIDEO_INGESTED,
            body=json.dumps(result),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
            )
        )
        
        print(f"✅ Embedding complete, published to '{QUEUE_VIDEO_INGESTED}'")
        print(f"{'='*60}\n")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error processing embedding: {e}")
        # Reject and requeue the message for retry
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """
    Main worker loop.
    """
    print("🚀 Starting Embedding Worker...")
    
    # Connect to RabbitMQ
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare queues
    declare_queue(channel, QUEUE_VIDEO_VALIDATED)
    declare_queue(channel, QUEUE_VIDEO_INGESTED)
    
    # Configure QoS - process one message at a time
    channel.basic_qos(prefetch_count=1)
    
    # Start consuming
    print(f"👂 Listening on queue: {QUEUE_VIDEO_VALIDATED}")
    channel.basic_consume(
        queue=QUEUE_VIDEO_VALIDATED,
        on_message_callback=callback,
    )
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping Embedding Worker...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
