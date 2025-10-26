# Quick Start Implementation Guide

## Directory Structure

```
autodidact-ai-core/
├── data/
│   ├── bot/
│   │   └── architecture.md          # Bot architecture documentation
│   ├── strategy/
│   │   └── search_crawl_strategy.md # Search/crawl strategy
│   ├── prompts/
│   │   └── question_template_generation_prompt.md
│   ├── domains.json                 # 217 domains
│   └── domains_with_subdomains.json # 45 domains with subdomains
│
├── src/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── coordinator.py           # Master coordinator
│   │   ├── question_engine.py       # Question generation
│   │   ├── crawlers/
│   │   │   ├── __init__.py
│   │   │   ├── base_crawler.py
│   │   │   ├── youtube_crawler.py
│   │   │   ├── reddit_crawler.py
│   │   │   ├── quora_crawler.py
│   │   │   └── blog_crawler.py
│   │   ├── extractor.py             # Content extraction
│   │   ├── scorer.py                # Quality scoring
│   │   └── storage.py               # Storage manager
│   │
│   ├── db_utils/
│   │   ├── chroma_client.py         # Already exists
│   │   ├── llm_client.py            # Already exists
│   │   └── vector_store.py          # Already exists
│   │
│   └── config/
│       ├── config.yaml              # Configuration
│       └── question_templates.json  # Generated templates
│
├── .env                             # Environment variables
├── requirements.txt
└── README.md
```

## Step-by-Step Implementation

### Step 1: Generate Question Templates

```bash
# Use the prompt in data/prompts/question_template_generation_prompt.md
# to generate question_templates.json
python scripts/generate_templates.py
```

This will create `src/config/question_templates.json` with 100+ templates.

### Step 2: Set Up Environment

Create `.env` file:

```bash
# YouTube
YOUTUBE_API_KEY=your_api_key_here

# Google Custom Search (for blogs)
GOOGLE_CSE_API_KEY=your_api_key_here
GOOGLE_CSE_ID=your_search_engine_id

# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=AutodidactBot/1.0

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=autodidact
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Chroma
CHROMA_PERSIST_DIR=./chroma_data

# Quality Thresholds
MIN_QUALITY_SCORE=60
MAX_CONTENT_AGE_DAYS=730
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database

```bash
# Create PostgreSQL tables
python scripts/init_database.py

# Initialize Chroma vector store
python scripts/init_chroma.py
```

### Step 5: Test Individual Crawlers

```bash
# Test YouTube crawler
python -m src.bot.crawlers.youtube_crawler --test

# Test Reddit crawler
python -m src.bot.crawlers.reddit_crawler --test

# Test blog crawler
python -m src.bot.crawlers.blog_crawler --test
```

### Step 6: Run Small Test Crawl

```bash
# Crawl a single domain for testing
python -m src.bot.coordinator --domain MUSIC_PIANO --limit 10
```

### Step 7: Run Full Crawl

```bash
# Start full crawl (Phase 1: Tier 1 domains)
python -m src.bot.coordinator --phase 1 --background

# Monitor progress
python -m src.bot.monitor
```

## Next Steps After Setup

1. **Review collected content** in the database
2. **Adjust quality thresholds** based on results
3. **Refine question templates** for better coverage
4. **Scale to more domains** gradually
5. **Set up monitoring dashboard** for real-time tracking

## Monitoring Commands

```bash
# Check crawl status
python -m src.bot.status

# View quality metrics
python -m src.bot.metrics --domain MUSIC_PIANO

# Export content for domain
python -m src.bot.export --domain MUSIC_PIANO --format json
```

## Troubleshooting

### Issue: API Rate Limits
```bash
# Check current quota usage
python -m src.bot.quota_check

# Adjust rate limits in config
vim src/config/config.yaml
```

### Issue: Low Quality Scores
```bash
# Review quality distribution
python -m src.bot.quality_analysis

# Adjust scoring weights
vim src/bot/scorer.py
```

### Issue: Storage Issues
```bash
# Check database size
python -m src.bot.storage_stats

# Clean duplicate content
python -m src.bot.deduplicate
```

## Useful Scripts

All scripts should be created in `scripts/` directory:

- `generate_templates.py` - Generate question templates from prompt
- `init_database.py` - Initialize PostgreSQL schema
- `init_chroma.py` - Set up Chroma vector store
- `test_crawlers.py` - Test all platform crawlers
- `run_phase.py` - Run specific crawl phase
- `export_data.py` - Export content for analysis
- `quality_report.py` - Generate quality metrics report

## Configuration Files

### config.yaml Example

```yaml
crawler:
  max_concurrent_jobs: 10
  retry_attempts: 3
  retry_delay: 30
  checkpoint_interval: 100

platforms:
  youtube:
    quota_limit: 10000
    requests_per_batch: 50
    min_views: 1000
    min_like_ratio: 0.9
    
  reddit:
    requests_per_minute: 60
    min_score: 50
    max_posts_per_subreddit: 100
    
  quora:
    requests_per_minute: 30
    min_upvotes: 50
    max_answers: 10
    
  blogs:
    requests_per_day: 100
    min_word_count: 500
    timeout_seconds: 30

quality:
  min_total_score: 60
  weights:
    relevance: 0.30
    authority: 0.25
    engagement: 0.20
    freshness: 0.15
    completeness: 0.10

storage:
  batch_size: 100
  enable_deduplication: true
  similarity_threshold: 0.95
```

## Resource Estimation

### Time Estimates
- **Phase 1** (50 domains): 1-2 weeks
- **Phase 2** (167 domains): 4-6 weeks
- **Phase 3** (Depth): 3-4 weeks
- **Total Initial Crawl**: 8-12 weeks

### Storage Estimates
- **Per domain average**: 200 resources × 50KB = 10MB
- **217 domains**: ~2.2GB raw content
- **Vector embeddings**: ~500MB
- **Total**: ~3GB for complete dataset

### API Costs (Monthly)
- **YouTube API**: Free (10K quota/day sufficient)
- **Google CSE**: Free tier (100/day) or $5/1000 queries
- **Reddit API**: Free
- **Proxies** (for Quora): $50-100/month
- **Total**: $50-150/month (if scaling Quora heavily)

## References

- [Bot Architecture Documentation](./data/bot/architecture.md)
- [Search & Crawl Strategy](./data/strategy/search_crawl_strategy.md)
- [Question Template Prompt](./data/prompts/question_template_generation_prompt.md)
