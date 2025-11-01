# YouTube Scraper Integration Guide

## Overview

The message queue architecture now supports **three different YouTube transcript scrapers**, allowing you to choose the best option for your use case:

1. **Default** (`youtube-transcript-api`) - Free, simple
2. **Apify** - Robust, production-ready, handles geo-blocking
3. **YouTube API** - Comprehensive metadata, official API

## Architecture

The unified scraper interface is implemented in `src/scrapers/youtube_transcript_fetcher.py`, which provides a single `get_youtube_transcript()` function that routes to the appropriate backend based on configuration.

### Integration with Existing Crawlers

The implementation leverages your existing crawler infrastructure:

- **`src/bot/crawlers/apify_youtube_crawler.py`** - Apify integration
- **`src/bot/crawlers/youtube_crawler.py`** - YouTube Data API v3 integration
- **`src/scrapers/youtube_spider.py`** - Default youtube-transcript-api

## Scraper Comparison

| Feature                   | Default              | Apify                        | YouTube API        |
| ------------------------- | -------------------- | ---------------------------- | ------------------ |
| **Cost**                  | Free                 | ~$0.25/1000 videos           | Free (10k req/day) |
| **API Key Required**      | ❌ No                 | ✅ Yes                        | ✅ Yes              |
| **Geo-blocking Handling** | ❌ Limited            | ✅ Excellent                  | ⚠️ Moderate         |
| **Reliability**           | ⭐⭐⭐ Good             | ⭐⭐⭐⭐⭐ Excellent              | ⭐⭐⭐⭐ Very Good     |
| **Metadata Richness**     | ⭐⭐ Basic             | ⭐⭐⭐⭐ Rich                    | ⭐⭐⭐⭐⭐ Very Rich    |
| **Setup Complexity**      | Very Easy            | Easy                         | Moderate           |
| **Best For**              | Development, testing | Production, high reliability | Metadata-rich apps |

## Configuration

### Method 1: Environment Variable (Recommended)

Set the default scraper for all workers:

```bash
# In .env file
YOUTUBE_SCRAPER=apify

# For Apify
APIFY_API_TOKEN=your_apify_token_here

# For YouTube API
YOUTUBE_API_KEY=your_youtube_api_key_here
```

Then restart workers:
```bash
docker-compose restart transcription_worker
```

### Method 2: Per-Message Selection

Specify scraper when submitting videos:

```python
from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator

orchestrator = IndexingOrchestrator()

# Use Apify for this specific video
orchestrator.submit_video_for_indexing(
    "https://www.youtube.com/watch?v=example",
    additional_metadata={'scraper': 'apify'}
)

# Use default for another video
orchestrator.submit_video_for_indexing(
    "https://www.youtube.com/watch?v=example2",
    additional_metadata={'scraper': 'default'}
)
```

### Method 3: Docker Compose Environment

Set in `docker-compose.yml`:

```yaml
transcription_worker:
  environment:
    YOUTUBE_SCRAPER: apify
    APIFY_API_TOKEN: ${APIFY_API_TOKEN}
```

## Usage Examples

### Example 1: Testing All Scrapers

```python
from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript

url = "https://www.youtube.com/watch?v=vpn4qv4A1Aw"

# Test default
transcript, metadata = get_youtube_transcript(url, scraper='default')

# Test Apify (if token available)
transcript, metadata = get_youtube_transcript(url, scraper='apify')

# Test YouTube API (if key available)
transcript, metadata = get_youtube_transcript(url, scraper='api')
```

### Example 2: Batch with Mixed Scrapers

```python
from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator

orchestrator = IndexingOrchestrator()

# High-priority video: use Apify for reliability
orchestrator.submit_video_for_indexing(
    "https://www.youtube.com/watch?v=important",
    additional_metadata={'scraper': 'apify'}
)

# Regular videos: use default (free)
orchestrator.submit_video_for_indexing(
    "https://www.youtube.com/watch?v=regular",
    additional_metadata={'scraper': 'default'}
)

orchestrator.close()
```

### Example 3: Fallback Strategy

```python
def submit_with_fallback(url):
    """Submit video with fallback to different scrapers if one fails"""
    from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript
    
    scrapers = ['default', 'apify', 'api']
    
    for scraper in scrapers:
        try:
            transcript, metadata = get_youtube_transcript(url, scraper=scraper)
            if transcript and metadata:
                print(f"✅ Success with {scraper} scraper")
                return transcript, metadata
        except Exception as e:
            print(f"❌ {scraper} failed: {e}")
            continue
    
    print("❌ All scrapers failed")
    return None, None
```

## Getting API Credentials

### Apify API Token

1. Sign up at https://apify.com
2. Go to https://console.apify.com/account/integrations
3. Copy your API token
4. Set `APIFY_API_TOKEN=your_token` in `.env`

**Pricing:** Free tier includes $5 credit (~20,000 videos)

### YouTube Data API Key

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create credentials → API key
5. Set `YOUTUBE_API_KEY=your_key` in `.env`

**Quota:** 10,000 requests/day (free tier)

## Implementation Details

### Unified Interface

`src/scrapers/youtube_transcript_fetcher.py`:

```python
def get_youtube_transcript(url: str, scraper: Optional[str] = None):
    """
    Unified interface for all YouTube scrapers.
    
    Args:
        url: YouTube video URL
        scraper: 'default', 'apify', or 'api'
                 If None, uses YOUTUBE_SCRAPER env var
    
    Returns:
        (transcript_text, metadata_dict)
    """
    scraper = scraper or os.getenv('YOUTUBE_SCRAPER', 'default')
    
    if scraper == 'apify':
        return _fetch_with_apify(url)
    elif scraper == 'api':
        return _fetch_with_api_crawler(url)
    else:
        return _fetch_with_default(url)
```

### Worker Integration

`src/workers/transcription_worker.py`:

```python
def process_transcription(message_data: dict) -> dict:
    youtube_url = message_data.get('youtube_url')
    scraper = message_data.get('scraper')  # Optional override
    
    # Uses unified fetcher
    content, metadata = get_youtube_transcript(youtube_url, scraper=scraper)
    # ... rest of processing
```

## Monitoring Scraper Usage

### Check Which Scraper is Active

```python
import os
print(f"Current scraper: {os.getenv('YOUTUBE_SCRAPER', 'default')}")
```

### Monitor Scraper Performance

Add logging to track scraper usage:

```python
# In worker logs
"🎬 Transcribing video: {url} using scraper: {scraper}"
```

### RabbitMQ Message Inspection

View messages in RabbitMQ UI to see which scraper was requested:
- http://localhost:15672
- Queues → tasks.video.new → Get messages
- Check `scraper` field in message body

## Troubleshooting

### Issue: "APIFY_API_TOKEN not set"

**Solution:** Set the token in `.env`:
```bash
echo "APIFY_API_TOKEN=your_token_here" >> .env
docker-compose restart transcription_worker
```

### Issue: "YOUTUBE_API_KEY not set"

**Solution:** Get API key from Google Cloud Console and add to `.env`:
```bash
echo "YOUTUBE_API_KEY=your_key_here" >> .env
docker-compose restart transcription_worker
```

### Issue: Geo-blocked videos fail with default scraper

**Solution:** Switch to Apify scraper which handles geo-blocking:
```bash
export YOUTUBE_SCRAPER=apify
```

### Issue: YouTube API quota exceeded

**Solution:** Switch to Apify or default scraper:
```bash
export YOUTUBE_SCRAPER=apify  # or 'default'
```

## Production Recommendations

### For High-Reliability Production

```bash
# Use Apify for best reliability
YOUTUBE_SCRAPER=apify
APIFY_API_TOKEN=your_production_token
```

### For Cost-Conscious Production

```bash
# Use default, fallback to Apify for failures
YOUTUBE_SCRAPER=default
# Monitor error rates and upgrade to Apify if needed
```

### For Metadata-Rich Applications

```bash
# Use YouTube API for comprehensive metadata
YOUTUBE_SCRAPER=api
YOUTUBE_API_KEY=your_api_key
```

## Testing

Run the scraper selection example:

```bash
python examples/scraper_selection_example.py
```

Or test the unified fetcher directly:

```bash
python src/scrapers/youtube_transcript_fetcher.py
```

## Next Steps

1. ✅ Scraper selection implemented
2. ✅ Unified interface created
3. ✅ Documentation complete
4. 🔄 Monitor scraper performance in production
5. 🔄 Adjust scraper selection based on reliability metrics

## Files Modified/Created

- ✅ Created: `src/scrapers/youtube_transcript_fetcher.py`
- ✅ Modified: `src/workers/transcription_worker.py`
- ✅ Created: `examples/scraper_selection_example.py`
- ✅ Updated: `docs/TASK_1.1_MESSAGE_QUEUE.md`
- ✅ Updated: `docs/QUICKSTART_MESSAGE_QUEUE.md`
- ✅ Updated: `.env.example`
- ✅ Updated: `docs/TASK_1.1_IMPLEMENTATION_SUMMARY.md`
