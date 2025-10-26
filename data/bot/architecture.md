# Bot Architecture - Autodidact Content Crawler

## Overview

The Autodidact Content Crawler is a multi-platform web scraping and indexing system designed to discover, extract, and organize educational content from YouTube, Reddit, Quora, and educational blogs. The bot uses template-based question generation to systematically search for learning resources across all 217 domains and their subdomains.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Master Coordinator (main_bot.py)                │  │
│  │  - Job scheduling & queue management                      │  │
│  │  - Domain/subdomain iteration                             │  │
│  │  - Rate limiting & backoff                                │  │
│  │  - Error handling & retry logic                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    QUESTION GENERATION ENGINE                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │         Template Processor (question_engine.py)           │  │
│  │  - Loads 100+ question templates                         │  │
│  │  - Substitutes placeholders with domain/skill names       │  │
│  │  - Generates platform-specific queries                    │  │
│  │  - Creates search query batches                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     PLATFORM CRAWLER LAYER                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ YouTube  │  │  Reddit  │  │  Quora   │  │  Blogs   │       │
│  │ Crawler  │  │ Crawler  │  │ Crawler  │  │ Crawler  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      CONTENT EXTRACTION LAYER                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Content Extractor (extractor.py)             │  │
│  │  - HTML parsing & cleaning                                │  │
│  │  - Metadata extraction                                    │  │
│  │  - Transcript retrieval (YouTube)                         │  │
│  │  - Comment/discussion extraction                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     QUALITY ASSESSMENT LAYER                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Content Scorer (quality_scorer.py)              │  │
│  │  - Relevance scoring                                      │  │
│  │  - Authority/credibility assessment                       │  │
│  │  - Engagement metrics evaluation                          │  │
│  │  - Content freshness check                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Vector Store (Chroma) + PostgreSQL               │  │
│  │  - Content embeddings & semantic search                   │  │
│  │  - Metadata & structured data                             │  │
│  │  - Deduplication & versioning                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Master Coordinator (`main_bot.py`)

**Responsibilities:**
- Orchestrates the entire crawling workflow
- Manages job queues and task distribution
- Implements rate limiting and backoff strategies
- Handles errors, retries, and logging
- Coordinates between all subsystems

**Key Features:**
```python
class MasterCoordinator:
    def __init__(self):
        self.domain_loader = DomainLoader()
        self.question_engine = QuestionEngine()
        self.crawlers = {
            'youtube': YouTubeCrawler(),
            'reddit': RedditCrawler(),
            'quora': QuoraCrawler(),
            'blogs': BlogCrawler()
        }
        self.extractor = ContentExtractor()
        self.scorer = QualityScorer()
        self.storage = StorageManager()
        
    def run_full_crawl(self, domains=None, platforms=None):
        """Execute complete crawl cycle"""
        pass
        
    def run_incremental_crawl(self):
        """Update existing content with new resources"""
        pass
        
    def run_targeted_crawl(self, domain_id, question_category):
        """Crawl specific domain/category combination"""
        pass
```

**Configuration:**
```yaml
coordinator:
  max_concurrent_jobs: 10
  retry_attempts: 3
  retry_delay_seconds: 30
  checkpoint_interval: 100  # Save progress every N items
  enable_logging: true
  log_level: INFO
```

---

### 2. Question Generation Engine (`question_engine.py`)

**Responsibilities:**
- Load question templates from JSON
- Substitute placeholders with domain/subdomain data
- Generate platform-optimized queries
- Create search variations and permutations

**Template Processing:**
```python
class QuestionEngine:
    def __init__(self, templates_path):
        self.templates = self.load_templates(templates_path)
        self.domains = self.load_domains()
        
    def generate_queries(self, domain_id, platform=None):
        """
        Generate all applicable queries for a domain
        
        Args:
            domain_id: e.g., "MUSIC_PIANO"
            platform: Filter by platform (optional)
            
        Returns:
            List of generated query strings
        """
        queries = []
        domain_data = self.get_domain_data(domain_id)
        
        for template in self.templates:
            if platform and platform not in template['platforms']:
                continue
                
            query = self.substitute_placeholders(
                template['template'],
                domain_data
            )
            queries.append({
                'query': query,
                'template_id': template['id'],
                'category': template['category'],
                'platforms': template['platforms'],
                'skill_level': template['skill_level']
            })
            
        return queries
    
    def substitute_placeholders(self, template, domain_data):
        """Replace ${PLACEHOLDER} with actual values"""
        # Smart substitution logic
        # Handle ${DOMAIN}, ${SKILL}, ${TOOL}, etc.
        pass
```

**Query Optimization:**
- Generate query variations (synonyms, alternate phrasings)
- Platform-specific formatting (YouTube vs Reddit style)
- Add filters (date ranges, sort order, etc.)

---

### 3. Platform Crawlers

Each platform has a dedicated crawler implementing a common interface:

```python
class BaseCrawler(ABC):
    @abstractmethod
    def search(self, query, filters=None):
        """Execute search and return result URLs"""
        pass
        
    @abstractmethod
    def extract_metadata(self, url):
        """Get metadata without full content extraction"""
        pass
        
    @abstractmethod
    def get_rate_limit_params(self):
        """Return rate limiting configuration"""
        pass
```

#### 3.1 YouTube Crawler (`youtube_crawler.py`)

**Features:**
- YouTube Data API v3 integration
- Search by query with filters (duration, upload date, relevance)
- Video metadata extraction (title, description, stats, channel)
- Transcript/captions retrieval
- Comment extraction (top comments)
- Channel discovery and validation

**API Usage:**
```python
class YouTubeCrawler(BaseCrawler):
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
    def search(self, query, filters=None):
        """
        Search YouTube videos
        
        Filters:
            - max_results: int
            - upload_date: 'today', 'week', 'month', 'year'
            - duration: 'short', 'medium', 'long'
            - sort_by: 'relevance', 'viewCount', 'rating'
        """
        request = self.youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=filters.get('max_results', 25),
            order=filters.get('sort_by', 'relevance')
        )
        response = request.execute()
        return self.parse_search_results(response)
        
    def get_transcript(self, video_id):
        """Retrieve video transcript using youtube-transcript-api"""
        from youtube_transcript_api import YouTubeTranscriptApi
        return YouTubeTranscriptApi.get_transcript(video_id)
```

**Rate Limits:**
- 10,000 quota units per day (free tier)
- Search: 100 units per request
- Video details: 1 unit per request

---

#### 3.2 Reddit Crawler (`reddit_crawler.py`)

**Features:**
- PRAW (Python Reddit API Wrapper) integration
- Search across relevant subreddits
- Post and comment extraction
- User karma/credibility assessment
- Subreddit discovery for each domain

**Implementation:**
```python
class RedditCrawler(BaseCrawler):
    def __init__(self, client_id, client_secret, user_agent):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
    def search(self, query, subreddits=None, filters=None):
        """
        Search Reddit posts
        
        Args:
            query: Search query
            subreddits: List of subreddit names (or None for all)
            filters: time_filter, sort, limit
        """
        if subreddits:
            search_space = '+'.join(subreddits)
        else:
            search_space = 'all'
            
        results = self.reddit.subreddit(search_space).search(
            query,
            sort=filters.get('sort', 'relevance'),
            time_filter=filters.get('time_filter', 'all'),
            limit=filters.get('limit', 100)
        )
        
        return [self.parse_submission(post) for post in results]
        
    def get_relevant_subreddits(self, domain):
        """Discover subreddits relevant to domain"""
        # e.g., MUSIC_PIANO -> ['piano', 'learnpiano', 'pianolearning']
        pass
```

**Subreddit Mapping:**
```json
{
  "MUSIC_PIANO": ["piano", "learnpiano", "pianolearning"],
  "CODING_PYTHON": ["learnpython", "Python", "pythontips"],
  "MARTIAL_ARTS_BJJ": ["bjj", "brazilianjiujitsu", "bjj_training"]
}
```

---

#### 3.3 Quora Crawler (`quora_crawler.py`)

**Features:**
- Web scraping (BeautifulSoup + Selenium for dynamic content)
- Question and answer extraction
- Author credibility assessment
- Topic following for domains

**Implementation:**
```python
class QuoraCrawler(BaseCrawler):
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0...'
        }
        
    def search(self, query, filters=None):
        """
        Search Quora questions via web scraping
        Note: Quora has no official API
        """
        search_url = f"https://www.quora.com/search?q={quote(query)}"
        response = self.session.get(search_url, headers=self.headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        return self.parse_search_page(soup)
        
    def extract_answer_content(self, question_url):
        """Extract top answers from a Quora question"""
        # Use Selenium for JavaScript-rendered content
        pass
```

**Challenges:**
- No official API (requires web scraping)
- Heavy JavaScript rendering (needs Selenium)
- Rate limiting and bot detection
- Content behind login walls

---

#### 3.4 Blog Crawler (`blog_crawler.py`)

**Features:**
- Google Custom Search API for blog discovery
- RSS feed monitoring for educational blogs
- Content extraction with readability parsing
- Blog quality and authority scoring

**Implementation:**
```python
class BlogCrawler(BaseCrawler):
    def __init__(self, google_api_key, search_engine_id):
        self.api_key = google_api_key
        self.cse_id = search_engine_id
        self.known_blogs = self.load_blog_database()
        
    def search(self, query, filters=None):
        """Search for blog posts using Google Custom Search"""
        service = build("customsearch", "v1", developerKey=self.api_key)
        
        result = service.cse().list(
            q=query,
            cx=self.cse_id,
            num=10
        ).execute()
        
        return self.parse_search_results(result)
        
    def extract_article(self, url):
        """Extract clean article content using newspaper3k"""
        from newspaper import Article
        
        article = Article(url)
        article.download()
        article.parse()
        
        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date,
            'images': article.images,
            'top_image': article.top_image
        }
```

**Curated Blog Sources:**
Maintain a database of high-quality educational blogs per domain:
```json
{
  "CODING_PYTHON": [
    "realpython.com",
    "python.org/blog",
    "medium.com/tag/python"
  ],
  "MUSIC_THEORY": [
    "musictheory.net",
    "teoria.com"
  ]
}
```

---

### 4. Content Extractor (`extractor.py`)

**Responsibilities:**
- Parse HTML and extract clean content
- Handle different content formats (video, text, discussion)
- Extract structured metadata
- Normalize content across platforms

**Key Methods:**
```python
class ContentExtractor:
    def extract_youtube_content(self, video_data):
        """Extract YouTube video content + transcript"""
        return {
            'type': 'video',
            'platform': 'youtube',
            'url': video_data['url'],
            'title': video_data['title'],
            'description': video_data['description'],
            'transcript': self.get_transcript(video_data['id']),
            'duration': video_data['duration'],
            'channel': video_data['channel'],
            'views': video_data['views'],
            'likes': video_data['likes'],
            'published_date': video_data['published_at']
        }
        
    def extract_reddit_content(self, post_data):
        """Extract Reddit post + top comments"""
        return {
            'type': 'discussion',
            'platform': 'reddit',
            'title': post_data['title'],
            'selftext': post_data['selftext'],
            'url': post_data['url'],
            'score': post_data['score'],
            'comments': self.extract_top_comments(post_data),
            'subreddit': post_data['subreddit'],
            'author': post_data['author']
        }
```

---

### 5. Quality Scorer (`quality_scorer.py`)

**Responsibilities:**
- Score content relevance to query/domain
- Assess author/source credibility
- Evaluate engagement metrics
- Check content freshness and currency

**Scoring Algorithm:**
```python
class QualityScorer:
    def score_content(self, content, domain, query):
        """
        Calculate overall quality score (0-100)
        
        Weights:
            - Relevance: 30%
            - Authority: 25%
            - Engagement: 20%
            - Freshness: 15%
            - Completeness: 10%
        """
        relevance_score = self.calculate_relevance(content, query)
        authority_score = self.calculate_authority(content)
        engagement_score = self.calculate_engagement(content)
        freshness_score = self.calculate_freshness(content)
        completeness_score = self.calculate_completeness(content)
        
        total_score = (
            relevance_score * 0.30 +
            authority_score * 0.25 +
            engagement_score * 0.20 +
            freshness_score * 0.15 +
            completeness_score * 0.10
        )
        
        return {
            'total_score': total_score,
            'relevance': relevance_score,
            'authority': authority_score,
            'engagement': engagement_score,
            'freshness': freshness_score,
            'completeness': completeness_score
        }
```

**Scoring Criteria:**

**Relevance (30%):**
- Semantic similarity to query (embeddings)
- Keyword match density
- Domain-specific terminology presence
- Content depth on topic

**Authority (25%):**
- Creator credentials/expertise
- Channel/blog authority metrics
- Verification badges
- Community reputation (karma, followers)

**Engagement (20%):**
- Views/upvotes/likes
- Comment quality and quantity
- Share/save metrics
- Positive sentiment ratio

**Freshness (15%):**
- Publication date
- Last updated timestamp
- Relevance to current best practices
- Deprecation detection

**Completeness (10%):**
- Content length (sufficient depth)
- Multimedia elements (code samples, diagrams)
- Structured format (headers, lists)
- Clear explanations and examples

---

### 6. Storage Manager (`storage.py`)

**Responsibilities:**
- Store content in vector database (Chroma)
- Maintain metadata in PostgreSQL
- Handle deduplication
- Enable semantic search

**Schema Design:**

**PostgreSQL (Metadata):**
```sql
CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) UNIQUE,
    platform VARCHAR(50),
    url TEXT UNIQUE,
    title TEXT,
    domain_id VARCHAR(100),
    subdomain_id VARCHAR(100),
    template_id INTEGER,
    query_text TEXT,
    author_info JSONB,
    metrics JSONB,
    quality_scores JSONB,
    extracted_at TIMESTAMP,
    published_at TIMESTAMP,
    last_updated TIMESTAMP
);

CREATE INDEX idx_domain ON content(domain_id);
CREATE INDEX idx_platform ON content(platform);
CREATE INDEX idx_quality ON content((quality_scores->>'total_score'));
```

**Chroma (Vector Store):**
```python
class StorageManager:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.create_collection(
            name="educational_content",
            metadata={"description": "Learning resources"}
        )
        self.db = psycopg2.connect(...)
        
    def store_content(self, content, embedding):
        """Store content with embedding and metadata"""
        # Check for duplicates
        if self.is_duplicate(content['url']):
            return None
            
        # Store in Chroma
        self.collection.add(
            embeddings=[embedding],
            documents=[content['text']],
            metadatas=[content['metadata']],
            ids=[content['id']]
        )
        
        # Store in PostgreSQL
        self.insert_metadata(content)
        
    def search_similar(self, query_embedding, domain=None, limit=10):
        """Semantic search for similar content"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"domain_id": domain} if domain else None
        )
        return results
```

---

## Workflow Execution

### Full Crawl Workflow

```python
def full_crawl_workflow():
    """
    Complete crawl of all domains and platforms
    Estimated time: 7-14 days for 217 domains
    """
    
    coordinator = MasterCoordinator()
    
    # 1. Load domains and subdomains
    domains = coordinator.domain_loader.load_all()
    
    # 2. For each domain/subdomain
    for domain in domains:
        # 3. Generate all queries for this domain
        queries = coordinator.question_engine.generate_queries(domain['id'])
        
        # 4. Group queries by platform
        platform_queries = group_by_platform(queries)
        
        # 5. Crawl each platform
        for platform, query_list in platform_queries.items():
            crawler = coordinator.crawlers[platform]
            
            for query in query_list:
                # Rate limiting
                time.sleep(crawler.get_rate_limit_delay())
                
                # Search
                results = crawler.search(query['query'])
                
                # Extract content
                for result in results:
                    content = coordinator.extractor.extract(result, platform)
                    
                    # Score quality
                    scores = coordinator.scorer.score_content(
                        content, domain['id'], query['query']
                    )
                    
                    # Store if quality threshold met
                    if scores['total_score'] >= 60:
                        coordinator.storage.store_content(content, scores)
        
        # 6. Checkpoint progress
        coordinator.save_checkpoint(domain['id'])
```

### Incremental Update Workflow

```python
def incremental_update_workflow():
    """
    Update existing content with new resources
    Run daily/weekly
    """
    
    # Focus on:
    # 1. Recent content (last 7 days)
    # 2. High-traffic domains
    # 3. Domains with few resources
    # 4. Trending topics
    
    pass
```

---

## Configuration & Environment

### Environment Variables

```bash
# API Keys
YOUTUBE_API_KEY=your_youtube_key
GOOGLE_CSE_API_KEY=your_google_key
GOOGLE_CSE_ID=your_search_engine_id
REDDIT_CLIENT_ID=your_reddit_client
REDDIT_CLIENT_SECRET=your_reddit_secret

# Database
POSTGRES_HOST=localhost
POSTGRES_DB=autodidact
POSTGRES_USER=user
POSTGRES_PASSWORD=password
CHROMA_PERSIST_DIR=/path/to/chroma_data

# Rate Limiting
YOUTUBE_REQUESTS_PER_DAY=10000
REDDIT_REQUESTS_PER_MINUTE=60
BLOG_REQUESTS_PER_SECOND=2

# Thresholds
MIN_QUALITY_SCORE=60
MAX_CONTENT_AGE_DAYS=730
```

### Dependencies

```txt
# Core
python>=3.9
requests>=2.28.0
beautifulsoup4>=4.11.0
selenium>=4.8.0

# Platform APIs
google-api-python-client>=2.80.0
praw>=7.6.0
youtube-transcript-api>=0.5.0

# Content Extraction
newspaper3k>=0.2.8
readability-lxml>=0.8.1

# Storage
chromadb>=0.3.0
psycopg2-binary>=2.9.0
sentence-transformers>=2.2.0

# Utilities
python-dotenv>=0.21.0
loguru>=0.6.0
tenacity>=8.2.0
```

---

## Error Handling & Resilience

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def resilient_api_call(func, *args, **kwargs):
    """Retry API calls with exponential backoff"""
    return func(*args, **kwargs)
```

### Error Categories

1. **Network Errors**: Retry with backoff
2. **Rate Limit Errors**: Wait and retry with increased delay
3. **Authentication Errors**: Alert and stop
4. **Parsing Errors**: Log and skip content
5. **Storage Errors**: Queue for retry

---

## Monitoring & Logging

### Metrics to Track

- Queries executed per platform
- Content items discovered
- Content items stored (passed quality threshold)
- Average quality scores
- Error rates by type
- API quota usage
- Processing time per domain

### Logging Structure

```python
from loguru import logger

logger.add(
    "logs/crawler_{time}.log",
    rotation="500 MB",
    retention="30 days",
    level="INFO"
)

logger.info(
    "Crawl completed",
    domain=domain_id,
    platform=platform,
    queries_run=query_count,
    content_found=content_count,
    content_stored=stored_count,
    avg_quality=avg_quality_score
)
```

---

## Performance Optimization

### Parallelization

- Use `asyncio` for concurrent API requests
- Thread pools for independent platform crawls
- Process pools for CPU-intensive tasks (embedding generation)

### Caching

- Cache domain metadata
- Cache question templates
- Cache embeddings for duplicate detection
- Cache API responses (short TTL)

### Database Optimization

- Batch inserts for PostgreSQL
- Connection pooling
- Index optimization
- Periodic vacuum and analyze

---

## Future Enhancements

1. **Machine Learning Quality Scorer**: Train a model on user engagement data
2. **Automated Subreddit Discovery**: Use Reddit API to find new relevant communities
3. **Content Updating**: Re-crawl and update outdated content
4. **Multi-language Support**: Expand to non-English content
5. **User Feedback Loop**: Incorporate user ratings into quality scores
6. **Real-time Crawling**: Monitor for new content in real-time
7. **Image/Diagram Extraction**: Extract and index visual learning aids

---

## Security Considerations

- Store API keys in environment variables or secrets manager
- Implement rate limiting to avoid platform bans
- Use rotating user agents and proxies for web scraping
- Respect robots.txt and platform ToS
- Implement authentication for bot API endpoints
- Encrypt sensitive data at rest and in transit
