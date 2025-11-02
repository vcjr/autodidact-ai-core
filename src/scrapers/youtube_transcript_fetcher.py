"""
YouTube Transcript Fetcher
==========================

Unified interface for fetching YouTube transcripts using different backends:
- 'default': youtube-transcript-api (simple, free, no API key needed)
- 'apify': Apify YouTube Scraper (robust, handles geo-blocking, paid)
- 'api': YouTube Data API crawler (comprehensive metadata, free tier)

Configuration via environment variable YOUTUBE_SCRAPER or function parameter.
"""

import os
from typing import Optional, Tuple, Dict, Any


def get_youtube_transcript(
    url: str, 
    scraper: Optional[str] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Fetch YouTube transcript and metadata using the selected scraper.
    
    Args:
        url: YouTube video URL
        scraper: 'default', 'apify', or 'api'. 
                 If None, uses YOUTUBE_SCRAPER env var (default: 'default')
    
    Returns:
        Tuple of (transcript_text, metadata_dict)
        Returns (None, None) if transcript extraction fails
    
    Environment Variables:
        YOUTUBE_SCRAPER: default|apify|api (default: 'default')
        APIFY_API_TOKEN: Required if scraper='apify'
        YOUTUBE_API_KEY: Required if scraper='api'
    
    Examples:
        # Use default scraper
        transcript, metadata = get_youtube_transcript(url)
        
        # Use Apify (robust, handles geo-blocking)
        transcript, metadata = get_youtube_transcript(url, scraper='apify')
        
        # Use YouTube API (comprehensive metadata)
        transcript, metadata = get_youtube_transcript(url, scraper='api')
    """
    # Determine which scraper to use
    scraper = scraper or os.getenv('YOUTUBE_SCRAPER', 'default').lower()
    
    print(f"🎬 Fetching transcript using '{scraper}' scraper")
    
    if scraper == 'apify':
        return _fetch_with_apify(url)
    elif scraper == 'api':
        return _fetch_with_api_crawler(url)
    else:  # default
        return _fetch_with_default(url)


def _fetch_with_default(url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Fetch transcript using youtube-transcript-api (simple, free).
    This is imported from youtube_spider.py for backward compatibility.
    """
    try:
        from src.scrapers.youtube_spider import get_youtube_transcript as legacy_fetcher
        return legacy_fetcher(url)
    except Exception as e:
        print(f"❌ Default scraper error: {e}")
        return None, None


def _fetch_with_apify(url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Fetch transcript using Apify YouTube Scraper (robust, paid).
    Handles geo-blocking and provides high reliability.
    """
    try:
        from src.bot.crawlers.apify_youtube_crawler import ApifyYouTubeCrawler
        import re
        
        # Extract video ID from URL
        video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
        if not video_id_match:
            print(f"❌ Could not extract video ID from URL: {url}")
            return None, None
        
        video_id = video_id_match.group(1)
        
        # Initialize Apify crawler
        api_token = os.getenv('APIFY_API_TOKEN')
        if not api_token:
            print("❌ APIFY_API_TOKEN not set in environment")
            return None, None
        
        crawler = ApifyYouTubeCrawler(
            api_token=api_token,
            max_results_per_query=1,
            use_quality_scorer=False  # Disable for simple transcript fetch
        )
        
        # Search for the specific video URL
        results = crawler.search_videos(url, max_results=1)
        
        if not results or not results[0].get('transcript'):
            print(f"❌ No transcript found for video {video_id}")
            return None, None
        
        video = results[0]
        
        # Parse duration string (e.g., "15:23" or "1:05:30") to seconds
        duration_seconds = 0
        duration_str = video.get('duration', '')
        if duration_str:
            try:
                parts = duration_str.split(':')
                if len(parts) == 2:  # MM:SS
                    duration_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except:
                pass
        
        # Try to get channel details for subscriber count
        channel_details = None
        if video.get('channel_id'):
            try:
                channel_details = crawler.get_channel_details(video['channel_id'])
            except:
                pass
        
        # Format metadata to match expected schema
        metadata = {
            'source_url': url,
            'video_id': video_id,
            'title': video.get('title', f'Video {video_id}'),
            'channel_name': video.get('channel_title'),
            'channel_title': video.get('channel_title'),
            'channel_id': video.get('channel_id'),
            'channel_url': f"https://www.youtube.com/channel/{video.get('channel_id')}" if video.get('channel_id') else None,
            'views': video.get('view_count', 0),
            'view_count': video.get('view_count', 0),
            'like_count': video.get('like_count', 0),
            'comment_count': video.get('comment_count', 0),
            'duration': video.get('duration'),
            'duration_seconds': duration_seconds,
            'video_length_seconds': duration_seconds,
            'published_at': video.get('published_at'),
            'description': video.get('description', ''),
            'thumbnail_url': video.get('thumbnail_url'),
            'language': video.get('language', 'en'),
            'is_generated': False,  # Apify provides manual transcripts
            'transcript_language': video.get('language', 'en'),
            'is_translatable': True,
        }
        
        # Add channel metrics if available
        if channel_details:
            metadata['subscriber_count'] = channel_details.get('subscriber_count', 0)
            metadata['is_verified'] = channel_details.get('is_verified', False)
        
        transcript = video['transcript']
        print(f"✅ Apify: Fetched '{metadata['title']}' ({len(transcript)} chars)")
        print(f"   📊 Metadata: {metadata['view_count']:,} views, {metadata['like_count']:,} likes, {metadata['comment_count']:,} comments")
        
        return transcript, metadata
        
    except Exception as e:
        print(f"❌ Apify scraper error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def _fetch_with_api_crawler(url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Fetch transcript using YouTubeCrawler with Data API v3 (comprehensive metadata).
    Provides the most detailed metadata but requires API key and counts against quota.
    """
    try:
        from src.bot.crawlers.youtube_crawler import YouTubeCrawler
        import re
        
        # Extract video ID
        video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
        if not video_id_match:
            print(f"❌ Could not extract video ID from URL: {url}")
            return None, None
        
        video_id = video_id_match.group(1)
        
        # Initialize YouTube API crawler
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("❌ YOUTUBE_API_KEY not set in environment")
            return None, None
        
        crawler = YouTubeCrawler(
            api_key=api_key,
            max_results_per_query=1,
            use_quality_scorer=False,
            use_proxies=False
        )
        
        # Get video details
        video_details = crawler.get_video_details([video_id])
        if not video_details:
            print(f"❌ Could not fetch video details for {video_id}")
            return None, None
        
        details = video_details[0]
        
        # Get transcript
        transcript = crawler.get_transcript(video_id)
        if not transcript:
            print(f"❌ No transcript found for video {video_id}")
            return None, None
        
        # Search to get title and channel info
        # (YouTube API doesn't provide title in videos().list without 'snippet' part)
        search_results = crawler.search_videos(f"https://www.youtube.com/watch?v={video_id}", max_results=1)
        
        title = search_results[0]['title'] if search_results else f'Video {video_id}'
        channel_title = search_results[0]['channel_title'] if search_results else 'Unknown'
        
        # Format metadata
        metadata = {
            'source_url': url,
            'video_id': video_id,
            'title': title,
            'channel_name': channel_title,
            'channel_title': channel_title,
            'views': details.get('view_count', 0),
            'video_length_seconds': details.get('duration_seconds', 0),
            'language': 'en',
            'is_generated': False,
            'transcript_language': 'en',
            'is_translatable': True,
        }
        
        print(f"✅ YouTube API: Fetched '{metadata['title']}' ({len(transcript)} chars)")
        
        return transcript, metadata
        
    except Exception as e:
        print(f"❌ YouTube API crawler error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=vpn4qv4A1Aw"
    
    print("="*70)
    print("YouTube Transcript Fetcher - Testing All Scrapers")
    print("="*70)
    
    # Test default scraper
    print("\n1. Testing DEFAULT scraper (youtube-transcript-api)")
    print("-"*70)
    transcript, metadata = get_youtube_transcript(test_url, scraper='default')
    if transcript and metadata:
        print(f"✅ Success: {metadata['title']}")
        print(f"   Transcript length: {len(transcript)} chars")
    else:
        print("❌ Failed")
    
    # Test Apify scraper (if token available)
    if os.getenv('APIFY_API_TOKEN'):
        print("\n2. Testing APIFY scraper")
        print("-"*70)
        transcript, metadata = get_youtube_transcript(test_url, scraper='apify')
        if transcript and metadata:
            print(f"✅ Success: {metadata['title']}")
            print(f"   Transcript length: {len(transcript)} chars")
        else:
            print("❌ Failed")
    else:
        print("\n2. APIFY scraper skipped (APIFY_API_TOKEN not set)")
    
    # Test API crawler (if key available)
    if os.getenv('YOUTUBE_API_KEY'):
        print("\n3. Testing API scraper (YouTube Data API v3)")
        print("-"*70)
        transcript, metadata = get_youtube_transcript(test_url, scraper='api')
        if transcript and metadata:
            print(f"✅ Success: {metadata['title']}")
            print(f"   Transcript length: {len(transcript)} chars")
        else:
            print("❌ Failed")
    else:
        print("\n3. API scraper skipped (YOUTUBE_API_KEY not set)")
    
    print("\n" + "="*70)
    print("Testing complete!")
