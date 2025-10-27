"""
Bot Indexer - Automated Content Acquisition & Storage
=====================================================

Orchestrates the full bot pipeline:
1. QuestionEngine generates search queries
2. YouTubeCrawler fetches videos + transcripts
3. IntakeAgent stores in ChromaDB with UnifiedMetadata

This is the main entry point for automated knowledge base expansion.

Usage:
    from src.bot.bot_indexer import BotIndexer
    
    # Initialize
    indexer = BotIndexer()
    
    # Index content for a specific domain/subdomain
    indexer.index_domain(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        skill_level="beginner",
        num_queries=5,
        videos_per_query=3
    )
    
    # Or index multiple domains
    indexer.index_batch([
        {"domain_id": "MUSIC", "subdomain_id": "PIANO"},
        {"domain_id": "MUSIC", "subdomain_id": "GUITAR"},
        {"domain_id": "CODING_SOFTWARE", "subdomain_id": "PYTHON"}
    ])
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Handle imports for both direct execution and module import
try:
    from src.bot.question_engine import QuestionEngine, SearchQuery
    from src.bot.crawlers.youtube_crawler import YouTubeCrawler
    from src.bot.crawlers.mock_youtube_crawler import MockYouTubeCrawler
    from src.agents.intake_agent import IntakeAgent
    from src.models.unified_metadata_schema import UnifiedMetadata
except ModuleNotFoundError:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, project_root)
    from src.bot.question_engine import QuestionEngine, SearchQuery
    from src.bot.crawlers.youtube_crawler import YouTubeCrawler
    from src.bot.crawlers.mock_youtube_crawler import MockYouTubeCrawler
    from src.agents.intake_agent import IntakeAgent
    from src.models.unified_metadata_schema import UnifiedMetadata


class BotIndexer:
    """
    Orchestrates automated content indexing pipeline.
    
    Components:
    - QuestionEngine: Generates search queries from templates
    - YouTubeCrawler: Fetches videos and transcripts
    - IntakeAgent: Stores content in ChromaDB v2 (768d embeddings)
    
    Attributes:
        question_engine: Template-based query generator
        youtube_crawler: YouTube search & transcript extractor
        intake_agent: ChromaDB storage manager
        stats: Indexing statistics
    """
    
    def __init__(
        self,
        youtube_api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        use_mock_crawler: bool = False,
        min_quality_score: float = 0.6,
        use_quality_scorer: bool = True,
        use_proxies: bool = False,
        proxy_config: Optional[str] = None
    ):
        """
        Initialize bot indexer pipeline.
        
        Args:
            youtube_api_key: YouTube Data API v3 key (defaults to env var)
            collection_name: ChromaDB collection name (defaults to v2)
            use_mock_crawler: Use MockYouTubeCrawler instead of real API (default False)
            min_quality_score: Minimum quality score to index (0.0-1.0, default 0.6)
            use_quality_scorer: Enable intelligent quality scoring (default True)
            use_proxies: Enable proxy rotation for transcript requests (default False)
            proxy_config: Path to proxy config file or None for default
        """
        print("=" * 70)
        print("Initializing Bot Indexer Pipeline")
        print("=" * 70)
        
        # Initialize components
        self.question_engine = QuestionEngine()
        
        if use_mock_crawler:
            print("\n⚠️  Using MOCK YouTube Crawler (no real API calls)")
            self.youtube_crawler = MockYouTubeCrawler(max_results_per_query=5)
        else:
            self.youtube_crawler = YouTubeCrawler(
                api_key=youtube_api_key,
                max_results_per_query=5,  # Conservative default
                min_quality_score=min_quality_score,
                use_quality_scorer=use_quality_scorer,
                use_proxies=use_proxies,
                proxy_config=proxy_config
            )
        
        self.intake_agent = IntakeAgent(collection_name=collection_name) if collection_name else IntakeAgent()
        
        # Statistics
        self.stats = {
            'queries_generated': 0,
            'videos_crawled': 0,
            'videos_indexed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        print("\n✅ Pipeline initialized successfully")
        print(f"   📊 QuestionEngine: {len(self.question_engine.templates)} templates")
        print(f"   🎬 YouTubeCrawler: {self.youtube_crawler.max_results_per_query} videos/query")
        print(f"   💾 IntakeAgent: {self.intake_agent.collection_name} collection\n")
    
    def index_domain(
        self,
        domain_id: str,
        subdomain_id: Optional[str] = None,
        platform: str = "youtube",
        skill_level: Optional[str] = None,
        category: Optional[str] = None,
        num_queries: int = 5,
        videos_per_query: int = 3,
        delay_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """
        Index content for a specific domain/subdomain.
        
        Args:
            domain_id: Domain to index (e.g., "MUSIC", "CODING_SOFTWARE")
            subdomain_id: Optional subdomain (e.g., "PIANO", "PYTHON")
            platform: Platform to crawl (default: "youtube")
            skill_level: Filter by skill level (beginner/intermediate/advanced/all)
            category: Filter by category
            num_queries: Number of search queries to generate
            videos_per_query: Max videos to extract per query
            delay_seconds: Delay between queries (rate limiting)
        
        Returns:
            Statistics dict with indexing results
        """
        self.stats['start_time'] = datetime.now()
        
        print("=" * 70)
        print(f"Indexing Content: {domain_id}/{subdomain_id or 'ALL'}")
        print("=" * 70)
        print(f"Platform: {platform}")
        print(f"Skill Level: {skill_level or 'all'}")
        print(f"Category: {category or 'all'}")
        print(f"Queries: {num_queries} × {videos_per_query} videos\n")
        
        # Step 1: Generate queries
        print("📝 Step 1/3: Generating Search Queries")
        print("-" * 70)
        
        queries = self.question_engine.generate_queries(
            domain_id=domain_id,
            subdomain_id=subdomain_id,
            platform=platform,
            skill_level=skill_level,
            category=category,
            limit=num_queries,
            shuffle=True
        )
        
        self.stats['queries_generated'] = len(queries)
        
        print(f"✅ Generated {len(queries)} queries\n")
        for i, q in enumerate(queries[:3], 1):
            print(f"   {i}. {q.query}")
        if len(queries) > 3:
            print(f"   ... and {len(queries) - 3} more\n")
        
        # Step 2: Crawl videos
        print("\n🎬 Step 2/3: Crawling YouTube Videos")
        print("-" * 70)
        
        videos = self.youtube_crawler.search_and_extract_batch(
            queries=queries,
            max_results_per_query=videos_per_query,
            delay_seconds=delay_seconds
        )
        
        self.stats['videos_crawled'] = len(videos)
        
        # Step 3: Index to ChromaDB
        print("\n💾 Step 3/3: Indexing to ChromaDB")
        print("-" * 70)
        
        indexed_count = 0
        error_count = 0
        
        for i, indexable in enumerate(videos, 1):
            try:
                # Index via IntakeAgent using the metadata and content from IndexableContent
                doc_id = self.intake_agent.process_and_add_document(
                    content=indexable.content,
                    source_url=indexable.metadata.source,
                    metadata=indexable.metadata
                )
                
                indexed_count += 1
                print(f"   ✅ [{i}/{len(videos)}] Indexed: {indexable.metadata.technique[:60]}...")
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ [{i}/{len(videos)}] Error indexing {indexable.metadata.source}: {e}")
                continue
        
        self.stats['videos_indexed'] = indexed_count
        self.stats['errors'] = error_count
        self.stats['end_time'] = datetime.now()
        
        # Final summary
        print("\n" + "=" * 70)
        print("Indexing Complete - Summary")
        print("=" * 70)
        
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print(f"📊 Queries Generated: {self.stats['queries_generated']}")
        print(f"🎬 Videos Crawled: {self.stats['videos_crawled']}")
        print(f"💾 Videos Indexed: {self.stats['videos_indexed']}")
        print(f"❌ Errors: {self.stats['errors']}")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📈 Rate: {self.stats['videos_indexed'] / duration:.2f} videos/second")
        
        # Quota info
        quota_stats = self.youtube_crawler.get_statistics()
        print(f"\n🔢 YouTube Quota:")
        print(f"   Used: {quota_stats['quota_used']:,}/{quota_stats['max_quota']:,} units")
        print(f"   Remaining: {quota_stats['quota_remaining']:,} units")
        print(f"   Estimated searches left: ~{quota_stats['quota_remaining'] // 100}")
        
        return self.stats
    
    def index_batch(
        self,
        domains: List[Dict[str, str]],
        platform: str = "youtube",
        queries_per_domain: int = 3,
        videos_per_query: int = 3,
        delay_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """
        Index multiple domains in batch.
        
        Args:
            domains: List of dicts with domain_id and optional subdomain_id
            platform: Platform to crawl
            queries_per_domain: Queries per domain
            videos_per_query: Videos per query
            delay_seconds: Delay between queries
        
        Returns:
            Aggregated statistics
        
        Example:
            indexer.index_batch([
                {"domain_id": "MUSIC", "subdomain_id": "PIANO"},
                {"domain_id": "MUSIC", "subdomain_id": "GUITAR"},
                {"domain_id": "CODING_SOFTWARE", "subdomain_id": "PYTHON"}
            ])
        """
        print("=" * 70)
        print(f"Batch Indexing: {len(domains)} domains")
        print("=" * 70)
        
        total_stats = {
            'queries_generated': 0,
            'videos_crawled': 0,
            'videos_indexed': 0,
            'errors': 0,
            'domains_processed': 0
        }
        
        for i, domain_config in enumerate(domains, 1):
            print(f"\n[{i}/{len(domains)}] Processing {domain_config.get('domain_id')}/{domain_config.get('subdomain_id', 'ALL')}")
            
            try:
                stats = self.index_domain(
                    domain_id=domain_config['domain_id'],
                    subdomain_id=domain_config.get('subdomain_id'),
                    platform=platform,
                    num_queries=queries_per_domain,
                    videos_per_query=videos_per_query,
                    delay_seconds=delay_seconds
                )
                
                # Aggregate stats
                total_stats['queries_generated'] += stats['queries_generated']
                total_stats['videos_crawled'] += stats['videos_crawled']
                total_stats['videos_indexed'] += stats['videos_indexed']
                total_stats['errors'] += stats['errors']
                total_stats['domains_processed'] += 1
                
            except Exception as e:
                print(f"❌ Error processing domain: {e}")
                total_stats['errors'] += 1
                continue
        
        # Final batch summary
        print("\n" + "=" * 70)
        print("Batch Indexing Complete - Total Summary")
        print("=" * 70)
        print(f"✅ Domains Processed: {total_stats['domains_processed']}/{len(domains)}")
        print(f"📊 Total Queries: {total_stats['queries_generated']}")
        print(f"🎬 Total Videos Crawled: {total_stats['videos_crawled']}")
        print(f"💾 Total Videos Indexed: {total_stats['videos_indexed']}")
        print(f"❌ Total Errors: {total_stats['errors']}")
        
        return total_stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current indexing statistics."""
        return {
            **self.stats,
            'youtube_quota': self.youtube_crawler.get_statistics(),
            'question_templates': self.question_engine.get_statistics()
        }


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Initialize indexer with REAL YouTube crawler + PROXIES
    print("\n💡 Using Real YouTube API Crawler with BrightData Proxy\n")
    indexer = BotIndexer(
        use_mock_crawler=False,
        use_proxies=True,
        proxy_config="proxy_config.json",
        min_quality_score=0.6
    )
    
    # Demo 1: Index single domain
    print("\n" + "=" * 70)
    print("DEMO: Indexing MUSIC/PIANO (Beginner Level)")
    print("=" * 70)
    
    stats = indexer.index_domain(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        skill_level="beginner",
        num_queries=2,  # Small batch for demo
        videos_per_query=2,
        delay_seconds=1.0
    )
    
    # Show final stats
    print("\n" + "=" * 70)
    print("Full Statistics")
    print("=" * 70)
    
    all_stats = indexer.get_statistics()
    print(f"\n📊 Indexing Stats:")
    print(f"   Queries: {all_stats['queries_generated']}")
    print(f"   Videos Crawled: {all_stats['videos_crawled']}")
    print(f"   Videos Indexed: {all_stats['videos_indexed']}")
    print(f"   Errors: {all_stats['errors']}")
    
    print(f"\n🎬 YouTube Stats:")
    yt_stats = all_stats['youtube_quota']
    print(f"   Quota Used: {yt_stats['quota_used']}/{yt_stats['max_quota']}")
    print(f"   Videos Seen: {yt_stats['videos_seen']}")
    
    print(f"\n📝 Template Stats:")
    template_stats = all_stats['question_templates']
    print(f"   Total Templates: {template_stats['total_templates']}")
    print(f"   Categories: {template_stats['categories']}")
    print(f"   Domains: {template_stats['total_domains']}")
