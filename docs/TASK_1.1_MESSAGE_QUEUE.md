# Task 1.1: Message Queue Architecture

## Overview

This implementation decouples the Autodidact AI indexing pipeline using **RabbitMQ** as a message broker. The monolithic synchronous orchestrator has been replaced with an asynchronous, message-driven architecture consisting of:

1. **Producer (Orchestrator)**: Publishes video URLs to the message queue
2. **Workers**: Independent services that consume messages and perform specific tasks
3. **Message Queue**: RabbitMQ coordinates communication between components

## Architecture

### Message Flow

```
YouTube URL → Orchestrator → [tasks.video.new] → Transcription Worker
                                                         ↓
                                                 [tasks.video.transcribed]
                                                         ↓
                                                 Quality Assessment Worker
                                                         ↓
                                                 [tasks.video.validated]
                                                         ↓
                                                 Embedding Worker
                                                         ↓
                                                 [tasks.video.ingested]
```

### Components

#### 1. RabbitMQ Message Broker
- **Image**: `rabbitmq:3-management`
- **Ports**: 
  - 5672 (AMQP protocol)
  - 15672 (Management UI)
- **Credentials**: 
  - User: `autodidact`
  - Password: `rabbitmq_password`

#### 2. Indexing Orchestrator (Producer)
- **File**: `src/orchestrators/indexing_orchestrator_v2.py`
- **Role**: Publishes video URLs to `tasks.video.new` queue
- **Methods**:
  - `submit_video_for_indexing(url)`: Submit single video
  - `submit_batch(urls)`: Submit multiple videos

#### 3. Transcription Worker
- **File**: `src/workers/transcription_worker.py`
- **Consumes**: `tasks.video.new`
- **Publishes**: `tasks.video.transcribed`
- **Tasks**:
  - Fetches YouTube transcripts using configurable scraper
  - Supports multiple scraper backends: `default`, `apify`, or `api`
  - Extracts metadata
  - Logs video to PostgreSQL database
- **Scraper Options**:
  - `default`: youtube-transcript-api (free, simple)
  - `apify`: Apify YouTube Scraper (robust, handles geo-blocking, requires API token)
  - `api`: YouTube Data API v3 (comprehensive metadata, requires API key)

#### 4. Quality Assessment Worker
- **File**: `src/workers/quality_assessment_worker.py`
- **Consumes**: `tasks.video.transcribed`
- **Publishes**: `tasks.video.validated` (only if score ≥ 0.8)
- **Tasks**:
  - Validates content using ValidationAgent
  - Scores content quality (0.0 - 1.0)
  - Updates video status in database
  - Filters low-quality content

#### 5. Embedding Worker
- **File**: `src/workers/embedding_worker.py`
- **Consumes**: `tasks.video.validated`
- **Publishes**: `tasks.video.ingested`
- **Tasks**:
  - Generates embeddings using sentence-transformers
  - Stores chunks in ChromaDB
  - Updates final ingestion status

### Queue Definitions

| Queue Name                | Purpose                 | Producer                  | Consumer                       |
| ------------------------- | ----------------------- | ------------------------- | ------------------------------ |
| `tasks.video.new`         | New videos to process   | Orchestrator              | Transcription Worker           |
| `tasks.video.transcribed` | Videos with transcripts | Transcription Worker      | Quality Assessment Worker      |
| `tasks.video.validated`   | Approved videos         | Quality Assessment Worker | Embedding Worker               |
| `tasks.video.ingested`    | Completed videos        | Embedding Worker          | (Future: Analytics/Monitoring) |

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The new dependency `pika>=1.3.0` (RabbitMQ Python client) has been added.

### 2. Start Services

```bash
docker-compose up -d
```

This will start:
- ChromaDB
- Redis
- PostgreSQL
- **RabbitMQ** (new)
- **Transcription Worker** (new)
- **Quality Assessment Worker** (new)
- **Embedding Worker** (new)

### 3. Verify RabbitMQ

Access the RabbitMQ Management UI:
- URL: http://localhost:15672
- Username: `autodidact`
- Password: `rabbitmq_password`

You should see all queues listed under the "Queues" tab.

### 4. Configure YouTube Scraper (Optional)

By default, the system uses `youtube-transcript-api` (free, no API key needed). You can switch to other scrapers:

**Option 1: Environment Variable**
```bash
# Set in .env file or export
export YOUTUBE_SCRAPER=apify  # or 'default' or 'api'

# For Apify (robust, handles geo-blocking)
export APIFY_API_TOKEN=your_token_here

# For YouTube Data API v3 (comprehensive metadata)
export YOUTUBE_API_KEY=your_key_here
```

**Option 2: Per-Message Selection**
```python
from src.orchestrators.indexing_orchestrator_v2 import IndexingOrchestrator

orchestrator = IndexingOrchestrator()

# Submit with specific scraper
orchestrator.submit_video_for_indexing(
    "https://www.youtube.com/watch?v=example",
    additional_metadata={'scraper': 'apify'}  # or 'default' or 'api'
)
```

**Scraper Comparison:**

| Scraper   | Cost      | Pros                                     | Cons                            | Best For                     |
| --------- | --------- | ---------------------------------------- | ------------------------------- | ---------------------------- |
| `default` | Free      | Simple, no API key                       | May fail on geo-blocked videos  | Development, testing         |
| `apify`   | Paid      | Robust, handles blocking, reliable       | Requires API token, costs money | Production, high reliability |
| `api`     | Free tier | Comprehensive metadata, YouTube official | API quota limits (10k/day)      | Metadata-rich applications   |

## Usage

### Submit Videos for Indexing

#### Option 1: Using the Orchestrator Script

```python
from src.orchestrators.indexing_orchestrator_v2 import submit_video, submit_batch

# Submit a single video
submit_video("https://www.youtube.com/watch?v=vpn4qv4A1Aw")

# Submit multiple videos
urls = [
    "https://www.youtube.com/watch?v=video1",
    "https://www.youtube.com/watch?v=video2",
]
results = submit_batch(urls)
print(results)
```

#### Option 2: Direct Queue Publishing

```python
from src.workers.rabbitmq_utils import get_rabbitmq_connection, QUEUE_VIDEO_NEW
import json
import pika

connection = get_rabbitmq_connection()
channel = connection.channel()

message = {
    'youtube_url': 'https://www.youtube.com/watch?v=example',
    'additional_metadata': {},
}

channel.basic_publish(
    exchange='',
    routing_key=QUEUE_VIDEO_NEW,
    body=json.dumps(message),
    properties=pika.BasicProperties(delivery_mode=2)
)

connection.close()
```

## Monitoring

### View Queue Status

1. **RabbitMQ Management UI**: http://localhost:15672
   - Monitor queue lengths
   - View message rates
   - Track consumer connections

2. **Worker Logs**:
```bash
# View all workers
docker-compose logs -f transcription_worker quality_assessment_worker embedding_worker

# View specific worker
docker-compose logs -f transcription_worker
```

3. **Database Status**:
```sql
-- Check video processing status
SELECT status, COUNT(*) 
FROM videos 
GROUP BY status;
```

## Scaling

### Horizontal Scaling

To handle higher throughput, scale workers independently:

```bash
# Scale transcription workers to 3 instances
docker-compose up -d --scale transcription_worker=3

# Scale quality assessment workers to 2 instances
docker-compose up -d --scale quality_assessment_worker=2

# Scale embedding workers to 5 instances
docker-compose up -d --scale embedding_worker=5
```

RabbitMQ will automatically distribute messages across worker instances.

### Performance Tuning

#### Worker Concurrency

Edit `channel.basic_qos(prefetch_count=1)` in worker files:
- **prefetch_count=1**: Process one message at a time (safe, lower throughput)
- **prefetch_count=10**: Process up to 10 messages concurrently (higher throughput, more memory)

#### Queue Configuration

Queues are configured with:
- **TTL**: 24 hours (messages expire after 1 day)
- **Max Length**: 10,000 messages
- **Durability**: Enabled (survives broker restarts)

Adjust in `src/workers/rabbitmq_utils.py`:

```python
def declare_queue(channel, queue_name, durable=True):
    channel.queue_declare(
        queue=queue_name,
        durable=durable,
        arguments={
            'x-message-ttl': 86400000,  # Adjust TTL
            'x-max-length': 10000,       # Adjust max length
        }
    )
```

## Error Handling

### Retry Logic

Workers automatically retry failed messages:
- **Successful processing**: Message is acknowledged and removed from queue
- **Failed processing**: Message is rejected and requeued for retry

### Failed Message Handling

Currently, messages are retried indefinitely. For production, consider:

1. **Dead Letter Queues**: Move failed messages after N retries
2. **Max Retries**: Add retry counter in message metadata
3. **Alerts**: Notify team when errors exceed threshold

Example (add to worker):

```python
def callback(ch, method, properties, body):
    try:
        # Process message
        result = process_task(message_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error: {e}")
        # Reject without requeue after 3 attempts
        retry_count = properties.headers.get('x-retry-count', 0) if properties.headers else 0
        if retry_count >= 3:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            # Increment retry counter
            ch.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={'x-retry-count': retry_count + 1}
                )
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
```

## Benefits of This Architecture

### 1. **Resilience**
- Workers can fail and restart without losing messages
- Messages persist in queues during outages
- Independent failure domains

### 2. **Scalability**
- Scale each worker type independently based on bottlenecks
- Add workers without code changes
- Horizontal scaling across machines

### 3. **Flexibility**
- Easy to add new processing stages
- Can reorder or skip stages
- Support for different content types

### 4. **Observability**
- Monitor queue depths to identify bottlenecks
- Track processing rates per stage
- Centralized logging per worker type

### 5. **Development**
- Test individual workers in isolation
- Deploy workers independently
- Easier debugging with clear boundaries

## Migration from Old System

The original synchronous orchestrator (`indexing_orchestrator.py`) still exists but is deprecated. 

### Key Differences

| Aspect     | Old System            | New System                  |
| ---------- | --------------------- | --------------------------- |
| Processing | Synchronous           | Asynchronous                |
| Failure    | Entire pipeline fails | Only failed stage retries   |
| Scaling    | Vertical only         | Horizontal per stage        |
| Monitoring | Limited               | Queue metrics + worker logs |
| Deployment | Monolithic            | Microservices               |

### Backward Compatibility

To maintain compatibility:
1. Keep old orchestrator for legacy code
2. Gradually migrate API calls to use new orchestrator
3. Eventually deprecate old system

## Next Steps

### Phase 1 Completion Checklist
- [x] Add RabbitMQ to docker-compose.yml
- [x] Add pika to requirements.txt
- [x] Create worker directory structure
- [x] Implement Transcription Worker
- [x] Implement Quality Assessment Worker
- [x] Implement Embedding Worker
- [x] Refactor Orchestrator as Producer
- [x] Create Dockerfile for workers
- [x] Add workers to docker-compose.yml
- [x] Document new architecture

### Ready for Phase 1 Task 1.2
The system is now ready for **Kubernetes migration** (Task 1.2). The containerized workers can be easily converted to Kubernetes Deployments with minimal changes.

## Troubleshooting

### Workers Not Processing Messages

1. Check RabbitMQ connection:
```bash
docker-compose logs rabbitmq
```

2. Verify queues exist:
- Open http://localhost:15672
- Check "Queues" tab

3. Check worker logs:
```bash
docker-compose logs transcription_worker
```

### Messages Stuck in Queue

1. Check worker health:
```bash
docker-compose ps
```

2. Restart specific worker:
```bash
docker-compose restart transcription_worker
```

3. Check for errors in worker logs

### RabbitMQ Connection Issues

Environment variables must match in:
- docker-compose.yml (service definitions)
- Worker code (connection parameters)

Verify:
- RABBITMQ_HOST
- RABBITMQ_PORT
- RABBITMQ_USER
- RABBITMQ_PASSWORD

## Additional Resources

- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Pika Documentation](https://pika.readthedocs.io/)
- [Message Queue Patterns](https://www.enterpriseintegrationpatterns.com/patterns/messaging/)
