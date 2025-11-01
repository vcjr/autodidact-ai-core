#!/usr/bin/env python3
"""
Backfill Video Metadata
========================

Re-fetch metadata for videos that have empty/missing fields and update both:
1. GCS storage (for future dashboard views)
2. PostgreSQL database (for queries and filtering)

This script:
- Finds videos with missing metadata (0 views, 0 likes, etc.)
- Re-fetches from Apify with full metadata
- Updates GCS storage
- Optionally updates database

Usage:
    python scripts/backfill_video_metadata.py [--dry-run] [--limit N]
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autodidact.database import database_utils
from src.storage.gcs_manager import retrieve_video_from_gcs, store_video_in_gcs, video_exists_in_gcs
from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript


def find_videos_needing_backfill():
    """Find videos with missing/empty metadata."""
    query = """
        SELECT 
            v.video_id,
            v.video_url,
            v.title,
            v.status
        FROM videos v
        WHERE v.status != 'rejected'
        ORDER BY v.retrieval_date DESC;
    """
    
    conn = database_utils.get_db_connection()
    cur = conn.cursor()
    cur.execute(query)
    
    videos = []
    for row in cur.fetchall():
        video_id, video_url, title, status = row
        
        # Check if video exists in GCS
        if video_exists_in_gcs(video_id):
            # Check if metadata is empty
            transcript, metadata = retrieve_video_from_gcs(video_id)
            if metadata:
                view_count = metadata.get('view_count', 0) or metadata.get('views', 0)
                like_count = metadata.get('like_count', 0)
                
                # If metadata is missing or empty, mark for backfill
                if view_count == 0 and like_count == 0:
                    videos.append({
                        'video_id': video_id,
                        'video_url': video_url,
                        'title': title,
                        'status': status,
                        'has_gcs': True,
                        'needs_update': True
                    })
            else:
                # Metadata is None - definitely needs backfill
                videos.append({
                    'video_id': video_id,
                    'video_url': video_url,
                    'title': title,
                    'status': status,
                    'has_gcs': True,
                    'needs_update': True
                })
        else:
            # Not in GCS at all - needs full fetch
            videos.append({
                'video_id': video_id,
                'video_url': video_url,
                'title': title,
                'status': status,
                'has_gcs': False,
                'needs_update': True
            })
    
    cur.close()
    conn.close()
    
    return videos


def backfill_video(video_info, dry_run=False):
    """Re-fetch and update metadata for a single video."""
    video_id = video_info['video_id']
    video_url = video_info['video_url']
    
    print(f"\n🔄 Processing: {video_info['title']}")
    print(f"   Video ID: {video_id}")
    print(f"   URL: {video_url}")
    
    if dry_run:
        print("   [DRY RUN] Would re-fetch metadata from Apify")
        return True
    
    try:
        # Re-fetch with Apify (gets full metadata)
        transcript, metadata = get_youtube_transcript(video_url, scraper='apify')
        
        if not transcript or not metadata:
            print(f"   ❌ Failed to fetch metadata")
            return False
        
        # Update GCS
        store_video_in_gcs(video_id, transcript, metadata)
        print(f"   ✅ Updated GCS storage")
        
        # Show what we got
        view_count = metadata.get('view_count', 0)
        like_count = metadata.get('like_count', 0)
        comment_count = metadata.get('comment_count', 0)
        subscriber_count = metadata.get('subscriber_count', 0)
        duration = metadata.get('duration', 'Unknown')
        
        print(f"   📊 New metadata:")
        print(f"      Views: {view_count:,}")
        print(f"      Likes: {like_count:,}")
        print(f"      Comments: {comment_count:,}")
        print(f"      Duration: {duration}")
        if subscriber_count:
            print(f"      Channel subscribers: {subscriber_count:,}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Backfill missing video metadata')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
    parser.add_argument('--limit', type=int, help='Limit number of videos to process')
    args = parser.parse_args()
    
    print("🔍 Finding videos with missing metadata...")
    videos = find_videos_needing_backfill()
    
    if not videos:
        print("✅ All videos have complete metadata!")
        return
    
    print(f"\n📋 Found {len(videos)} videos needing metadata:")
    for i, v in enumerate(videos[:10], 1):
        gcs_status = "✅ In GCS" if v['has_gcs'] else "❌ Not in GCS"
        print(f"   {i}. {v['title'][:60]} ({gcs_status})")
    
    if len(videos) > 10:
        print(f"   ... and {len(videos) - 10} more")
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would process {len(videos)} videos")
        return
    
    # Apply limit if specified
    videos_to_process = videos[:args.limit] if args.limit else videos
    
    print(f"\n🚀 Processing {len(videos_to_process)} videos...")
    confirm = input(f"Continue? This will cost ~${len(videos_to_process) * 0.00025:.4f} in Apify credits (y/N): ")
    
    if confirm.lower() != 'y':
        print("Cancelled.")
        return
    
    success_count = 0
    fail_count = 0
    
    for i, video in enumerate(videos_to_process, 1):
        print(f"\n[{i}/{len(videos_to_process)}]")
        if backfill_video(video, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully updated: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total processed: {success_count + fail_count}")
    print(f"\n💡 Tip: Restart the admin dashboard to see updated metadata!")


if __name__ == '__main__':
    main()
