# Apify YouTube Scraping Setup Guide

## Why Apify?

After testing BrightData proxies, we discovered:
- ❌ **Datacenter proxies**: Blocked by YouTube
- ❌ **Residential proxies**: Violate BrightData's policy (streaming media blocked)
- ✅ **Apify**: Specifically designed for YouTube scraping, handles all proxy/blocking issues

## Advantages

1. **Managed Infrastructure**: Apify handles all proxy rotation, IP blocks, rate limiting
2. **YouTube-Specific**: Pre-built YouTube scrapers that extract metadata + transcripts
3. **Cost-Effective**: ~$0.25 per 1000 videos (vs $15/GB for residential proxies)
4. **No Configuration**: No proxy setup, whitelist management, or SSL certificates
5. **Reliable**: Enterprise-grade service used by thousands of companies
6. **Free Tier**: $5 credit to start

## Setup Steps

### 1. Create Apify Account

1. Go to https://apify.com
2. Sign up (free tier includes $5 credit)
3. Verify your email

### 2. Get API Token

1. Go to https://console.apify.com/account/integrations
2. Copy your **API Token**
3. Add to `.env` file:
   ```bash
   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxx
   ```

### 3. Install Apify Client

```bash
pip install apify-client
```

Or update from requirements:
```bash
pip install -r requirements.txt
```

### 4. Test the Integration

```bash
python src/bot/crawlers/apify_youtube_crawler.py
```

Expected output:
```
✅ ApifyYouTubeCrawler initialized
🔍 Apify: Searching for 'piano tutorial for beginners'
✅ Apify: Found 3 videos, 3 with transcripts

1. Piano Tutorial for Absolute Beginners
   ID: xyz123
   Channel: Piano Lessons
   Views: 1,234,567
   Transcript: 5432 chars
   Preview: Welcome to this piano tutorial. Today we're going to learn...
```

## Integration with BotIndexer

The `ApifyYouTubeCrawler` is a drop-in replacement for `YouTubeCrawler`. It provides the same interface but uses Apify's managed scraping instead of direct API calls.

### Current Architecture

```
YouTubeCrawler:
├── search_videos() → Uses YouTube Data API v3 (with API key)
└── get_transcript() → Uses youtube-transcript-api (gets IP blocked)
```

### New Architecture with Apify

```
ApifyYouTubeCrawler:
└── search_videos() → Uses Apify YouTube Scraper
    ├── Returns metadata (title, views, etc.)
    └── Returns transcripts (managed scraping, no IP blocks)
```

### Option 1: Hybrid Approach (Recommended)

Use YouTube Data API for search (you have 10k quota), Apify only for transcripts:

```python
# Keep using YouTubeCrawler for search
videos = youtube_crawler.search_videos(query)

# Use Apify only for transcript extraction
for video in videos:
    apify_data = apify_crawler.get_video_details(video['video_id'])
    video['transcript'] = apify_data['transcript']
```

### Option 2: Full Apify

Use Apify for both search and transcripts:

```python
# Replace YouTubeCrawler entirely
videos = apify_crawler.search_videos(query, max_results=5)
# Videos already include transcripts!
```

## Pricing

### Free Tier
- $5 credit (enough for ~20,000 videos)
- No credit card required

### Pay-As-You-Go
- ~$0.25 per 1000 videos scraped
- Includes metadata + transcripts
- Much cheaper than residential proxies ($15/GB)

### Example Costs

| Videos  | Cost   | vs Residential Proxies |
| ------- | ------ | ---------------------- |
| 1,000   | $0.25  | $1.50 (6x cheaper)     |
| 10,000  | $2.50  | $15.00 (6x cheaper)    |
| 100,000 | $25.00 | $150.00 (6x cheaper)   |

## Apify Actors Used

### YouTube Scraper (`apify/youtube-scraper`)
- Search videos by keyword
- Extract metadata (title, views, likes, etc.)
- Download subtitles/transcripts
- Get comments (optional)
- **What we use it for**: Everything!

Documentation: https://apify.com/apify/youtube-scraper

## Next Steps

1. ✅ Sign up for Apify
2. ✅ Get API token
3. ✅ Add to `.env`
4. ✅ Install `apify-client`
5. ✅ Test `apify_youtube_crawler.py`
6. 🔄 Update `BotIndexer` to use `ApifyYouTubeCrawler`
7. 🔄 Run full pipeline test

## Comparison: BrightData vs Apify

| Feature          | BrightData Residential          | Apify                 |
| ---------------- | ------------------------------- | --------------------- |
| YouTube Access   | ❌ Blocked by policy             | ✅ Designed for it     |
| Setup Complexity | High (proxies, whitelist, SSL)  | Low (just API token)  |
| Cost             | $15/GB (~$1.50 per 1000 videos) | $0.25 per 1000 videos |
| IP Blocking      | Need to manage                  | Handled automatically |
| Transcripts      | Manual extraction               | Built-in              |
| Free Tier        | None                            | $5 credit             |
| **Winner**       | ❌                               | ✅ **Apify**           |

## Troubleshooting

### Error: "APIFY_API_TOKEN not set"
Add to `.env`:
```bash
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxx
```

### Error: "Insufficient credit"
- Check balance: https://console.apify.com/billing
- Add funds or use free tier credit

### Slow scraping
- Apify can take 30-60 seconds per search
- This is normal - they're managing proxies and avoiding blocks
- Much more reliable than managing your own proxies

### No transcripts returned
- Some videos don't have transcripts/subtitles
- Apify returns empty string if unavailable
- This is expected - filter in your quality scorer
