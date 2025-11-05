# Quick Start Guide: Message Queue Architecture

## Prerequisites

1. Docker and Docker Compose installed
2. Python 3.13+ installed
3. All dependencies in requirements.txt

## 5-Minute Setup

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
- ChromaDB (vector database)
- Redis (caching)
- PostgreSQL (metadata)
- **RabbitMQ (message broker)**
- **Transcription Worker**
- **Quality Assessment Worker**
- **Embedding Worker**

### Step 3: Verify Services

```bash
# Check all services are running
docker-compose ps

# Check RabbitMQ Management UI
open http://localhost:15672
# Login: autodidact / rabbitmq_password
```

### Step 3.5: (Optional) Configure YouTube Scraper

By default, the system uses the free `youtube-transcript-api`. For production or geo-blocked videos, use Apify:

```bash
# Option 1: Set environment variable
export YOUTUBE_SCRAPER=apify
export APIFY_API_TOKEN=your_token_here

# Option 2: Add to .env file
echo "YOUTUBE_SCRAPER=apify" >> .env
echo "APIFY_API_TOKEN=your_token_here" >> .env

# Restart workers to pick up new config
docker-compose restart transcription_worker
```

**Scraper Options:**
- `default` (free): Simple youtube-transcript-api
- `apify` (paid): Robust, handles geo-blocking
- `api` (free tier): YouTube Data API v3 with comprehensive metadata

### Step 4: Submit a Test Video

```bash
python tests/test_message_queue.py
```

Or in Python:

```python
from src.orchestrators.indexing_orchestrator_v2 import submit_video

submit_video("https://www.youtube.com/watch?v=vpn4qv4A1Aw")
```

### Step 5: Monitor Processing

#### Option 1: RabbitMQ UI
- Open http://localhost:15672
- Click "Queues" tab
- Watch messages move through queues

#### Option 2: Worker Logs
```bash
# All workers
docker-compose logs -f transcription_worker quality_assessment_worker embedding_worker

# Specific worker
docker-compose logs -f transcription_worker
```

#### Option 3: Database
```bash
# Connect to PostgreSQL
docker exec -it metadata_db psql -U autodidact -d video_metadata

# Check video status
SELECT video_id, title, status, score, created_at 
FROM videos 
ORDER BY created_at DESC 
LIMIT 10;
```

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Restart a Specific Worker
```bash
docker-compose restart transcription_worker
```

### Scale Workers
```bash
# Run 3 transcription workers
docker-compose up -d --scale transcription_worker=3

# Run 2 embedding workers
docker-compose up -d --scale embedding_worker=2
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f transcription_worker

# Last 100 lines
docker-compose logs --tail=100 quality_assessment_worker
```

### Clear Queues
```bash
# Connect to RabbitMQ container
docker exec -it autodidact_rabbitmq rabbitmqctl list_queues

# Purge a specific queue
docker exec -it autodidact_rabbitmq rabbitmqctl purge_queue tasks.video.new
```

## Pipeline Flow

```
1. Submit URL → Orchestrator
                    ↓
2. Orchestrator → [tasks.video.new] queue
                    ↓
3. Transcription Worker → fetches transcript → [tasks.video.transcribed]
                    ↓
4. Quality Worker → validates content → [tasks.video.validated] (if score ≥ 0.8)
                    ↓
5. Embedding Worker → creates embeddings → [tasks.video.ingested]
                    ↓
6. Done! Content in ChromaDB
```

## Troubleshooting

### Workers Not Starting
```bash
# Check logs for errors
docker-compose logs transcription_worker

# Rebuild worker image
docker-compose build transcription_worker
docker-compose up -d transcription_worker
```

### RabbitMQ Connection Failed
```bash
# Check RabbitMQ is running
docker-compose ps rabbitmq

# Check RabbitMQ logs
docker-compose logs rabbitmq

# Restart RabbitMQ
docker-compose restart rabbitmq
```

### Messages Not Being Processed
1. Verify workers are running: `docker-compose ps`
2. Check worker logs: `docker-compose logs -f transcription_worker`
3. Verify RabbitMQ connection: http://localhost:15672 → Connections tab
4. Check queue has messages: http://localhost:15672 → Queues tab

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres_db

# Test connection
docker exec -it metadata_db psql -U autodidact -d video_metadata -c "SELECT 1;"
```

## What's Different from Before?

| Before                  | After                            |
| ----------------------- | -------------------------------- |
| Synchronous processing  | Asynchronous message-based       |
| Single point of failure | Resilient with automatic retries |
| No parallelization      | Horizontal scaling per stage     |
| Hard to monitor         | Queue metrics + logs             |
| All-or-nothing          | Granular stage control           |

## Next Steps

- ✅ Task 1.1 Complete: Message Queue Architecture
- ⏭️  Task 1.2: Kubernetes Migration
- ⏭️  Task 1.3: CI/CD Pipeline

See `docs/TASK_1.1_MESSAGE_QUEUE.md` for full documentation.
