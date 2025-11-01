"""
Apify YouTube Crawler
=====================

Uses Apify's YouTube scraper to extract video metadata and transcripts.
Handles all proxy/IP blocking issues internally.

Apify Setup:
1. Sign up at https://apify.com
2. Get API token from https://console.apify.com/account/integrations
3. Set APIFY_API_TOKEN in .env

Pricing:
- Free tier: $5 credit
- ~$0.25 per 1000 videos
- Much cheaper than residential proxies

Apify Actors:
- YouTube Scraper: apify/youtube-scraper
- Includes: video metadata, transcripts, comments
"""

import os
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from apify_client import ApifyClient
from datetime import datetime

# Import for pipeline compatibility
try:
    from src.bot.question_engine import SearchQuery
    from src.models.unified_metadata_schema import UnifiedMetadata
    from src.bot.quality_scorer import QualityScorer, ContentMetrics, QualityScore
except ModuleNotFoundError:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    sys.path.insert(0, project_root)
    from src.bot.question_engine import SearchQuery
    from src.models.unified_metadata_schema import UnifiedMetadata
    from src.bot.quality_scorer import QualityScorer, ContentMetrics, QualityScore


@dataclass
class IndexableContent:
    """
    Container for content ready to be indexed.
    Includes both metadata and the actual text content.
    """
    metadata: UnifiedMetadata
    content: str  # Full text: title + description + transcript


class ApifyYouTubeCrawler:
    def fetch_channel_details(self, channel_id: str) -> Dict[str, Any]:
        """
        Fetch YouTube channel details using Apify (subscriber count, verification).
        Returns dict with 'subscriber_count' and 'is_verified'.
        """
        try:
            run_input = {
                "startUrls": [{"url": f"https://www.youtube.com/channel/{channel_id}"}],
                "scrapeChannelAbout": True,
                "scrapeChannelVideos": False,
                "scrapeChannelPlaylists": False
            }
            run = self.client.actor("streamers/youtube-channel-scraper").call(
                run_input=run_input,
                timeout_secs=60
            )
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                return {
                    "subscriber_count": item.get("subscriberCount", 0) or 0,
                    "is_verified": item.get("isVerified", False) or False
                }
        except Exception as e:
            print(f"   ⚠️  Channel details fetch failed: {e}")
            return {"subscriber_count": 0, "is_verified": False}
    """
    YouTube crawler using Apify's managed scraping service.
    
    Handles:
    - Video search
    - Metadata extraction
    - Transcript/subtitle extraction
    - Automatic proxy rotation (managed by Apify)
    - Rate limiting and retry logic
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        max_results_per_query: int = 5,
        timeout_seconds: int = 300,
        min_quality_score: float = 0.6,
        use_quality_scorer: bool = True
    ):
        """
        Initialize Apify YouTube crawler.
        
        Args:
            api_token: Apify API token (or set APIFY_API_TOKEN env var)
            max_results_per_query: Max videos to return per search
            timeout_seconds: Max time to wait for scrape to complete
            min_quality_score: Minimum quality score to index (0.0-1.0, default 0.6)
            use_quality_scorer: Enable intelligent quality scoring (default True)
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable not set")
        
        self.client = ApifyClient(self.api_token)
        self.max_results_per_query = max_results_per_query
        self.timeout_seconds = timeout_seconds
        self.min_quality_score = min_quality_score
        self.use_quality_scorer = use_quality_scorer
        
        # Initialize quality scorer
        self.quality_scorer = QualityScorer(
            min_score_threshold=min_quality_score
        ) if use_quality_scorer else None
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'total_videos_scraped': 0,
            'total_transcripts_extracted': 0,
            'total_videos_filtered': 0,  # New: videos filtered by quality
            'total_channel_lookups': 0,  # New: channel detail fetches
            'apify_runs': 0,
            'errors': 0
        }
        
        print(f"✅ ApifyYouTubeCrawler initialized:")
        print(f"   📊 Max results per query: {max_results_per_query}")
        print(f"   ⏱️  Timeout: {timeout_seconds}s")
        if use_quality_scorer:
            print(f"   🎯 Quality scoring enabled (min score: {min_quality_score})")
        else:
            print(f"   ⚠️  Quality scoring disabled")
    
    def search_videos(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search YouTube and return video metadata + transcripts.
        
        Args:
            query: Search query
            max_results: Max results (defaults to max_results_per_query)
        
        Returns:
            List of video dicts with metadata and transcripts
        """
        max_results = max_results or self.max_results_per_query
        self.stats['total_queries'] += 1
        
        print(f"🔍 Apify: Searching for '{query}' (max {max_results} results)")
        
        try:
            # Run the Apify YouTube Scraper actor
            run_input = {
                "searchKeywords": query,
                "maxResults": max_results,
                "downloadSubtitles": True,  # Extract transcripts
                "subtitlesLanguage": "en",
                "downloadThumbnails": False,
                "downloadVideos": False
            }
            
            # Start the actor run (using streamers/youtube-scraper - most popular)
            run = self.client.actor("streamers/youtube-scraper").call(
                run_input=run_input,
                timeout_secs=self.timeout_seconds
            )
            
            self.stats['apify_runs'] += 1
            
            # Get results from dataset
            results = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Extract transcript from subtitles list
                transcript = ''
                subtitles = item.get('subtitles', [])
                if subtitles and isinstance(subtitles, list):
                    # Find English subtitle
                    for sub in subtitles:
                        if sub.get('language') == 'en':
                            transcript = sub.get('srt', '')
                            break
                
                video_data = {
                    'video_id': item.get('id'),
                    'title': item.get('title'),
                    'description': item.get('text'),  # 'text' field contains description
                    'channel_title': item.get('channelName'),
                    'channel_id': item.get('channelId'),
                    'published_at': item.get('date'),  # 'date' field contains upload date
                    'duration': item.get('duration'),
                    'view_count': item.get('viewCount'),
                    'like_count': item.get('likes'),  # 'likes' not 'likeCount'
                    'comment_count': item.get('commentsCount'),  # 'commentsCount' not 'commentCount'
                    'transcript': transcript,
                    'url': f"https://www.youtube.com/watch?v={item.get('id')}",
                    'thumbnail_url': item.get('thumbnailUrl')
                }
                
                results.append(video_data)
                self.stats['total_videos_scraped'] += 1
                
                if video_data['transcript']:
                    self.stats['total_transcripts_extracted'] += 1
            
            print(f"✅ Apify: Found {len(results)} videos, {sum(1 for r in results if r['transcript'])} with transcripts")
            return results
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Apify search failed: {e}")
            return []
    
    def get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get channel details including subscriber count and verification status.
        
        Args:
            channel_id: YouTube channel ID
        
        Returns:
            Channel dict with subscriber_count and is_verified, or None if failed
        """
        try:
            self.stats['total_channel_lookups'] += 1
            
            run_input = {
                "startUrls": [{"url": f"https://www.youtube.com/channel/{channel_id}"}],
                "maxResults": 1,
                "downloadSubtitles": False,
                "downloadThumbnails": False,
                "downloadVideos": False
            }
            
            run = self.client.actor("streamers/youtube-scraper").call(
                run_input=run_input,
                timeout_secs=60  # Shorter timeout for channel lookup
            )
            
            self.stats['apify_runs'] += 1
            
            # Get channel info from dataset
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                channel_data = {
                    'channel_id': channel_id,
                    'subscriber_count': item.get('subscribersCount', 0) or 0,
                    'is_verified': item.get('isVerified', False) or False,
                    'channel_name': item.get('channelName', ''),
                    'description': item.get('channelDescription', '')
                }
                return channel_data
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  Channel lookup failed: {e}")
            return None
    
    def get_playlist_videos(
        self,
        playlist_url: str,
        max_videos: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all videos from a YouTube playlist.
        
        Args:
            playlist_url: YouTube playlist URL (e.g., https://www.youtube.com/playlist?list=PLxxx)
            max_videos: Maximum number of videos to fetch (None = all videos)
        
        Returns:
            List of video dicts with metadata and transcripts
        """
        print(f"📋 Apify: Fetching playlist {playlist_url}")
        if max_videos:
            print(f"   📊 Limited to {max_videos} videos")
        
        try:
            run_input = {
                "startUrls": [{"url": playlist_url}],
                "downloadSubtitles": True,
                "subtitlesLanguage": "en",
                "downloadThumbnails": False,
                "downloadVideos": False
            }
            
            if max_videos:
                run_input["maxResults"] = max_videos
            
            run = self.client.actor("streamers/youtube-scraper").call(
                run_input=run_input,
                timeout_secs=self.timeout_seconds
            )
            
            self.stats['apify_runs'] += 1
            
            # Get results from dataset
            results = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Extract transcript from subtitles list
                transcript = ''
                subtitles = item.get('subtitles', [])
                if subtitles and isinstance(subtitles, list):
                    # Find English subtitle
                    for sub in subtitles:
                        if sub.get('language') == 'en':
                            transcript = sub.get('srt', '')
                            break
                
                video_data = {
                    'video_id': item.get('id'),
                    'title': item.get('title'),
                    'description': item.get('text'),
                    'channel_title': item.get('channelName'),
                    'channel_id': item.get('channelId'),
                    'published_at': item.get('date'),
                    'duration': item.get('duration'),
                    'view_count': item.get('viewCount'),
                    'like_count': item.get('likes'),
                    'comment_count': item.get('commentsCount'),
                    'transcript': transcript,
                    'url': f"https://www.youtube.com/watch?v={item.get('id')}",
                    'thumbnail_url': item.get('thumbnailUrl')
                }
                
                results.append(video_data)
                self.stats['total_videos_scraped'] += 1
                
                if video_data['transcript']:
                    self.stats['total_transcripts_extracted'] += 1
            
            print(f"✅ Apify: Found {len(results)} videos in playlist, {sum(1 for r in results if r['transcript'])} with transcripts")
            return results
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Apify playlist fetch failed: {e}")
            return []
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific video by ID.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Video dict with metadata and transcript, or None if failed
        """
        print(f"📹 Apify: Fetching video {video_id}")
        
        try:
            run_input = {
                "startUrls": [{"url": f"https://www.youtube.com/watch?v={video_id}"}],
                "downloadSubtitles": True,
                "subtitlesLanguage": "en",
                "downloadThumbnails": False,
                "downloadVideos": False
            }
            
            run = self.client.actor("streamers/youtube-scraper").call(
                run_input=run_input,
                timeout_secs=self.timeout_seconds
            )
            
            self.stats['apify_runs'] += 1
            
            # Get first (and only) result
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                # Extract transcript from subtitles list
                transcript = ''
                subtitles = item.get('subtitles', [])
                if subtitles and isinstance(subtitles, list):
                    # Find English subtitle
                    for sub in subtitles:
                        if sub.get('language') == 'en':
                            transcript = sub.get('srt', '')
                            break
                
                video_data = {
                    'video_id': item.get('id'),
                    'title': item.get('title'),
                    'description': item.get('text'),  # 'text' field contains description
                    'channel_title': item.get('channelName'),
                    'channel_id': item.get('channelId'),
                    'published_at': item.get('date'),  # 'date' field contains upload date
                    'duration': item.get('duration'),
                    'view_count': item.get('viewCount'),
                    'like_count': item.get('likes'),  # 'likes' not 'likeCount'
                    'comment_count': item.get('commentsCount'),  # 'commentsCount' not 'commentCount'
                    'transcript': transcript,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'thumbnail_url': item.get('thumbnailUrl')
                }
                
                self.stats['total_videos_scraped'] += 1
                
                if video_data['transcript']:
                    self.stats['total_transcripts_extracted'] += 1
                
                print(f"✅ Apify: Video fetched, transcript: {'✓' if video_data['transcript'] else '✗'}")
                return video_data
            
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Apify video fetch failed: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get crawler statistics."""
        stats_dict = {
            **self.stats,
            'success_rate': (
                (self.stats['total_videos_scraped'] - self.stats['errors']) /
                max(self.stats['total_videos_scraped'], 1)
            ),
            'transcript_rate': (
                self.stats['total_transcripts_extracted'] /
                max(self.stats['total_videos_scraped'], 1)
            ),
            'filter_rate': (
                self.stats['total_videos_filtered'] /
                max(self.stats['total_videos_scraped'], 1)
            )
        }
        
        # Add quality scorer stats if enabled
        if self.use_quality_scorer and self.quality_scorer:
            stats_dict['quality_scorer'] = {
                'scores_calculated': self.quality_scorer.scores_calculated,
                'scores_above_threshold': self.quality_scorer.scores_above_threshold,
                'average_score': round(self.quality_scorer.average_score, 3)
            }
        
        return stats_dict
    
    def search_and_extract_batch(
        self,
        queries: List[SearchQuery],
        max_results_per_query: Optional[int] = None,
        delay_seconds: float = 1.0
    ) -> List[IndexableContent]:
        """
        Execute multiple search queries with rate limiting (pipeline-compatible interface).
        
        Args:
            queries: List of SearchQuery objects
            max_results_per_query: Max videos per query (default: self.max_results_per_query)
            delay_seconds: Delay between queries (default 1.0s)
        
        Returns:
            Combined list of IndexableContent from all queries
        """
        all_results = []
        max_results = max_results_per_query or self.max_results_per_query
        
        print(f"\n🚀 Apify Batch crawl: {len(queries)} queries")
        print(f"   Rate limit: {delay_seconds}s delay between queries\n")
        
        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] Processing: {query.query}")
            
            try:
                # Search videos using Apify
                videos = self.search_videos(query.query, max_results=max_results)
                
                # Convert to IndexableContent format
                for video in videos:
                    # Set required fields for UnifiedMetadata
                    from src.models.unified_metadata_schema import Difficulty
                    
                    # Determine difficulty
                    try:
                        difficulty = Difficulty(query.skill_level.lower()) if query.skill_level else Difficulty.BEGINNER
                    except Exception:
                        difficulty = Difficulty.BEGINNER
                    
                    # Compute text_length (transcript length or content length)
                    transcript = video.get('transcript', '')
                    text_length = len(transcript) if transcript else 0
                    
                    # Calculate quality score if enabled
                    if self.use_quality_scorer and self.quality_scorer:
                        # Parse published_at if it's a string
                        published_at = video.get('published_at')
                        if isinstance(published_at, str):
                            try:
                                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                            except:
                                published_at = None
                        
                        # First pass: Calculate initial quality without channel details
                        # Use a lower threshold (80% of target) for initial filter
                        initial_threshold = self.min_quality_score * 0.8
                        
                        initial_metrics = ContentMetrics(
                            query=query.query,
                            title=video.get('title', ''),
                            description=video.get('description', ''),
                            transcript=transcript,
                            tags=[],
                            channel_name=video.get('channel_title', ''),
                            subscriber_count=0,
                            is_verified=False,
                            view_count=video.get('view_count', 0) or 0,
                            like_count=video.get('like_count', 0) or 0,
                            comment_count=video.get('comment_count', 0) or 0,
                            published_at=published_at,
                            duration_seconds=video.get('duration', 0) or 0,
                            has_captions=bool(transcript)
                        )
                        
                        initial_score = self.quality_scorer.score_content(initial_metrics)
                        
                        # If video passes initial (relaxed) threshold, fetch channel details
                        subscriber_count = 0
                        is_verified = False
                        
                        if initial_score.overall >= initial_threshold:
                            channel_id = video.get('channel_id')
                            if channel_id:
                                self.stats['total_channel_lookups'] += 1
                                channel_info = self.fetch_channel_details(channel_id)
                                if channel_info:
                                    subscriber_count = channel_info['subscriber_count']
                                    is_verified = channel_info['is_verified']
                        else:
                            # Video filtered in first pass
                            video_title = video.get('title', 'Unknown')[:50]
                            print(f"   ⚠️  Filtered (initial): {video_title}... (quality: {initial_score.overall:.2f} < {initial_threshold:.2f})")
                            self.stats['total_videos_filtered'] += 1
                            continue
                        
                        # Build final ContentMetrics with channel details
                        content_metrics = ContentMetrics(
                            query=query.query,
                            title=video.get('title', ''),
                            description=video.get('description', ''),
                            transcript=transcript,
                            tags=[],  # Apify doesn't return tags
                            channel_name=video.get('channel_title', ''),
                            subscriber_count=subscriber_count,
                            is_verified=is_verified,
                            view_count=video.get('view_count', 0) or 0,
                            like_count=video.get('like_count', 0) or 0,
                            comment_count=video.get('comment_count', 0) or 0,
                            published_at=published_at,
                            duration_seconds=video.get('duration', 0) or 0,
                            has_captions=bool(transcript)
                        )
                        
                        # Calculate final quality score with channel details
                        quality_score = self.quality_scorer.score_content(content_metrics)
                        helpfulness_score = quality_score.overall
                        quality_breakdown = quality_score.to_dict()
                        
                        # Filter by quality threshold (final check with full scoring)
                        if not self.quality_scorer.passes_threshold(quality_score):
                            self.stats['total_videos_filtered'] += 1
                            video_title = video.get('title', 'Unknown')[:50]
                            print(f"   ⚠️  Filtered (final): {video_title}... (quality: {helpfulness_score:.2f})")
                            continue
                        
                        # Video passed both quality checks!
                        video_title = video.get('title', 'Unknown')[:50]
                        print(f"   ✅ Passed quality: {video_title}... (score: {helpfulness_score:.2f})")
                    else:
                        # Fallback to default score
                        helpfulness_score = 1.0
                        quality_breakdown = None
                    
                    metadata = UnifiedMetadata(
                        source=video['url'],
                        content_type="video",
                        domain_id=query.domain_id,
                        subdomain_id=query.subdomain_id,
                        skill_level=query.skill_level,
                        category=query.category,
                        technique=video['title'],
                        # Optional/legacy fields below:
                        author=video.get('channel_title'),
                        channel_id=video.get('channel_id'),
                        channel_url=f"https://www.youtube.com/channel/{video.get('channel_id')}" if video.get('channel_id') else None,
                        created_at=video.get('published_at'),
                        # Required fields:
                        difficulty=difficulty,
                        helpfulness_score=helpfulness_score,
                        text_length=text_length,
                        # Quality breakdown (if available)
                        quality_breakdown=quality_breakdown
                    )
                    
                    # Create full content string
                    content_parts = [
                        f"Title: {video['title']}",
                        f"Channel: {video['channel_title']}",
                        f"Description: {video.get('description', '')[:500]}",  # Limit description
                        f"\nTranscript:\n{video['transcript']}"
                    ]
                    content = "\n\n".join(part for part in content_parts if part)
                    
                    # Create IndexableContent
                    indexable = IndexableContent(
                        metadata=metadata,
                        content=content
                    )
                    all_results.append(indexable)
                
                print(f"   ✅ Extracted {len(videos)} videos ({sum(1 for v in videos if v['transcript'])} with transcripts)")
                
                # Rate limiting
                if i < len(queries):
                    time.sleep(delay_seconds)
            
            except Exception as e:
                print(f"   ❌ Error processing query: {e}")
                continue
        
        print(f"\n✅ Batch complete: {len(all_results)} videos total\n")
        return all_results


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("=" * 70)
    print("Apify YouTube Crawler Demo")
    print("=" * 70)
    
    # Initialize crawler
    crawler = ApifyYouTubeCrawler(max_results_per_query=3)
    
    # Test search
    print("\n📝 Test 1: Search for 'piano tutorial for beginners'")
    print("-" * 70)
    results = crawler.search_videos("piano tutorial for beginners", max_results=3)
    
    for i, video in enumerate(results, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   ID: {video['video_id']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   Transcript: {len(video['transcript'])} chars")
        if video['transcript']:
            print(f"   Preview: {video['transcript'][:150]}...")
    
    # Show stats
    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)
    stats = crawler.get_statistics()
    print(f"Queries: {stats['total_queries']}")
    print(f"Videos Scraped: {stats['total_videos_scraped']}")
    print(f"Transcripts: {stats['total_transcripts_extracted']}")
    print(f"Apify Runs: {stats['apify_runs']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print(f"Transcript Rate: {stats['transcript_rate']:.1%}")
