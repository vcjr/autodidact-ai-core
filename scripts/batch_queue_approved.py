#!/usr/bin/env python3
"""
Batch Queue Approved Videos
============================

Queue all approved videos that haven't been ingested yet.
Useful after manually approving videos in bulk.

Usage:
    python scripts/batch_queue_approved.py [--limit N] [--dry-run]
    
Examples:
    # Queue all approved videos
    python scripts/batch_queue_approved.py
    
    # Queue only 10 videos (for testing)
    python scripts/batch_queue_approved.py --limit 10
    
    # See what would be queued without actually queueing
    python scripts/batch_queue_approved.py --dry-run
"""
import sys
import os
import json
import argparse
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


def get_approved_videos_not_in_chromadb(limit=None):
    """
    Find videos that are approved but not yet in ChromaDB.
    
    Returns list of video dicts with metadata.
    """
    conn = database_utils.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get approved videos
            # TODO: Cross-reference with ChromaDB to find which ones aren't ingested
            # For now, we'll assume all 'approved' status videos need queueing
            query = """
                SELECT 
                    v.video_id, 
                    v.video_url, 
                    v.title, 
                    v.quality_score,
                    c.channel_name,
                    c.channel_url
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE v.status = 'approved'
                ORDER BY v.retrieval_date DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            
            videos = []
            for row in cur.fetchall():
                videos.append({
                    'video_id': row[0],
                    'video_url': row[1],
                    'title': row[2],
                    'quality_score': float(row[3]) if row[3] else None,
                    'channel_name': row[4],
                    'channel_url': row[5],
                })
            
            return videos
    finally:
        conn.close()


def get_transcript(video_url: str):
    """
    Fetch transcript using Apify.
    
    Returns (content, metadata) tuple.
    """
    from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
    
    content, metadata = get_youtube_transcript(video_url, scraper='apify')
    
    if not content:
        raise ValueError(f"Could not fetch transcript for {video_url}")
    
    return content, metadata


def queue_video(video_data: dict, channel, dry_run=False):
    """
    Queue a single video for ingestion.
    
    Args:
        video_data: Video metadata dict
        channel: RabbitMQ channel (or None if dry_run)
        dry_run: If True, don't actually queue
    """
    video_id = video_data['video_id']
    title = video_data['title'][:60]
    
    if dry_run:
        print(f"   [DRY RUN] Would queue: {title}... ({video_id})")
        return True
    
    try:
        # Get transcript
        print(f"   📥 Fetching transcript for: {title}...")
        content, metadata = get_transcript(video_data['video_url'])
        print(f"      ✅ Got {len(content)} chars")
        
        # Enrich metadata
        enriched_metadata = {
            'quality_score': video_data['quality_score'],
            'domain_id': 'UNCATEGORIZED',
            'subdomain_id': None,
            'source': video_data['video_url'],
            'platform': 'youtube',
            'content_type': 'video',
            'difficulty': 'intermediate',
            'helpfulness_score': video_data['quality_score'] or 0.5,
            'text_length': len(content),
            'title': metadata.get('title'),
            'author': metadata.get('channel_name'),
            'channel_id': metadata.get('channel_id'),
            'channel_url': metadata.get('channel_url'),
            'video_id': metadata.get('video_id'),
            'views': metadata.get('views', 0),
            'video_length_seconds': metadata.get('video_length_seconds', 0),
            'language': metadata.get('language', 'en'),
        }
        
        # Prepare message
        message = {
            'youtube_url': video_data['video_url'],
            'content': content,
            'metadata': enriched_metadata,
            'video_id': video_id,
        }
        
        # Publish to queue
        channel.basic_publish(
            exchange='',
            routing_key='tasks.video.validated',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json',
            )
        )
        
        print(f"   ✅ Queued: {title}...")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {title}... - {e}")
        return False


def main(limit=None, dry_run=False):
    """
    Main function to batch queue approved videos.
    """
    print("=" * 80)
    print("📋 BATCH QUEUE APPROVED VIDEOS")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No videos will actually be queued")
    
    # Get approved videos
    print(f"🔎 Finding approved videos...")
    videos = get_approved_videos_not_in_chromadb(limit=limit)
    
    if not videos:
        print("✅ No approved videos found waiting to be queued!")
        return
    
    print(f"📊 Found {len(videos)} approved videos")
    print()
    
    # Connect to RabbitMQ (unless dry run)
    connection = None
    channel = None
    
    if not dry_run:
        print("🔌 Connecting to RabbitMQ...")
        credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_USER', 'autodidact'),
            os.getenv('RABBITMQ_PASSWORD', 'rabbitmq_password')
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                os.getenv('RABBITMQ_HOST', 'localhost'),
                credentials=credentials
            )
        )
        channel = connection.channel()
        print("   ✅ Connected")
        print()
    
    # Process videos
    print(f"🚀 Processing {len(videos)} videos...")
    print()
    
    success_count = 0
    fail_count = 0
    
    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video['title'][:60]}...")
        
        if queue_video(video, channel, dry_run=dry_run):
            success_count += 1
        else:
            fail_count += 1
        
        print()
    
    # Close connection
    if connection:
        connection.close()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total videos: {len(videos)}")
    print(f"✅ Successfully queued: {success_count}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}")
    print()
    
    if dry_run:
        print("🔍 This was a dry run. Run without --dry-run to actually queue videos.")
    else:
        print("✅ Videos queued for ingestion!")
        print("📡 Workers will process them in the background.")
    print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Batch queue approved videos for ingestion")
    parser.add_argument('--limit', type=int, help="Limit number of videos to process")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without doing it")
    
    args = parser.parse_args()
    
    main(limit=args.limit, dry_run=args.dry_run)
