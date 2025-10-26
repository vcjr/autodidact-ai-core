# Platform-Specific Implementation Notes

## YouTube Crawler Implementation Notes

### API Setup

1. **Get API Key:**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable YouTube Data API v3
   - Create API credentials (API Key)
   - Restrict key to YouTube Data API v3

2. **Quota Management:**
   - Default: 10,000 units/day
   - Search costs: 100 units
   - Video details: 1 unit
   - **Strategy:** 50 searches + 5,000 video details per day

### Code Example

```python
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import time

class YouTubeCrawler:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.quota_used = 0
        
    def search_videos(self, query, max_results=25):
        """Search for videos and return results"""
        try:
            request = self.youtube.search().list(
                q=query,
                part='id,snippet',
                type='video',
                maxResults=max_results,
                order='relevance',
                videoCaption='closedCaption',  # Prefer videos with captions
                videoDuration='medium'  # 4-20 minutes
            )
            response = request.execute()
            self.quota_used += 100  # Search costs 100 units
            
            return self._parse_search_results(response)
        except Exception as e:
            print(f"YouTube search error: {e}")
            return []
    
    def get_video_details(self, video_id):
        """Get detailed video information"""
        request = self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        )
        response = request.execute()
        self.quota_used += 1
        
        if response['items']:
            return response['items'][0]
        return None
    
    def get_transcript(self, video_id):
        """Get video transcript/captions"""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join([entry['text'] for entry in transcript])
        except:
            return None
```

---

## Reddit Crawler Implementation Notes

### API Setup

1. **Create Reddit App:**
   - Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
   - Click "Create App" or "Create Another App"
   - Select "script" type
   - Note: client_id, client_secret

2. **Install PRAW:**
   ```bash
   pip install praw
   ```

### Subreddit Mapping Database

Create `config/subreddit_mappings.json`:

```json
{
  "MUSIC_PIANO": {
    "primary": ["piano", "pianolearning"],
    "secondary": ["musictheory", "classicalmusic"],
    "general": ["learnmusic"]
  },
  "CODING_PYTHON": {
    "primary": ["learnpython", "Python"],
    "secondary": ["pythontips", "learnprogramming"],
    "general": ["programming", "coding"]
  },
  "FITNESS_TRAINING": {
    "primary": ["Fitness", "bodyweightfitness"],
    "secondary": ["gainit", "loseit"],
    "general": ["health"]
  }
}
```

### Code Example

```python
import praw
import json

class RedditCrawler:
    def __init__(self, client_id, client_secret, user_agent):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.subreddit_map = self._load_subreddit_mappings()
        
    def _load_subreddit_mappings(self):
        with open('config/subreddit_mappings.json') as f:
            return json.load(f)
    
    def get_relevant_subreddits(self, domain_id):
        """Get list of relevant subreddits for domain"""
        mapping = self.subreddit_map.get(domain_id, {})
        return mapping.get('primary', []) + mapping.get('secondary', [])
    
    def search_posts(self, query, domain_id, limit=100):
        """Search Reddit posts in relevant subreddits"""
        subreddits = self.get_relevant_subreddits(domain_id)
        if not subreddits:
            subreddits = ['all']
        
        search_space = '+'.join(subreddits)
        results = []
        
        for post in self.reddit.subreddit(search_space).search(
            query, 
            sort='relevance', 
            time_filter='all', 
            limit=limit
        ):
            results.append({
                'title': post.title,
                'selftext': post.selftext,
                'url': post.url,
                'score': post.score,
                'num_comments': post.num_comments,
                'created_utc': post.created_utc,
                'author': str(post.author),
                'subreddit': str(post.subreddit),
                'id': post.id
            })
        
        return results
    
    def get_top_comments(self, post_id, limit=10):
        """Extract top comments from a post"""
        submission = self.reddit.submission(id=post_id)
        submission.comment_sort = 'top'
        submission.comments.replace_more(limit=0)  # Remove "more comments"
        
        comments = []
        for comment in submission.comments.list()[:limit]:
            if comment.score > 10:  # Minimum score threshold
                comments.append({
                    'body': comment.body,
                    'score': comment.score,
                    'author': str(comment.author),
                    'created_utc': comment.created_utc
                })
        
        return comments
```

---

## Quora Crawler Implementation Notes

### Web Scraping Setup

**⚠️ Warning:** Quora has no official API. Web scraping should be done carefully and ethically.

1. **Install Dependencies:**
   ```bash
   pip install selenium beautifulsoup4 webdriver-manager
   ```

2. **Chrome Driver Setup:**
   ```python
   from selenium import webdriver
   from selenium.webdriver.chrome.service import Service
   from webdriver_manager.chrome import ChromeDriverManager
   ```

### Rate Limiting Strategy

- **Max 30 requests per minute**
- **Rotate user agents**
- **Use delays between requests**
- **Consider using proxies for scale**

### Code Example

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random

class QuoraCrawler:
    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_questions(self, query, max_results=20):
        """Search Quora for questions"""
        search_url = f"https://www.quora.com/search?q={query.replace(' ', '+')}"
        self.driver.get(search_url)
        
        # Wait for results to load
        time.sleep(random.uniform(2, 4))
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        questions = self._parse_search_results(soup, max_results)
        
        return questions
    
    def _parse_search_results(self, soup, max_results):
        """Parse search results page"""
        results = []
        
        # Quora's HTML structure (may change)
        question_elements = soup.find_all('div', {'class': 'q-box'})[:max_results]
        
        for elem in question_elements:
            try:
                title = elem.find('a', {'class': 'question_link'})
                if title:
                    results.append({
                        'title': title.get_text(strip=True),
                        'url': 'https://www.quora.com' + title.get('href'),
                    })
            except:
                continue
        
        return results
    
    def get_answers(self, question_url, max_answers=5):
        """Extract answers from a Quora question"""
        self.driver.get(question_url)
        time.sleep(random.uniform(2, 4))
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Extract answers (HTML structure may vary)
        answers = []
        answer_elements = soup.find_all('div', {'class': 'Answer'})[:max_answers]
        
        for elem in answer_elements:
            try:
                content = elem.find('div', {'class': 'answer_content'})
                upvotes = elem.find('span', {'class': 'count'})
                
                if content:
                    answers.append({
                        'content': content.get_text(strip=True),
                        'upvotes': int(upvotes.get_text()) if upvotes else 0
                    })
            except:
                continue
        
        return answers
    
    def close(self):
        """Close browser"""
        self.driver.quit()
```

---

## Blog Crawler Implementation Notes

### Google Custom Search Setup

1. **Create Custom Search Engine:**
   - Visit [Google CSE](https://programmablesearchengine.google.com/)
   - Create new search engine
   - Configure to search the entire web or specific sites
   - Get Search Engine ID

2. **Enable Custom Search API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Custom Search API
   - Create API key

### Known Educational Blog Database

Create `config/educational_blogs.json`:

```json
{
  "CODING": [
    "dev.to",
    "freecodecamp.org",
    "realpython.com",
    "css-tricks.com",
    "scotch.io",
    "digitalocean.com/community/tutorials"
  ],
  "DATA_SCIENCE": [
    "towardsdatascience.com",
    "kdnuggets.com",
    "machinelearningmastery.com",
    "analyticsvidhya.com"
  ],
  "MUSIC": [
    "musictheory.net",
    "ultimate-guitar.com/lessons",
    "soundfly.com/courses"
  ],
  "FITNESS": [
    "strongerbyscience.com",
    "barbend.com",
    "menshealth.com/fitness"
  ]
}
```

### Code Example

```python
from googleapiclient.discovery import build
from newspaper import Article
import requests
from bs4 import BeautifulSoup

class BlogCrawler:
    def __init__(self, api_key, search_engine_id):
        self.api_key = api_key
        self.cse_id = search_engine_id
        self.service = build("customsearch", "v1", developerKey=api_key)
        self.educational_blogs = self._load_blog_database()
        
    def _load_blog_database(self):
        with open('config/educational_blogs.json') as f:
            return json.load(f)
    
    def search_blogs(self, query, domain_category=None):
        """Search for blog posts using Google CSE"""
        # Optionally restrict to known educational blogs
        site_restrict = None
        if domain_category and domain_category in self.educational_blogs:
            sites = self.educational_blogs[domain_category]
            site_restrict = ' OR '.join([f'site:{site}' for site in sites])
        
        full_query = f"{query} {site_restrict}" if site_restrict else query
        
        try:
            result = self.service.cse().list(
                q=full_query,
                cx=self.cse_id,
                num=10,
                dateRestrict='y2'  # Last 2 years
            ).execute()
            
            return self._parse_search_results(result)
        except Exception as e:
            print(f"Blog search error: {e}")
            return []
    
    def _parse_search_results(self, result):
        """Parse Google CSE results"""
        if 'items' not in result:
            return []
        
        results = []
        for item in result['items']:
            results.append({
                'title': item['title'],
                'url': item['link'],
                'snippet': item['snippet'],
                'published_date': item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time')
            })
        
        return results
    
    def extract_article(self, url):
        """Extract article content using newspaper3k"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'top_image': article.top_image,
                'images': list(article.images),
                'word_count': len(article.text.split())
            }
        except Exception as e:
            print(f"Article extraction error: {e}")
            return None
```

---

## Quality Scoring Implementation

### Scoring Algorithm Details

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime, timedelta

class QualityScorer:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def calculate_relevance(self, content, query, domain):
        """
        Calculate semantic relevance (0-100)
        
        Methods:
        1. Embedding similarity (70%)
        2. Keyword matching (30%)
        """
        # Embedding similarity
        content_embedding = self.model.encode(content['text'][:1000])
        query_embedding = self.model.encode(query)
        similarity = np.dot(content_embedding, query_embedding)
        similarity_score = (similarity + 1) * 50  # Normalize to 0-100
        
        # Keyword matching
        keywords = self._extract_keywords(domain)
        keyword_score = self._keyword_density(content['text'], keywords) * 100
        
        # Weighted average
        relevance = (similarity_score * 0.7) + (keyword_score * 0.3)
        return min(100, relevance)
    
    def calculate_authority(self, content):
        """
        Calculate source authority (0-100)
        
        Factors:
        - Creator credentials (if available)
        - Platform authority
        - Community validation
        """
        score = 50  # Base score
        
        if content['platform'] == 'youtube':
            # Check channel subscribers, verification
            if content.get('channel_verified'):
                score += 20
            if content.get('channel_subscribers', 0) > 100000:
                score += 15
                
        elif content['platform'] == 'reddit':
            # Check author karma, awards
            if content.get('author_karma', 0) > 10000:
                score += 15
            if content.get('awards', 0) > 0:
                score += 10
                
        elif content['platform'] == 'blog':
            # Check domain authority, author bio
            if self._is_known_authority(content['domain']):
                score += 25
        
        return min(100, score)
    
    def calculate_engagement(self, content):
        """
        Calculate engagement metrics (0-100)
        
        Platform-specific metrics:
        - YouTube: views, likes, comments
        - Reddit: score, comments
        - Quora: upvotes
        - Blogs: shares, comments
        """
        if content['platform'] == 'youtube':
            views = content.get('views', 0)
            likes = content.get('likes', 0)
            like_ratio = likes / max(views, 1)
            
            # Normalize
            view_score = min(50, np.log10(max(views, 1)) * 10)
            like_score = min(50, like_ratio * 1000)
            
            return view_score + like_score
            
        elif content['platform'] == 'reddit':
            score = content.get('score', 0)
            comments = content.get('num_comments', 0)
            
            score_points = min(60, np.log10(max(score, 1)) * 30)
            comment_points = min(40, np.log10(max(comments, 1)) * 20)
            
            return score_points + comment_points
        
        # Default
        return 50
    
    def calculate_freshness(self, content, domain_category):
        """
        Calculate content freshness (0-100)
        
        Time decay based on domain:
        - Tech domains: steep decay (outdated quickly)
        - Fundamental domains: slow decay (evergreen)
        """
        if 'published_date' not in content or not content['published_date']:
            return 50  # Unknown date = medium score
        
        published = content['published_date']
        age_days = (datetime.now() - published).days
        
        # Domain-specific decay rates
        decay_rates = {
            'CODING': 365,      # Tech: 1 year half-life
            'DATA_SCIENCE': 365,
            'MARKETING': 365,
            'MATHEMATICS': 3650, # Fundamentals: 10 year half-life
            'MUSIC': 1825,       # Skills: 5 year half-life
            'FITNESS': 730,      # Health: 2 year half-life
        }
        
        half_life = decay_rates.get(domain_category, 730)
        freshness = 100 * (0.5 ** (age_days / half_life))
        
        return max(0, min(100, freshness))
    
    def calculate_completeness(self, content):
        """
        Calculate content completeness (0-100)
        
        Factors:
        - Length (sufficient depth)
        - Structure (headers, formatting)
        - Examples (code, images, etc.)
        """
        score = 0
        
        # Length check
        text_length = len(content.get('text', ''))
        if text_length > 2000:
            score += 40
        elif text_length > 1000:
            score += 30
        elif text_length > 500:
            score += 20
        
        # Structure check (for blogs)
        if content['platform'] == 'blog':
            if content.get('has_images'):
                score += 20
            if content.get('has_code_blocks'):
                score += 20
            if content.get('has_headers'):
                score += 20
        
        # For videos, check for transcript
        elif content['platform'] == 'youtube':
            if content.get('transcript'):
                score += 60
        
        return min(100, score)
    
    def score_content(self, content, query, domain):
        """
        Calculate overall quality score (0-100)
        
        Returns dict with all subscores
        """
        relevance = self.calculate_relevance(content, query, domain)
        authority = self.calculate_authority(content)
        engagement = self.calculate_engagement(content)
        freshness = self.calculate_freshness(content, domain)
        completeness = self.calculate_completeness(content)
        
        # Weighted average
        total_score = (
            relevance * 0.30 +
            authority * 0.25 +
            engagement * 0.20 +
            freshness * 0.15 +
            completeness * 0.10
        )
        
        return {
            'total_score': round(total_score, 2),
            'relevance': round(relevance, 2),
            'authority': round(authority, 2),
            'engagement': round(engagement, 2),
            'freshness': round(freshness, 2),
            'completeness': round(completeness, 2)
        }
```

---

## Performance Optimization Tips

### 1. Batch Processing

```python
# Instead of processing one at a time
for url in urls:
    content = extract(url)
    score = scorer.score(content)
    store(content, score)

# Batch process
batch_size = 100
for i in range(0, len(urls), batch_size):
    batch = urls[i:i+batch_size]
    contents = [extract(url) for url in batch]
    scores = [scorer.score(c) for c in contents]
    store_batch(contents, scores)
```

### 2. Async API Calls

```python
import asyncio
import aiohttp

async def fetch_multiple_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()
```

### 3. Connection Pooling

```python
import psycopg2.pool

# Create connection pool
db_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host=os.getenv('POSTGRES_HOST'),
    database=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD')
)

# Use connections from pool
conn = db_pool.getconn()
try:
    # Do database work
    pass
finally:
    db_pool.putconn(conn)
```

### 4. Caching

```python
from functools import lru_cache
import redis

# In-memory cache for frequently accessed data
@lru_cache(maxsize=1000)
def get_domain_data(domain_id):
    # Expensive database query
    return query_domain(domain_id)

# Redis cache for distributed caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_with_cache(key, fetch_func, ttl=3600):
    # Check cache first
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    # Fetch and cache
    data = fetch_func()
    redis_client.setex(key, ttl, json.dumps(data))
    return data
```

---

## Error Handling Best Practices

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True
)
def api_call_with_retry(func, *args, **kwargs):
    """Retry API calls with exponential backoff"""
    try:
        return func(*args, **kwargs)
    except RateLimitError as e:
        logger.warning(f"Rate limit hit, backing off: {e}")
        raise
    except APIError as e:
        logger.error(f"API error: {e}")
        raise

def safe_extract(extractor_func, url, default=None):
    """Safely extract content with fallback"""
    try:
        return extractor_func(url)
    except Exception as e:
        logger.error(f"Extraction failed for {url}: {e}")
        return default

# Categorize errors for different handling
class CrawlerError(Exception):
    pass

class RateLimitError(CrawlerError):
    pass

class AuthenticationError(CrawlerError):
    pass

class ContentExtractionError(CrawlerError):
    pass
```

---

## Testing Strategy

```python
import pytest
from unittest.mock import Mock, patch

# Test individual crawlers
def test_youtube_search():
    crawler = YouTubeCrawler(api_key='test_key')
    with patch.object(crawler, 'youtube') as mock_youtube:
        mock_youtube.search().list().execute.return_value = {
            'items': [{'id': {'videoId': 'test123'}}]
        }
        results = crawler.search_videos('test query')
        assert len(results) > 0

# Test quality scorer
def test_quality_scorer():
    scorer = QualityScorer()
    content = {
        'text': 'Sample content',
        'platform': 'youtube',
        'views': 10000,
        'likes': 950
    }
    score = scorer.score_content(content, 'test query', 'TEST_DOMAIN')
    assert 0 <= score['total_score'] <= 100

# Integration test
def test_full_crawl_pipeline():
    coordinator = MasterCoordinator()
    results = coordinator.run_targeted_crawl(
        domain_id='TEST_DOMAIN',
        limit=5
    )
    assert results['success'] == True
    assert results['content_stored'] > 0
```

---

## Deployment Checklist

- [ ] Set up all API credentials
- [ ] Configure PostgreSQL database
- [ ] Initialize Chroma vector store
- [ ] Test each platform crawler independently
- [ ] Verify quality scoring algorithm
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Test with small domain subset
- [ ] Set up backup strategy
- [ ] Configure error alerting
- [ ] Document runbooks for common issues
- [ ] Schedule incremental updates

---

**Last Updated:** 2025-10-25
