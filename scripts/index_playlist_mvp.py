"""
MVP Playlist Indexer
====================

Index an entire YouTube playlist to bootstrap the knowledge base.

Perfect for MVP where users bring their own curated learning content:
1. User provides playlist URL
2. System scrapes all videos
3. Quality scoring filters low-quality content
4. Generates learning roadmap from playlist

Usage:
    python scripts/index_playlist_mvp.py "https://www.youtube.com/playlist?list=PLxxx" --domain MUSIC --subdomain PIANO --difficulty beginner

Example playlists to test:
- Piano: https://www.youtube.com/playlist?list=PLpOuhygfD7QnP46wUgQudOySX_z2UOhXs
- Python: https://www.youtube.com/playlist?list=PL-osiE80TeTskrapNbzXhwoFUiLCjGgY7
- Guitar: https://www.youtube.com/playlist?list=PLlwfspJqZ126rGh9RxA77UZ9KcxBWAHfT
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.bot.crawlers.apify_youtube_crawler import ApifyYouTubeCrawler
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection
from src.models.unified_metadata_schema import UnifiedMetadata, Difficulty
from datetime import datetime


def index_playlist(
    playlist_url: str,
    domain_id: str = "UNKNOWN",
    subdomain_id: str = "UNKNOWN",
    difficulty: str = "beginner",
    category: str = "general",
    max_videos: int = None,
    min_quality: float = 0.55
):
    """
    Index all videos from a YouTube playlist.
    
    Args:
        playlist_url: YouTube playlist URL
        domain_id: Domain (e.g., MUSIC, CODING_SOFTWARE)
        subdomain_id: Subdomain (e.g., PIANO, PYTHON)
        difficulty: Difficulty level (beginner, intermediate, advanced)
        category: Category/topic
        max_videos: Maximum videos to index (None = all)
        min_quality: Minimum quality score (0.0-1.0)
    """
    load_dotenv()
    
    print("=" * 80)
    print("🎬 PLAYLIST INDEXER - MVP MODE")
    print("=" * 80)
    print(f"📋 Playlist: {playlist_url}")
    print(f"🏷️  Domain: {domain_id} > {subdomain_id}")
    print(f"📊 Difficulty: {difficulty}")
    print(f"🎯 Min Quality: {min_quality}")
    if max_videos:
        print(f"📹 Max Videos: {max_videos}")
    print("=" * 80)
    print()
    
    # Initialize crawler with quality scoring
    crawler = ApifyYouTubeCrawler(
        max_results_per_query=100,  # High limit for playlists
        min_quality_score=min_quality,
        use_quality_scorer=True
    )
    
    # Fetch playlist videos
    print("📡 Step 1: Fetching playlist videos...")
    videos = crawler.get_playlist_videos(playlist_url, max_videos=max_videos)
    
    if not videos:
        print("❌ No videos found in playlist!")
        return
    
    print(f"✅ Found {len(videos)} videos")
    print()
    
    # Initialize ChromaDB
    print("🗄️  Step 2: Connecting to ChromaDB...")
    client = get_chroma_client()
    collection = get_or_create_collection(client, "autodidact_ai_core_v2")
    print(f"✅ Collection ready (current size: {collection.count()})")
    print()
    
    # Process videos with quality scoring
    print("🎯 Step 3: Processing videos with quality scoring...")
    indexed_count = 0
    filtered_count = 0
    
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {video['title'][:60]}...")
        
        # Check if already indexed
        existing = collection.get(
            where={"source": video['url']},
            limit=1
        )
        
        if existing['ids']:
            print(f"   ⏭️  Already indexed, skipping")
            continue
        
        # Require transcript
        if not video.get('transcript'):
            print(f"   ⚠️  No transcript available, skipping")
            filtered_count += 1
            continue
        
        # Calculate quality score
        from src.bot.quality_scorer import QualityScorer, ContentMetrics
        
        scorer = QualityScorer(min_score_threshold=min_quality)
        
        # Parse published date
        published_at = video.get('published_at')
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except:
                published_at = None
        
        # Get channel details for better scoring
        channel_id = video.get('channel_id')
        subscriber_count = 0
        is_verified = False
        
        if channel_id:
            channel_info = crawler.fetch_channel_details(channel_id)
            if channel_info:
                subscriber_count = channel_info.get('subscriber_count', 0)
                is_verified = channel_info.get('is_verified', False)
        
        # Build metrics
        metrics = ContentMetrics(
            query=f"{domain_id} {subdomain_id} {difficulty}",
            title=video.get('title', ''),
            description=video.get('description', ''),
            transcript=video.get('transcript', ''),
            tags=[],
            channel_name=video.get('channel_title', ''),
            subscriber_count=subscriber_count,
            is_verified=is_verified,
            view_count=video.get('view_count', 0) or 0,
            like_count=video.get('like_count', 0) or 0,
            comment_count=video.get('comment_count', 0) or 0,
            published_at=published_at,
            duration_seconds=video.get('duration', 0) or 0,
            has_captions=True
        )
        
        quality_score = scorer.score_content(metrics)
        
        # Filter by quality
        if not scorer.passes_threshold(quality_score):
            print(f"   ⚠️  Quality too low: {quality_score.overall:.2f} < {min_quality}")
            print(f"       Breakdown: R={quality_score.relevance:.2f} A={quality_score.authority:.2f} "
                  f"E={quality_score.engagement:.2f} F={quality_score.freshness:.2f} C={quality_score.completeness:.2f}")
            filtered_count += 1
            continue
        
        print(f"   ✅ Quality: {quality_score.overall:.2f}")
        print(f"       Breakdown: R={quality_score.relevance:.2f} A={quality_score.authority:.2f} "
              f"E={quality_score.engagement:.2f} F={quality_score.freshness:.2f} C={quality_score.completeness:.2f}")
        
        # Create metadata
        metadata = UnifiedMetadata(
            source=video['url'],
            content_type="video",
            domain_id=domain_id,
            subdomain_id=subdomain_id,
            skill_level=difficulty,
            category=category,
            technique=video['title'],
            author=video.get('channel_title'),
            channel_id=video.get('channel_id'),
            channel_url=f"https://www.youtube.com/channel/{video.get('channel_id')}" if video.get('channel_id') else None,
            created_at=video.get('published_at'),
            difficulty=Difficulty(difficulty.lower()),
            helpfulness_score=quality_score.overall,
            text_length=len(video['transcript']),
            quality_breakdown=quality_score.to_dict()
        )
        
        # Create content
        content = f"""Title: {video['title']}

Channel: {video['channel_title']}

Description: {video.get('description', '')[:500]}

Transcript:
{video['transcript']}"""
        
        # Add to ChromaDB
        try:
            collection.add(
                documents=[content],
                metadatas=[metadata.to_dict()],
                ids=[f"video_{video['video_id']}"]
            )
            print(f"   ✅ Indexed successfully")
            indexed_count += 1
        except Exception as e:
            print(f"   ❌ Error indexing: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 INDEXING SUMMARY")
    print("=" * 80)
    print(f"Total videos in playlist: {len(videos)}")
    print(f"Successfully indexed: {indexed_count}")
    print(f"Filtered (quality/transcript): {filtered_count}")
    print(f"Skipped (already indexed): {len(videos) - indexed_count - filtered_count}")
    print(f"Final collection size: {collection.count()}")
    print()
    print("✅ Playlist indexing complete!")
    print()
    print("🚀 Next steps:")
    print("   1. Build knowledge graph: python scripts/build_knowledge_graph.py")
    print("   2. Generate curriculum: Use /curriculum/generate endpoint")
    print("   3. View in admin dashboard: python -m autodidact.ui.admin_dashboard")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index YouTube playlist for MVP")
    parser.add_argument("playlist_url", help="YouTube playlist URL")
    parser.add_argument("--domain", default="UNKNOWN", help="Domain ID (e.g., MUSIC)")
    parser.add_argument("--subdomain", default="UNKNOWN", help="Subdomain ID (e.g., PIANO)")
    parser.add_argument("--difficulty", default="beginner", choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--category", default="general", help="Category/topic")
    parser.add_argument("--max-videos", type=int, default=None, help="Maximum videos to index")
    parser.add_argument("--min-quality", type=float, default=0.55, help="Minimum quality score (0.0-1.0)")
    
    args = parser.parse_args()
    
    index_playlist(
        playlist_url=args.playlist_url,
        domain_id=args.domain,
        subdomain_id=args.subdomain,
        difficulty=args.difficulty,
        category=args.category,
        max_videos=args.max_videos,
        min_quality=args.min_quality
    )
