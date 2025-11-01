#!/usr/bin/env python3
"""
Helper script to manually queue an approved video for ingestion.
Use this after manually approving a video in the database.

Usage:
    python scripts/queue_approved_video.py <video_id>
"""
import sys
import os
import json
import pika
import psycopg2
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, '.env'))

from autodidact.database import database_utils


def get_video_data(video_id: str) -> dict:
    """Fetch video data from database."""
    conn = database_utils.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get video with channel info
            cur.execute("""
                SELECT 
                    v.video_id, 
                    v.video_url, 
                    v.title, 
                    v.quality_score,
                    c.channel_name,
                    c.channel_url
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE v.video_id = %s AND v.status = 'approved'
            """, (video_id,))
            
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Video {video_id} not found or not approved")
            
            return {
                'video_id': row[0],
                'video_url': row[1],
                'title': row[2],
                'quality_score': float(row[3]) if row[3] else None,
                'channel_name': row[4],
                'channel_url': row[5],
            }
    finally:
        conn.close()


def get_transcript(video_id: str) -> str:
    """
    Fetch transcript from the original source using Apify.
    Since transcripts are not stored in the database, we need to re-fetch.
    We use Apify explicitly to avoid IP blocking issues.
    """
    from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
    
    # Force use of Apify scraper to avoid IP blocking
    scraper = 'apify'
    
    # Construct URL from video_id
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"🔄 Re-fetching transcript using Apify for {video_id}...")
    content, metadata = get_youtube_transcript(url, scraper=scraper)
    
    if not content:
        raise ValueError(f"Could not fetch transcript for {video_id}")
    
    print(f"✅ Fetched transcript ({len(content)} chars)")
    
    return content, metadata


def queue_for_ingestion(video_id: str):
    """Queue an approved video for ingestion."""
    
    # Get video data from database
    print(f"📋 Fetching video data for {video_id}...")
    video_data = get_video_data(video_id)
    
    # Get transcript
    content, metadata = get_transcript(video_id)
    
    # Enrich metadata with required UnifiedMetadata fields
    # Note: Remove 'source_url' and use 'source' instead
    enriched_metadata = {
        'quality_score': video_data['quality_score'],
        # Required UnifiedMetadata fields
        'domain_id': 'UNCATEGORIZED',  # TODO: Add domain classification
        'subdomain_id': None,
        'source': video_data['video_url'],  # Use 'source' not 'source_url'
        'platform': 'youtube',
        'content_type': 'video',
        'difficulty': 'intermediate',  # TODO: Add difficulty classification
        'helpfulness_score': video_data['quality_score'] or 0.5,
        'text_length': len(content),
        # Optional fields from scraper
        'title': metadata.get('title'),
        'author': metadata.get('channel_name'),
        'channel_id': metadata.get('channel_id'),
        'channel_url': metadata.get('channel_url'),
        'video_id': metadata.get('video_id'),
        'views': metadata.get('views', 0),
        'video_length_seconds': metadata.get('video_length_seconds', 0),
        'language': metadata.get('language', 'en'),
    }
    
    # Prepare message for ingestion queue
    message = {
        'youtube_url': video_data['video_url'],
        'content': content,
        'metadata': enriched_metadata,
        'video_id': video_id,
    }
    
    # Connect to RabbitMQ
    print(f"🔌 Connecting to RabbitMQ...")
    credentials = pika.PlainCredentials('autodidact', 'rabbitmq_password')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost', credentials=credentials)
    )
    channel = connection.channel()
    
    # Publish to validation queue (which feeds into embedding)
    channel.basic_publish(
        exchange='',
        routing_key='tasks.video.validated',
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
        )
    )
    
    print(f"✅ Queued '{video_data['title']}' for ingestion")
    connection.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/queue_approved_video.py <video_id>")
        sys.exit(1)
    
    video_id = sys.argv[1]
    
    try:
        queue_for_ingestion(video_id)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
