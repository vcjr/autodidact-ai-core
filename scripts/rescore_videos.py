#!/usr/bin/env python3
"""
Re-score Videos
===============

Re-calculate quality scores for videos that were scored with the broken scorer.

This will:
1. Find videos with suspiciously low scores (< 0.3)
2. Fetch their full metadata from the database
3. Re-calculate scores with proper query and metadata
4. Update the database with corrected scores

Usage:
    python scripts/rescore_videos.py [--dry-run] [--all]
"""
import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

load_dotenv()

from autodidact.database import database_utils
from src.bot.quality_scorer import QualityScorer, ContentMetrics


def get_videos_to_rescore(all_videos=False):
    """Get videos that need re-scoring."""
    conn = database_utils.get_db_connection()
    try:
        with conn.cursor() as cur:
            if all_videos:
                # Re-score all videos
                query = """
                    SELECT video_id, video_url, title, quality_score
                    FROM videos
                    WHERE quality_score IS NOT NULL
                    ORDER BY quality_score ASC
                """
            else:
                # Only re-score suspiciously low scores
                query = """
                    SELECT video_id, video_url, title, quality_score
                    FROM videos
                    WHERE quality_score < 0.3 AND quality_score IS NOT NULL
                    ORDER BY quality_score ASC
                """
            
            cur.execute(query)
            
            videos = []
            for row in cur.fetchall():
                videos.append({
                    'video_id': row[0],
                    'video_url': row[1],
                    'title': row[2],
                    'old_score': float(row[3]) if row[3] else None,
                })
            
            return videos
    finally:
        conn.close()


def fetch_video_metadata(video_id, video_url):
    """Fetch metadata from GCS (fast) or YouTube API (slow)."""
    from src.storage.gcs_manager import retrieve_video_from_gcs, video_exists_in_gcs
    
    # Try GCS first (instant, free)
    if video_exists_in_gcs(video_id):
        try:
            content, metadata = retrieve_video_from_gcs(video_id)
            if content and metadata:
                print(f"   📦 Retrieved from GCS cache")
                return content, metadata
        except Exception as e:
            print(f"   ⚠️  GCS retrieval failed: {e}")
    
    # Fallback to API (slow, costs money)
    print(f"   🌐 Fetching from Apify (not in GCS)")
    from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
    
    try:
        content, metadata = get_youtube_transcript(video_url, scraper='apify')
        return content, metadata
    except Exception as e:
        print(f"   ❌ Failed to fetch metadata: {e}")
        return None, None


def rescore_video(video_data, dry_run=False):
    """Re-score a single video."""
    video_id = video_data['video_id']
    video_url = video_data['video_url']
    old_score = video_data['old_score']
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {video_data['title'][:60]}...")
    print(f"   Old score: {old_score:.3f}")
    
    # Fetch metadata (from GCS if available)
    content, metadata = fetch_video_metadata(video_id, video_url)
    
    if not content or not metadata:
        print(f"   ⚠️  Skipping - could not fetch metadata")
        return None
    
    # Build query from video metadata
    query_parts = []
    title_lower = metadata.get('title', '').lower()
    
    # Extract domain from title or description
    keywords = ['piano', 'guitar', 'python', 'javascript', 'java', 'music', 'coding', 'programming']
    for keyword in keywords:
        if keyword in title_lower:
            query_parts.append(keyword)
    
    query = ' '.join(query_parts[:3]) if query_parts else metadata.get('title', '')
    
    # Parse published date
    published_at = None
    pub_date = metadata.get('published_at') or metadata.get('upload_date')
    if pub_date:
        try:
            published_at = datetime.fromisoformat(str(pub_date).replace('Z', '+00:00'))
        except:
            pass
    
    # Ensure counts are integers (handle both old and new field names)
    subscriber_count = int(metadata.get('subscriber_count', 0) or 0)
    view_count = int(metadata.get('view_count') or metadata.get('views', 0) or 0)
    like_count = int(metadata.get('like_count') or metadata.get('likes', 0) or 0)
    comment_count = int(metadata.get('comment_count') or metadata.get('comments', 0) or 0)
    duration_seconds = int(metadata.get('duration_seconds') or metadata.get('video_length_seconds', 0) or 0)
    
    # Create metrics
    metrics = ContentMetrics(
        title=metadata.get('title', ''),
        description=metadata.get('description', ''),
        transcript=content or '',
        query=query,
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
    
    # Score
    scorer = QualityScorer()
    score_result = scorer.score_content(metrics)
    new_score = score_result.overall
    
    print(f"   New score: {new_score:.3f}")
    print(f"   Change: {(new_score - old_score):+.3f}")
    print(f"   Breakdown: R={score_result.relevance:.2f} A={score_result.authority:.2f} "
          f"E={score_result.engagement:.2f} F={score_result.freshness:.2f} C={score_result.completeness:.2f}")
    
    # Update database
    if not dry_run:
        database_utils.update_video_status(
            video_id,
            'pending_review' if new_score < 0.8 else 'approved',
            score=new_score,
            reason=f"Re-scored: {new_score:.3f} (was {old_score:.3f})"
        )
        print(f"   ✅ Updated in database")
    
    return {
        'video_id': video_id,
        'old_score': old_score,
        'new_score': new_score,
        'change': new_score - old_score
    }


def main(dry_run=False, all_videos=False):
    print("=" * 80)
    print("🔄 RE-SCORE VIDEOS")
    print("=" * 80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database updates will be made")
    
    if all_videos:
        print("📊 Re-scoring ALL videos")
    else:
        print("📊 Re-scoring videos with score < 0.3 (broken scorer)")
    
    print()
    
    # Get videos to re-score
    videos = get_videos_to_rescore(all_videos=all_videos)
    
    if not videos:
        print("✅ No videos need re-scoring!")
        return
    
    print(f"Found {len(videos)} videos to re-score")
    print()
    
    # Confirm
    if not dry_run:
        response = input(f"Re-score {len(videos)} videos? This will use Apify API credits. (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        print()
    
    # Process videos
    results = []
    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}]", end=' ')
        result = rescore_video(video, dry_run=dry_run)
        if result:
            results.append(result)
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Videos processed: {len(results)}")
    
    if results:
        avg_old = sum(r['old_score'] for r in results) / len(results)
        avg_new = sum(r['new_score'] for r in results) / len(results)
        avg_change = avg_new - avg_old
        
        print(f"Average old score: {avg_old:.3f}")
        print(f"Average new score: {avg_new:.3f}")
        print(f"Average change: {avg_change:+.3f}")
        print()
        
        improved = sum(1 for r in results if r['change'] > 0)
        worse = sum(1 for r in results if r['change'] < 0)
        same = sum(1 for r in results if r['change'] == 0)
        
        print(f"Improved: {improved}")
        print(f"Worse: {worse}")
        print(f"Same: {same}")
    
    print()
    
    if dry_run:
        print("🔍 This was a dry run. Run without --dry-run to actually update scores.")
    else:
        print("✅ Re-scoring complete!")
        print()
        print("💡 Next steps:")
        print("   1. Check status: python scripts/check_video_status.py")
        print("   2. Review updated videos: streamlit run autodidact/ui/admin_dashboard.py")
    
    print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Re-score videos with corrected quality scorer")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without doing it")
    parser.add_argument('--all', action='store_true', help="Re-score ALL videos (not just low scores)")
    
    args = parser.parse_args()
    
    main(dry_run=args.dry_run, all_videos=args.all)
