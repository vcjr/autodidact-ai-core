"""
YouTube Crawler for Autodidact AI Bot
=====================================

Searches YouTube for educational content based on QuestionEngine queries,
extracts video metadata and transcripts, and converts to UnifiedMetadata schema.

Features:
- YouTube Data API v3 search (respects 10K requests/day quota)
- Transcript extraction via youtube-transcript-api
- UnifiedMetadata conversion with quality scoring placeholders
- Rate limiting and error handling
- Deduplication via URL tracking

Usage:
    from src.bot.crawlers import YouTubeCrawler
    from src.bot.question_engine import QuestionEngine
    
    # Initialize
    crawler = YouTubeCrawler(api_key="YOUR_YOUTUBE_API_KEY")
    engine = QuestionEngine()
    
    # Generate queries
    queries = engine.generate_queries(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        limit=5
    )
    
    # Crawl videos
    results = crawler.search_and_extract_batch(queries)
    
    # Store in ChromaDB
    for metadata in results:
        intake_agent.add_content(metadata)
"""

import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# Handle imports for both direct execution and module import
try:
    from src.models.unified_metadata_schema import (
        UnifiedMetadata,
        Platform,
        ContentType,
        Difficulty
    )
    from src.bot.question_engine import SearchQuery
    from src.bot.quality_scorer import QualityScorer, ContentMetrics, QualityScore
    from src.bot.proxy_manager import ProxyManager
except ModuleNotFoundError:
    # When running as script, add project root to path
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    sys.path.insert(0, project_root)
    from src.models.unified_metadata_schema import (
        UnifiedMetadata,
        Platform,
        ContentType,
        Difficulty
    )
    from src.bot.question_engine import SearchQuery
    from src.bot.quality_scorer import QualityScorer, ContentMetrics, QualityScore
    from src.bot.proxy_manager import ProxyManager

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)


@dataclass
class VideoResult:
    """Raw YouTube video data before conversion to UnifiedMetadata"""
    video_id: str
    title: str
    description: str
    channel_title: str
    published_at: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    transcript: Optional[str] = None
    transcript_language: str = "en"


@dataclass
class IndexableContent:
    """
    Container for content ready to be indexed.
    Includes both metadata and the actual text content.
    """
    metadata: UnifiedMetadata
    content: str  # Full text: title + description + transcript


class YouTubeCrawler:
    """
    YouTube content crawler with quota-aware searching and transcript extraction.
    
    Rate Limits:
    - YouTube Data API v3: 10,000 quota units/day
    - Search query: 100 units/query
    - Video details: 1 unit/video
    - Max ~95 searches/day or ~10,000 video detail calls/day
    
    Attributes:
        api_key: YouTube Data API v3 key
        youtube: Google API client
        quota_used: Estimated quota units consumed (resets daily)
        max_quota: Daily quota limit (default 10,000)
        seen_video_ids: Set of video IDs already crawled (for deduplication)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_quota: int = 10000,
        max_results_per_query: int = 10,
        min_quality_score: float = 0.0,
        use_quality_scorer: bool = True,
        use_proxies: bool = False,
        proxy_config: Optional[str] = None
    ):
        """
        Initialize YouTube crawler.
        
        Args:
            api_key: YouTube Data API v3 key (defaults to YOUTUBE_API_KEY env var)
            max_quota: Daily quota limit (default 10,000)
            max_results_per_query: Max videos per search query (default 10)
            min_quality_score: Minimum quality score to index (0.0-1.0, default 0.0)
            use_quality_scorer: Enable intelligent quality scoring (default True)
            use_proxies: Enable proxy rotation for transcript requests (default False)
            proxy_config: Path to proxy config file or None for default
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "YouTube API key required. Set YOUTUBE_API_KEY env var or pass api_key parameter."
            )
        
        # Initialize YouTube API client
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
        # Quota management
        self.max_quota = max_quota
        self.quota_used = 0
        self.max_results_per_query = max_results_per_query
        
        # Deduplication
        self.seen_video_ids = set()
        
        # Quality scoring
        self.use_quality_scorer = use_quality_scorer
        self.quality_scorer = QualityScorer(min_score_threshold=min_quality_score) if use_quality_scorer else None
        
        # Proxy management
        self.use_proxies = use_proxies
        self.proxy_manager = ProxyManager(config_file=proxy_config) if use_proxies else None
        
        print(f"✅ YouTubeCrawler initialized:")
        print(f"   📊 Daily quota: {self.max_quota:,} units")
        print(f"   🔍 Max results per query: {self.max_results_per_query}")
        if use_quality_scorer:
            print(f"   ⭐ Quality scoring: enabled (min threshold: {min_quality_score:.2f})")
        if use_proxies:
            proxy_count = len(self.proxy_manager.stats) if self.proxy_manager else 0
            print(f"   🔄 Proxy rotation: enabled ({proxy_count} proxies loaded)")
    
    def search_videos(
        self,
        query: str,
        max_results: Optional[int] = None,
        order: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos matching query.
        
        Args:
            query: Search query string
            max_results: Max videos to return (default: self.max_results_per_query)
            order: Sort order (relevance/date/rating/viewCount/title)
        
        Returns:
            List of video metadata dicts from YouTube API
        
        Quota Cost: 100 units per search query
        """
        if max_results is None:
            max_results = self.max_results_per_query
        
        # Check quota
        quota_cost = 100
        if self.quota_used + quota_cost > self.max_quota:
            raise RuntimeError(
                f"Quota exceeded: {self.quota_used}/{self.max_quota} units used. "
                "YouTube API quota resets daily at midnight PST."
            )
        
        try:
            # Execute search
            request = self.youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                maxResults=max_results,
                order=order,
                videoCaption="closedCaption",  # Prioritize videos with captions
                relevanceLanguage="en"
            )
            response = request.execute()
            
            # Update quota
            self.quota_used += quota_cost
            
            # Extract video IDs and metadata
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                
                # Skip if already seen
                if video_id in self.seen_video_ids:
                    continue
                
                videos.append({
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt']
                })
                
                self.seen_video_ids.add(video_id)
            
            print(f"🔍 Search: '{query}' → {len(videos)} videos (quota: {self.quota_used}/{self.max_quota})")
            return videos
        
        except HttpError as e:
            print(f"❌ YouTube API error: {e}")
            raise
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed metadata for video IDs (views, likes, duration, etc.)
        
        Args:
            video_ids: List of YouTube video IDs
        
        Returns:
            List of video detail dicts
        
        Quota Cost: 1 unit per video
        """
        if not video_ids:
            return []
        
        # Check quota (1 unit per video)
        quota_cost = len(video_ids)
        if self.quota_used + quota_cost > self.max_quota:
            raise RuntimeError(
                f"Quota exceeded: {self.quota_used}/{self.max_quota} units used"
            )
        
        try:
            # Fetch details (max 50 videos per request)
            request = self.youtube.videos().list(
                part="statistics,contentDetails",
                id=','.join(video_ids)
            )
            response = request.execute()
            
            # Update quota
            self.quota_used += quota_cost
            
            # Parse response
            details = []
            for item in response.get('items', []):
                video_id = item['id']
                stats = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                
                # Parse ISO 8601 duration (PT1H2M3S → seconds)
                duration = self._parse_duration(content_details.get('duration', 'PT0S'))
                
                details.append({
                    'video_id': video_id,
                    'view_count': int(stats.get('viewCount', 0)),
                    'like_count': int(stats.get('likeCount', 0)),
                    'comment_count': int(stats.get('commentCount', 0)),
                    'duration_seconds': duration
                })
            
            return details
        
        except HttpError as e:
            print(f"❌ Error fetching video details: {e}")
            raise
    
    def get_transcript(self, video_id: str, languages: List[str] = ['en']) -> Optional[str]:
        """
        Extract transcript from YouTube video with optional proxy support.
        
        Args:
            video_id: YouTube video ID
            languages: Preferred transcript languages (default: ['en'])
        
        Returns:
            Full transcript text or None if unavailable
        """
        # Try with proxy rotation if enabled
        if self.use_proxies and self.proxy_manager:
            from youtube_transcript_api.proxies import GenericProxyConfig
            for attempt in range(3):  # Max 3 attempts with different proxies
                proxy_url = self.proxy_manager.get_proxy()
                
                # Ensure proxy_url has scheme
                if proxy_url and not proxy_url.startswith("http"):
                    proxy_url = "http://" + proxy_url
                
                # Log which proxy we're using
                masked_proxy = self.proxy_manager._mask_proxy(proxy_url) if proxy_url else "Direct"
                print(f"🔄 Attempt {attempt + 1}/3: Using proxy {masked_proxy}")
                
                try:
                    # Create proxy config for both HTTP and HTTPS
                    proxy_config = GenericProxyConfig(
                        http_url=proxy_url,
                        https_url=proxy_url
                    ) if proxy_url else None
                    
                    print(f"   📡 Fetching transcript for {video_id}...")
                    api = YouTubeTranscriptApi(proxy_config=proxy_config)
                    transcript = api.fetch(video_id, languages=languages)
                    
                    # Success - record proxy performance
                    if proxy_url:
                        self.proxy_manager.record_success(proxy_url, response_time=1.0)
                    
                    print(f"   ✅ Success! Transcript retrieved ({len(transcript.snippets)} snippets)")
                    
                    # Concatenate text from transcript snippets
                    full_text = ' '.join([snippet.text for snippet in transcript.snippets])
                    return full_text
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)[:200]  # Truncate long errors
                    print(f"   ❌ Failed: {error_type}: {error_msg}")
                    
                    # Record proxy failure
                    if proxy_url:
                        self.proxy_manager.record_failure(proxy_url)
                    
                    # Last attempt failed - log and return None
                    if attempt == 2:
                        print(f"❌ All proxy attempts failed for {video_id}: {e}")
                        return None
                    continue
        
        # Direct connection (no proxies)
        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=languages)
            
            # Concatenate text from transcript snippets
            full_text = ' '.join([snippet.text for snippet in transcript.snippets])
            return full_text
            
        except TranscriptsDisabled:
            print(f"⚠️  Transcripts disabled for {video_id}")
            return None
        except NoTranscriptFound:
            print(f"⚠️  No transcript found for {video_id}")
            return None
        except VideoUnavailable:
            print(f"⚠️  Video {video_id} unavailable")
            return None
        except Exception as e:
            print(f"❌ Unexpected error getting transcript for {video_id}: {e}")
            return None
    
    def extract_video(
        self,
        video_data: Dict[str, Any],
        include_transcript: bool = True
    ) -> Optional[VideoResult]:
        """
        Extract full video data including transcript and engagement metrics.
        
        Args:
            video_data: Video metadata from search_videos()
            include_transcript: Whether to fetch transcript (default True)
        
        Returns:
            VideoResult or None if extraction failed
        """
        video_id = video_data['video_id']
        
        # Get detailed stats
        details_list = self.get_video_details([video_id])
        if not details_list:
            print(f"⚠️  No details for {video_id}")
            return None
        
        details = details_list[0]
        
        # Get transcript
        transcript = None
        if include_transcript:
            transcript = self.get_transcript(video_id)
            if transcript is None:
                print(f"⚠️  Skipping {video_id}: No transcript available")
                return None  # Skip videos without transcripts
        
        return VideoResult(
            video_id=video_id,
            title=video_data['title'],
            description=video_data['description'],
            channel_title=video_data['channel_title'],
            published_at=video_data['published_at'],
            view_count=details['view_count'],
            like_count=details['like_count'],
            comment_count=details['comment_count'],
            duration_seconds=details['duration_seconds'],
            transcript=transcript
        )
    
    def to_unified_metadata(
        self,
        video: VideoResult,
        query: SearchQuery
    ) -> IndexableContent:
        """
        Convert VideoResult to IndexableContent (metadata + content text).
        Uses QualityScorer to calculate intelligent quality metrics.
        
        Args:
            video: VideoResult from extract_video()
            query: Original SearchQuery used to find this video
        
        Returns:
            IndexableContent with UnifiedMetadata and full content text
        """
        # Parse difficulty from query skill level
        difficulty_map = {
            'beginner': Difficulty.BEGINNER,
            'intermediate': Difficulty.INTERMEDIATE,
            'advanced': Difficulty.ADVANCED,
            'all': Difficulty.INTERMEDIATE  # Default for "all levels"
        }
        difficulty = difficulty_map.get(
            query.skill_level.lower() if query.skill_level else 'intermediate',
            Difficulty.INTERMEDIATE
        )
        
        # Build engagement metrics
        engagement_metrics = {
            'views': video.view_count,
            'likes': video.like_count,
            'comments': video.comment_count,
            'duration_seconds': video.duration_seconds
        }
        
        # Parse ISO 8601 datetime
        try:
            created_at = datetime.fromisoformat(video.published_at.replace('Z', '+00:00'))
        except Exception:
            created_at = None
        
        # Build full content text
        full_content = f"Title: {video.title}\n\nDescription: {video.description}\n\n"
        if video.transcript:
            full_content += f"Transcript:\n{video.transcript}"
        
        text_length = len(full_content)
        
        # Calculate quality score if enabled
        if self.use_quality_scorer and self.quality_scorer:
            # Build ContentMetrics for scoring
            content_metrics = ContentMetrics(
                query=query.query,
                title=video.title,
                description=video.description,
                transcript=video.transcript or "",
                tags=[],  # YouTube tags not available in current API response
                channel_name=video.channel_title,
                subscriber_count=0,  # TODO: Fetch from channel API
                is_verified=False,  # TODO: Fetch from channel API
                view_count=video.view_count,
                like_count=video.like_count,
                comment_count=video.comment_count,
                published_at=created_at,
                duration_seconds=video.duration_seconds,
                has_captions=bool(video.transcript)
            )
            
            # Calculate quality score
            quality_score = self.quality_scorer.score_content(content_metrics)
            helpfulness_score = quality_score.overall
            quality_breakdown = quality_score.to_dict()
        else:
            # Fallback to placeholder score
            helpfulness_score = 0.5
            quality_breakdown = None
        
        # Build UnifiedMetadata
        metadata = UnifiedMetadata(
            # Identifiers
            domain_id=query.domain_id,
            subdomain_id=query.subdomain_id,
            
            # Content metadata
            source=f"https://youtube.com/watch?v={video.video_id}",
            platform=Platform.YOUTUBE,
            content_type=ContentType.VIDEO,
            
            # Author & timestamps
            author=video.channel_title,
            created_at=created_at,
            indexed_at=datetime.now(timezone.utc),
            
            # Learning metadata
            difficulty=difficulty,
            technique=video.title[:200],  # Use title as technique
            tags=[query.category] if query.category else [],
            
            # Quality metrics (from QualityScorer)
            helpfulness_score=helpfulness_score,
            quality_breakdown=quality_breakdown,
            
            # Engagement metrics
            engagement_metrics=engagement_metrics,
            
            # Document stats
            text_length=text_length,
            
            # Additional
            language="en",
            prerequisites=[],
            learning_outcomes=[]
        )
        
        return IndexableContent(metadata=metadata, content=full_content)
    
    def search_and_extract(
        self,
        query: SearchQuery,
        max_results: Optional[int] = None
    ) -> List[IndexableContent]:
        """
        Search YouTube for query and extract video metadata + transcripts.
        
        Args:
            query: SearchQuery from QuestionEngine
            max_results: Max videos to extract (default: self.max_results_per_query)
        
        Returns:
            List of IndexableContent instances (metadata + content text)
        """
        print(f"\n🎬 Searching YouTube: '{query.query}'")
        print(f"   Domain: {query.domain_id}/{query.subdomain_id or 'N/A'}")
        print(f"   Category: {query.category} | Level: {query.skill_level}")
        
        # Search videos
        videos_data = self.search_videos(
            query=query.query,
            max_results=max_results
        )
        
        if not videos_data:
            print("   ⚠️  No videos found")
            return []
        
        # Extract video details + transcripts
        results = []
        filtered_count = 0
        
        for video_data in videos_data:
            try:
                video = self.extract_video(video_data, include_transcript=True)
                if video and video.transcript:
                    # Convert to metadata (quality scoring happens here)
                    indexable = self.to_unified_metadata(
                        video=video,
                        query=query
                    )
                    
                    # Filter by quality threshold if scorer is enabled
                    if self.use_quality_scorer and self.quality_scorer:
                        quality_score = indexable.metadata.helpfulness_score
                        if not self.quality_scorer.passes_threshold(type('obj', (object,), {'overall': quality_score})()):
                            print(f"   ⚠️  Filtered (low quality {quality_score:.2f}): {video.title[:60]}...")
                            filtered_count += 1
                            continue
                    
                    results.append(indexable)
                    score_text = f" (quality: {indexable.metadata.helpfulness_score:.2f})" if self.use_quality_scorer else ""
                    print(f"   ✅ Extracted{score_text}: {video.title[:60]}... ({len(video.transcript)} chars)")
            except Exception as e:
                print(f"   ❌ Error extracting {video_data.get('video_id')}: {e}")
                continue
        
        if filtered_count > 0:
            print(f"   🚫 Filtered {filtered_count} low-quality videos")
        
        print(f"\n📊 Extracted {len(results)}/{len(videos_data)} videos with transcripts")
        return results
    
    def search_and_extract_batch(
        self,
        queries: List[SearchQuery],
        max_results_per_query: Optional[int] = None,
        delay_seconds: float = 1.0
    ) -> List[IndexableContent]:
        """
        Execute multiple search queries with rate limiting.
        
        Args:
            queries: List of SearchQuery objects
            max_results_per_query: Max videos per query
            delay_seconds: Delay between queries (default 1.0s)
        
        Returns:
            Combined list of IndexableContent from all queries
        """
        all_results = []
        
        print(f"\n🚀 Batch crawl: {len(queries)} queries")
        print(f"   Rate limit: {delay_seconds}s delay between queries\n")
        
        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] Processing query...")
            
            try:
                results = self.search_and_extract(
                    query=query,
                    max_results=max_results_per_query
                )
                all_results.extend(results)
                
                # Rate limiting
                if i < len(queries):
                    time.sleep(delay_seconds)
            
            except RuntimeError as e:
                if "Quota exceeded" in str(e):
                    print(f"\n⚠️  Quota limit reached after {i}/{len(queries)} queries")
                    print(f"   Extracted {len(all_results)} videos total")
                    break
                raise
            except Exception as e:
                print(f"❌ Error processing query {i}: {e}")
                continue
        
        print(f"\n✅ Batch complete: {len(all_results)} videos extracted")
        print(f"   Quota used: {self.quota_used}/{self.max_quota} units")
        
        return all_results
    
    def _parse_duration(self, iso_duration: str) -> int:
        """
        Parse ISO 8601 duration to seconds.
        
        Example: PT1H2M10S → 3730 seconds
        
        Args:
            iso_duration: ISO 8601 duration string
        
        Returns:
            Duration in seconds
        """
        import re
        
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, iso_duration)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get crawler statistics."""
        stats = {
            'quota_used': self.quota_used,
            'max_quota': self.max_quota,
            'quota_remaining': self.max_quota - self.quota_used,
            'videos_seen': len(self.seen_video_ids),
            'max_results_per_query': self.max_results_per_query
        }
        
        # Add quality scorer stats if enabled
        if self.use_quality_scorer and self.quality_scorer:
            stats['quality_scorer'] = self.quality_scorer.get_statistics()
        
        # Add proxy stats if enabled
        if self.use_proxies and self.proxy_manager:
            stats['proxy_manager'] = self.proxy_manager.get_statistics()
        
        return stats


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    from src.bot.question_engine import QuestionEngine
    
    # Load environment variables
    load_dotenv()
    
    # Initialize
    print("=" * 70)
    print("YouTube Crawler Demo")
    print("=" * 70)
    
    crawler = YouTubeCrawler(max_results_per_query=3)
    engine = QuestionEngine()
    
    # Generate test queries
    print("\n" + "=" * 70)
    print("Generating Test Queries")
    print("=" * 70)
    
    queries = engine.generate_queries(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        skill_level="beginner",
        limit=2
    )
    
    print(f"\n📝 Generated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q.query}")
        print(f"      Category: {q.category} | Level: {q.skill_level}")
    
    # Crawl videos
    print("\n" + "=" * 70)
    print("Crawling YouTube")
    print("=" * 70)
    
    results = crawler.search_and_extract_batch(
        queries=queries,
        max_results_per_query=3,
        delay_seconds=1.0
    )
    
    # Display results
    print("\n" + "=" * 70)
    print("Extraction Results")
    print("=" * 70)
    
    for i, indexable in enumerate(results, 1):
        metadata = indexable.metadata
        print(f"\n📹 Video {i}:")
        print(f"   Title: {metadata.technique}")
        print(f"   Source: {metadata.source}")
        print(f"   Author: {metadata.author}")
        print(f"   Domain: {metadata.domain_id}/{metadata.subdomain_id}")
        print(f"   Difficulty: {metadata.difficulty.value}")
        print(f"   Views: {metadata.engagement_metrics.get('views', 0):,}")
        print(f"   Likes: {metadata.engagement_metrics.get('likes', 0):,}")
        print(f"   Duration: {metadata.engagement_metrics.get('duration_seconds', 0)} seconds")
        print(f"   Text Length: {metadata.text_length:,} characters")
        print(f"   Content Preview: {indexable.content[:100]}...")
        print(f"   Quality Score: {metadata.helpfulness_score}")
    
    # Statistics
    print("\n" + "=" * 70)
    print("Crawler Statistics")
    print("=" * 70)
    
    stats = crawler.get_statistics()
    print(f"   Quota Used: {stats['quota_used']}/{stats['max_quota']} units")
    print(f"   Quota Remaining: {stats['quota_remaining']} units")
    print(f"   Videos Extracted: {stats['videos_seen']}")
    print(f"   Estimated Searches Left Today: ~{stats['quota_remaining'] // 100}")
