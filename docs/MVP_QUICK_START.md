# MVP Quick Start - Playlist-Based Indexing

## 🎯 Recommended Approach: Playlist Indexing

**Best for:** MVP where users bring their own curated learning playlists

```bash
# Index an entire YouTube playlist with quality filtering
python scripts/index_playlist_mvp.py \
  "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID" \
  --domain MUSIC \
  --subdomain GUITAR \
  --difficulty beginner \
  --min-quality 0.55
```

**Features:**
- ✅ Fetches all videos from playlist automatically
- ✅ Quality scoring filters low-quality content  
- ✅ Stores transcripts in GCS for instant future access
- ✅ Indexes high-quality videos to ChromaDB
- ✅ No re-scraping needed for review/approval

**What it does:**
1. Fetches playlist videos via Apify (with transcripts)
2. Scores each video with 5-factor quality algorithm
3. Stores ALL videos in GCS cache (permanent storage)
4. Indexes videos scoring ≥ 0.55 to ChromaDB
5. Logs everything to PostgreSQL

---

## 🚀 Alternative: Message Queue (Production-ready, async)

**Best for:** MVP demo, production deployment, scalability

### Step 1: Start Infrastructure

```bash
# Start RabbitMQ, workers, databases
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Step 2: Index Content

```bash
# Minimal (6-10 videos)
python scripts/minimal_index_queue.py

# Full MVP (40-50 videos)
python scripts/quick_mvp_index_queue.py
```

**Pros:**
- ✅ Async processing (submit and go)
- ✅ Scalable (add more workers)
- ✅ Fault tolerant (retry failed jobs)
- ✅ Production-ready

**Cons:**
- ⚠️ Requires Docker infrastructure
- ⚠️ Takes 20-30 min to process (but async)

### Step 3: Monitor Progress

```bash
# Option 1: RabbitMQ UI
open http://localhost:15672
# Login: autodidact / rabbitmq_password

# Option 2: Watch worker logs
docker-compose logs -f transcription_worker

# Option 3: Check ChromaDB count
python -c "from src.db_utils.chroma_client import *; print(get_chroma_client().get_collection('autodidact_ai_core_v2').count())"
```

---

## After Indexing (Both Options)

### Build Knowledge Graph

```bash
python scripts/build_knowledge_graph.py
```

### Test Curriculum Generation

```bash
# Test V2 (graph-enhanced)
python -m src.agents.question_agent_v2

# Compare V1 vs V2
python scripts/compare_agents.py
```

---

## Recommendation

**For MVP Demo:** Use **Option 2 (Message Queue)**

Why?
- Shows production-ready architecture
- Demonstrates async processing
- Proves scalability
- You already have the infrastructure set up!

**Quick Start:**
```bash
# 1. Start services (one time)
docker-compose up -d

# 2. Index content (5 min to submit, 20 min to process)
python scripts/quick_mvp_index_queue.py

# 3. While workers process, build the graph
python scripts/build_knowledge_graph.py

# 4. Test the system
python -m src.agents.question_agent_v2
```

---

## Troubleshooting

### "No documents in collection"
```bash
# Check if workers are running
docker-compose ps

# Check worker logs
docker-compose logs transcription_worker

# Check RabbitMQ queue
open http://localhost:15672
```

### "Graph is empty"
```bash
# Make sure ChromaDB has documents first
python -c "from src.db_utils.chroma_client import *; print(get_chroma_client().get_collection('autodidact_ai_core_v2').count())"

# Then rebuild graph
python scripts/build_knowledge_graph.py
```

### Workers not processing
```bash
# Restart workers
docker-compose restart transcription_worker quality_assessment_worker embedding_worker

# Check RabbitMQ connection
docker-compose logs rabbitmq
```
