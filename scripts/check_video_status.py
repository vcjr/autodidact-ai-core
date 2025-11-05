#!/usr/bin/env python3
"""
Video Status Checker
====================

Check the status of videos in the pipeline.

Usage:
    python scripts/check_video_status.py
"""
import sys
import os
from dotenv import load_dotenv
import pika

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

load_dotenv()

from autodidact.database import database_utils


def get_video_stats():
    """Get video counts by status."""
    conn = database_utils.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, COUNT(*) 
                FROM videos 
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """)
            
            stats = {}
            for row in cur.fetchall():
                stats[row[0]] = row[1]
            
            return stats
    finally:
        conn.close()


def get_quality_score_stats():
    """Get quality score distribution."""
    conn = database_utils.get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get score ranges
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN quality_score IS NULL THEN 'No score'
                        WHEN quality_score < 0.3 THEN '0.0-0.3 (Very Low)'
                        WHEN quality_score < 0.5 THEN '0.3-0.5 (Low)'
                        WHEN quality_score < 0.7 THEN '0.5-0.7 (Medium)'
                        WHEN quality_score < 0.8 THEN '0.7-0.8 (Good)'
                        ELSE '0.8-1.0 (Excellent)'
                    END as score_range,
                    COUNT(*) as count,
                    AVG(quality_score) as avg_score
                FROM videos
                GROUP BY score_range
                ORDER BY avg_score NULLS FIRST
            """)
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'range': row[0],
                    'count': row[1],
                    'avg': row[2]
                })
            
            return results
    finally:
        conn.close()


def get_queue_stats():
    """Get RabbitMQ queue message counts."""
    try:
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
        
        queues = {}
        queue_names = [
            'tasks.video.transcription',
            'tasks.video.quality_assessment',
            'tasks.video.validated',
        ]
        
        for queue_name in queue_names:
            try:
                result = channel.queue_declare(queue=queue_name, passive=True)
                queues[queue_name] = result.method.message_count
            except:
                queues[queue_name] = 'N/A'
        
        connection.close()
        return queues
        
    except Exception as e:
        return {'error': str(e)}


def get_chromadb_stats():
    """Get ChromaDB collection stats."""
    try:
        from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection
        
        client = get_chroma_client()
        collection = get_or_create_collection(client, "autodidact_ai_core_v2")
        
        return {
            'total_documents': collection.count()
        }
    except Exception as e:
        return {'error': str(e)}


def main():
    print("=" * 80)
    print("📊 VIDEO PIPELINE STATUS")
    print("=" * 80)
    print()
    
    # Database stats
    print("🗄️  DATABASE (PostgreSQL)")
    print("-" * 80)
    video_stats = get_video_stats()
    
    total_videos = sum(video_stats.values())
    print(f"Total videos: {total_videos}")
    print()
    
    for status, count in sorted(video_stats.items()):
        percentage = (count / total_videos * 100) if total_videos > 0 else 0
        
        # Add emoji based on status
        emoji = {
            'approved': '✅',
            'pending_review': '⏳',
            'rejected': '❌',
            'transcription_pending': '📝',
            'quality_pending': '🎯',
            'ingested': '💾',
        }.get(status, '📋')
        
        print(f"{emoji} {status:20s}: {count:5d} ({percentage:5.1f}%)")
    
    print()
    
    # Quality score distribution
    print("📊 QUALITY SCORE DISTRIBUTION")
    print("-" * 80)
    quality_stats = get_quality_score_stats()
    
    for stat in quality_stats:
        count = stat['count']
        avg = stat['avg']
        avg_str = f"(avg: {avg:.3f})" if avg else ""
        
        # Add emoji
        emoji = {
            'No score': '⚫',
            '0.0-0.3 (Very Low)': '🔴',
            '0.3-0.5 (Low)': '🟠',
            '0.5-0.7 (Medium)': '🟡',
            '0.7-0.8 (Good)': '🟢',
            '0.8-1.0 (Excellent)': '🌟',
        }.get(stat['range'], '📊')
        
        print(f"{emoji} {stat['range']:25s}: {count:5d} {avg_str}")
    
    print()
    
    # Queue stats
    print("📨 RABBITMQ QUEUES")
    print("-" * 80)
    queue_stats = get_queue_stats()
    
    if 'error' in queue_stats:
        print(f"❌ Error connecting to RabbitMQ: {queue_stats['error']}")
        print("   Make sure RabbitMQ is running: docker-compose up -d")
    else:
        for queue_name, count in queue_stats.items():
            queue_short = queue_name.replace('tasks.video.', '')
            print(f"📬 {queue_short:20s}: {count} messages pending")
    
    print()
    
    # ChromaDB stats
    print("🗃️  CHROMADB")
    print("-" * 80)
    chroma_stats = get_chromadb_stats()
    
    if 'error' in chroma_stats:
        print(f"❌ Error connecting to ChromaDB: {chroma_stats['error']}")
        print("   Make sure ChromaDB is running: docker-compose up -d")
    else:
        print(f"📚 Total indexed documents: {chroma_stats['total_documents']}")
    
    print()
    print("=" * 80)
    
    # Recommendations
    print()
    print("💡 QUICK ACTIONS")
    print("-" * 80)
    
    if video_stats.get('pending_review', 0) > 0:
        print(f"⏳ You have {video_stats['pending_review']} videos waiting for review")
        print(f"   → Open admin dashboard: streamlit run autodidact/ui/admin_dashboard.py")
        print()
    
    if video_stats.get('approved', 0) > 0:
        print(f"✅ You have {video_stats['approved']} approved videos")
        print(f"   → Queue them: python scripts/batch_queue_approved.py")
        print()
    
    validated_in_queue = queue_stats.get('tasks.video.validated', 0)
    if validated_in_queue and validated_in_queue != 'N/A' and validated_in_queue > 0:
        print(f"📬 {validated_in_queue} videos waiting to be embedded")
        print(f"   → Check workers: docker-compose logs -f embedding_worker")
        print()
    
    if queue_stats.get('error'):
        print("❌ RabbitMQ not accessible")
        print("   → Start services: docker-compose up -d")
        print()
    
    print("=" * 80)


if __name__ == '__main__':
    main()
