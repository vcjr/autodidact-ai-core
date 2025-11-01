#!/usr/bin/env python3
"""
Quality Assessment Worker
Consumes transcribed videos from 'tasks.video.transcribed' queue,
validates and scores them using the QualityScorer,
and publishes approved videos to 'tasks.video.validated' queue.
"""
import sys
import os
import json
import pika
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.workers.rabbitmq_utils import (
    get_rabbitmq_connection,
    declare_queue,
    QUEUE_VIDEO_TRANSCRIBED,
    QUEUE_VIDEO_VALIDATED,
)
from src.bot.quality_scorer import QualityScorer, ContentMetrics
from autodidact.database import database_utils


def process_validation(message_data: dict) -> dict:
    """
    Process video quality validation.
    
    Args:
        message_data: Dictionary containing 'content' and 'metadata'
        
    Returns:
        Dictionary with validation results or None if rejected
    """
    content = message_data.get('content')
    metadata = message_data.get('metadata')
    video_id = message_data.get('video_id')
    
    print(f"🔍 Validating video: {metadata.get('title')}")
    
    # Parse published date
    published_at = None
    if metadata.get('upload_date'):
        try:
            published_at = datetime.fromisoformat(metadata['upload_date'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    # Build a meaningful query from metadata for relevance scoring
    # This allows the scorer to check if the content matches its own domain/topic
    query_parts = []
    if metadata.get('domain_id'):
        query_parts.append(metadata['domain_id'].replace('_', ' ').lower())
    if metadata.get('subdomain_id'):
        query_parts.append(metadata['subdomain_id'].replace('_', ' ').lower())
    if metadata.get('skill_level'):
        query_parts.append(metadata['skill_level'])
    
    # Fallback: use title keywords if no domain metadata
    query = ' '.join(query_parts) if query_parts else metadata.get('title', '')
    
    # Ensure counts are integers (handle None or string values)
    subscriber_count = int(metadata.get('subscriber_count', 0) or 0)
    view_count = int(metadata.get('view_count', 0) or 0)
    like_count = int(metadata.get('like_count', 0) or 0)
    comment_count = int(metadata.get('comment_count', 0) or 0)
    duration_seconds = int(metadata.get('duration_seconds', 0) or 0)
    
    # Create ContentMetrics from metadata
    metrics = ContentMetrics(
        title=metadata.get('title', ''),
        description=metadata.get('description', ''),
        transcript=content or '',
        query=query,  # Use constructed query for better relevance scoring
        tags=metadata.get('tags', []),
        channel_name=metadata.get('channel_name', ''),
        subscriber_count=subscriber_count,
        is_verified=metadata.get('is_verified', False),
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
        published_at=published_at,
        duration_seconds=duration_seconds,
        has_captions=bool(content),
    )
    
    # Debug: Log what we're scoring with
    print(f"   Query for relevance: '{query}'")
    print(f"   Subscriber count: {subscriber_count:,}")
    print(f"   View count: {view_count:,}")
    print(f"   Has transcript: {bool(content)} ({len(content) if content else 0} chars)")
    
    # Score the content
    scorer = QualityScorer()
    score_result = scorer.score_content(metrics)
    
    if not score_result:
        database_utils.update_video_status(
            video_id, 
            'error_validation', 
            reason="Quality scorer failed to produce score"
        )
        raise ValueError("Quality scorer failed to produce score")
    
    # Get overall quality score
    quality_score = score_result.overall
    
    print(f"📊 Quality breakdown:\n{score_result}")
    
    # Check if score meets threshold
    if quality_score < 0.8:
        rejection_reason = f"Quality score {quality_score:.2f} is below threshold (0.8)"
        print(f"⚠️  Video rejected: {rejection_reason}")
        database_utils.update_video_status(
            video_id, 
            'pending_review', 
            score=quality_score, 
            reason=rejection_reason
        )
        # Don't pass to next stage, but acknowledge the message
        return None
    
    print(f"✅ Video approved with score: {quality_score:.2f}")
    database_utils.update_video_status(
        video_id, 
        'approved', 
        score=quality_score, 
        reason="Passed quality threshold"
    )
    
    # Add score breakdown to metadata
    final_metadata = {
        **metadata,
        'quality_score': quality_score,
        'quality_breakdown': score_result.to_dict(),
    }
    
    return {
        'youtube_url': message_data.get('youtube_url'),
        'content': content,
        'metadata': final_metadata,
        'video_id': video_id,
    }


def callback(ch, method, properties, body):
    """
    Callback function for processing messages from the queue.
    """
    try:
        print(f"\n{'='*60}")
        print("📥 Received validation task")
        
        # Parse message
        message_data = json.loads(body)
        
        # Process validation
        result = process_validation(message_data)
        
        # Only publish to next queue if validation passed
        if result:
            ch.basic_publish(
                exchange='',
                routing_key=QUEUE_VIDEO_VALIDATED,
                body=json.dumps(result),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                )
            )
            print(f"✅ Validation complete, published to '{QUEUE_VIDEO_VALIDATED}'")
        else:
            print(f"⏭️  Video sent to review queue, not forwarding to ingestion")
        
        print(f"{'='*60}\n")
        
        # Always acknowledge the message (whether passed or failed)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error processing validation: {e}")
        # Reject and requeue the message for retry
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """
    Main worker loop.
    """
    print("🚀 Starting Quality Assessment Worker...")
    
    # Connect to RabbitMQ
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare queues
    declare_queue(channel, QUEUE_VIDEO_TRANSCRIBED)
    declare_queue(channel, QUEUE_VIDEO_VALIDATED)
    
    # Configure QoS - process one message at a time
    channel.basic_qos(prefetch_count=1)
    
    # Start consuming
    print(f"👂 Listening on queue: {QUEUE_VIDEO_TRANSCRIBED}")
    channel.basic_consume(
        queue=QUEUE_VIDEO_TRANSCRIBED,
        on_message_callback=callback,
    )
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping Quality Assessment Worker...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == '__main__':
    main()
