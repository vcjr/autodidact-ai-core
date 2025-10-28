# Autodidact AI Core - Expert Integration Analysis Report

**Report Date:** Oct 2025  
**Purpose:** Comprehensive architectural analysis for AI agent context and system integration  
**Author:** Expert AI Engineering Analysis  
**Scope:** Full-stack analysis of existing RAG system + new bot crawler architecture

---

## Executive Summary

The Autodidact AI Core project consists of **two interconnected but architecturally distinct systems** that must work in harmony:

1. **Existing RAG System** (`src/`, `ARCHITECTURE.md`) - A LangChain/Gemini-powered curriculum generator that retrieves and synthesizes personalized learning paths from a vector database
2. **New Bot Crawler** (`data/bot/`, `data/strategy/`) - A multi-platform content discovery engine designed to populate the RAG system with educational resources from YouTube, Reddit, Quora, and blogs

### Critical Integration Insights

✅ **Strengths:**
- Both systems use ChromaDB as vector store (unified storage)
- Quality scoring (`helpfulness_score`) is present in both architectures
- Metadata-driven filtering aligns with RAG retrieval requirements
- Modular agent design allows independent development

⚠️ **Critical Gaps:**
- **Metadata schema mismatch**: Bot uses `domain_id`/`subdomain_id`, existing RAG uses `instrument_id`
- **Storage architecture conflict**: Bot proposes PostgreSQL + ChromaDB dual storage, existing RAG uses ChromaDB only
- **Embedding model divergence**: Existing system uses ChromaDB default (all-MiniLM-L6-v2), bot proposes sentence-transformers
- **Scale discrepancy**: Existing system has ~10 test documents, bot will generate millions of vectors (217 domains × 100+ subdomains × 100 questions × 100 sources = **200M+ potential vectors**)

🎯 **Recommended Integration Path:**
1. **Phase 1**: Unify metadata schema (extend `instrument_id` → `domain_id` with backward compatibility)
2. **Phase 2**: Standardize on single embedding model across both systems
3. **Phase 3**: Implement bot with ChromaDB-only storage (drop PostgreSQL requirement)
4. **Phase 4**: Add deduplication layer to prevent vector database bloat
5. **Phase 5**: Implement incremental indexing to scale from test data to production

---

## System Architecture Comparison Matrix

| **Dimension**         | **Original Design (ARCHITECTURE.md)** | **Current Implementation (src/)**                                 | **New Bot Design (data/bot/)**                                                                     | **Integration Recommendation**                                                           |
| --------------------- | ------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Orchestration**     | LangChain/LangGraph                   | Custom agents (LangChain-style)                                   | Master Coordinator (asyncio)                                                                       | **Keep both**: Bot for offline indexing, LangChain for online RAG                        |
| **Vector Store**      | Milvus or Weaviate (proposed)         | ChromaDB HTTP client                                              | ChromaDB + PostgreSQL                                                                              | **ChromaDB only**: Eliminate PostgreSQL to reduce complexity                             |
| **Embedding Model**   | Not specified                         | ChromaDB default (all-MiniLM-L6-v2)                               | sentence-transformers (proposed)                                                                   | **Standardize on sentence-transformers/all-mpnet-base-v2**: Better quality, 768d vs 384d |
| **LLM Provider**      | Not specified                         | Google Gemini (gemini-2.5-flash)                                  | Not specified (assumes Gemini)                                                                     | **Keep Gemini**: Already integrated and functional                                       |
| **Metadata Schema**   | Not defined                           | `instrument_id, difficulty, technique, helpfulness_score, source` | `domain_id, subdomain_id, platform, quality_score, author, engagement_metrics`                     | **Unified schema** (see Section 5)                                                       |
| **Crawling Strategy** | Scrapy + Playwright                   | Not implemented                                                   | YouTube API + PRAW + Selenium + newspaper3k                                                        | **Adopt bot design**: More robust than generic web scraping                              |
| **Quality Scoring**   | `helpfulness_score >= 0.8` filter     | Hardcoded threshold in ScopeAgent                                 | 5-factor algorithm (relevance 30%, authority 25%, engagement 20%, freshness 15%, completeness 10%) | **Use bot algorithm**: More sophisticated, configurable                                  |
| **Scale Target**      | 1M vectors (100×100×100)              | ~10 test vectors                                                  | 200M+ vectors (217×100×100×100)                                                                    | **Phased scaling**: Start with Tier 1 domains (see Section 8)                            |
| **Data Collection**   | Batch indexing                        | Not implemented                                                   | Scheduled crawls (daily/weekly)                                                                    | **Implement bot scheduler**: Airflow or Prefect                                          |

---

## Data Flow Integration Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          OFFLINE INDEXING PIPELINE                      │
│                           (New Bot System)                              │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │   YouTube    │  │    Reddit    │  │ Quora/Blogs  │
         │   Crawler    │  │   Crawler    │  │   Crawler    │
         └──────────────┘  └──────────────┘  └──────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                        ┌────────────────────────┐
                        │  Content Extractor     │
                        │  - HTML parsing        │
                        │  - Transcript extract  │
                        │  - Metadata enrichment │
                        └────────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │   Quality Scorer       │
                        │  - 5-factor scoring    │
                        │  - Filter < 0.8        │
                        │  - Tag skill level     │
                        └────────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │  Deduplication Layer   │ ◄─── NEW COMPONENT NEEDED
                        │  - Content hash check  │
                        │  - URL dedup           │
                        │  - Similarity merge    │
                        └────────────────────────┘
                                    │
                                    ▼
                ┌────────────────────────────────────────────┐
                │           ChromaDB Vector Store             │
                │  Collection: "autodidact_ai_core"           │
                │  - Content embeddings (768d)                │
                │  - Unified metadata schema                  │
                │  - ~200M vectors (full scale)               │
                └────────────────────────────────────────────┘
                                    │
                                    │ (Query-time retrieval)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         ONLINE RAG PIPELINE                             │
│                      (Existing src/ System)                             │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │ ScopeAgent   │  │QuestionAgent │  │ IntakeAgent  │
         │ - Query      │  │ - RAG        │  │ - Doc ingest │
         │   analysis   │  │   orchestr.  │  │   (manual)   │
         └──────────────┘  └──────────────┘  └──────────────┘
                    │               │
                    └───────────────┼───────────────┘
                                    ▼
                        ┌────────────────────────┐
                        │   Gemini API (LLM)     │
                        │  - Curriculum gen      │
                        │  - Source citations    │
                        │  - Personalization     │
                        └────────────────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │   User App   │
                            └──────────────┘
```

### Key Integration Points

1. **Storage Integration**: ChromaDB `autodidact_ai_core` collection is the **single source of truth**
2. **Quality Gate**: Bot's 5-factor scorer → `helpfulness_score` metadata → RAG's `>= 0.8` filter
3. **Metadata Bridge**: Bot's `domain_id`/`subdomain_id` must map to RAG's `instrument_id`
4. **Embedding Consistency**: Both systems MUST use same model or vectors won't align
5. **Deduplication**: NEW layer needed to prevent bot from creating duplicate vectors

---

## Metadata Schema Reconciliation

### Current Mismatch

**Existing RAG Metadata** (from `intake_agent.py`):
```python
{
    "source": str,              # URL or document identifier
    "text_length": int,         # Character count
    "instrument_id": str,       # e.g., "MUSIC_PIANO"
    "difficulty": str,          # "beginner" | "intermediate" | "advanced"
    "technique": str,           # e.g., "sweeping"
    "helpfulness_score": float  # 0.0 - 1.0
}
```

**Bot Proposed Metadata** (from `data/bot/architecture.md`):
```python
{
    "domain_id": str,           # e.g., "MUSIC"
    "subdomain_id": str,        # e.g., "PIANO"
    "platform": str,            # "youtube" | "reddit" | "quora" | "blog"
    "author": str,              # Content creator
    "engagement_metrics": dict, # {views, likes, comments, etc.}
    "quality_score": float,     # 0.0 - 1.0 (5-factor weighted)
    "content_type": str,        # "video" | "article" | "discussion"
    "skill_level": str,         # "beginner" | "intermediate" | "advanced"
    "tags": list,               # ["technique:sweeping", "style:metal"]
    "created_at": datetime,     # Content publication date
    "indexed_at": datetime      # Bot crawl timestamp
}
```

### Unified Schema (Recommended)

```python
# src/models/unified_metadata_schema.py
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

class UnifiedMetadata(BaseModel):
    """
    Universal metadata schema for both bot indexing and RAG retrieval.
    Backward compatible with existing RAG system.
    """
    
    # PRIMARY IDENTIFIERS (Bot + RAG)
    domain_id: str = Field(..., description="Top-level domain (e.g., MUSIC)")
    subdomain_id: Optional[str] = Field(None, description="Specific subdomain (e.g., PIANO)")
    
    # LEGACY COMPATIBILITY (RAG)
    instrument_id: str = Field(..., description="Alias: {domain_id}_{subdomain_id}")
    
    # CONTENT METADATA (Bot)
    source: str = Field(..., description="URL or document identifier")
    platform: str = Field(..., description="youtube | reddit | quora | blog")
    content_type: str = Field(..., description="video | article | discussion")
    author: Optional[str] = Field(None, description="Content creator")
    created_at: Optional[datetime] = Field(None, description="Publication date")
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # LEARNING METADATA (Bot + RAG)
    difficulty: str = Field(..., description="beginner | intermediate | advanced")
    skill_level: str = Field(..., description="Alias for difficulty")
    technique: Optional[str] = Field(None, description="Specific technique/concept")
    tags: List[str] = Field(default_factory=list, description="Freeform tags")
    
    # QUALITY METRICS (Bot + RAG)
    helpfulness_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality (RAG filter)")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Alias for helpfulness_score")
    quality_breakdown: Optional[Dict[str, float]] = Field(
        None, 
        description="5-factor: {relevance, authority, engagement, freshness, completeness}"
    )
    
    # ENGAGEMENT METRICS (Bot)
    engagement_metrics: Optional[Dict[str, int]] = Field(
        None,
        description="{views, likes, comments, shares, upvotes}"
    )
    
    # DOCUMENT STATS (RAG)
    text_length: int = Field(..., description="Character count")
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain_id": "MUSIC",
                "subdomain_id": "PIANO",
                "instrument_id": "MUSIC_PIANO",
                "source": "https://youtube.com/watch?v=abc123",
                "platform": "youtube",
                "content_type": "video",
                "author": "PianoTutorials",
                "created_at": "2024-01-15T10:00:00Z",
                "difficulty": "intermediate",
                "skill_level": "intermediate",
                "technique": "chord progressions",
                "tags": ["jazz", "improvisation"],
                "helpfulness_score": 0.87,
                "quality_score": 0.87,
                "quality_breakdown": {
                    "relevance": 0.92,
                    "authority": 0.85,
                    "engagement": 0.88,
                    "freshness": 0.75,
                    "completeness": 0.95
                },
                "engagement_metrics": {
                    "views": 15000,
                    "likes": 850,
                    "comments": 120
                },
                "text_length": 2500
            }
        }
```

### Migration Strategy

1. **Bot Implementation**: Use `UnifiedMetadata` from day 1
2. **RAG Updates**: 
   - Modify `IntakeAgent` to accept new schema
   - Add `instrument_id` auto-generation: `f"{domain_id}_{subdomain_id}"`
   - Update `ScopeAgent` to extract `domain_id` and `subdomain_id` (not just `instrument_id`)
3. **Backward Compatibility**: Keep `instrument_id` as alias for existing test data
4. **Data Migration**: Convert existing 10 test vectors to new schema

---

## Technology Stack Integration

### Current Stack Comparison

| **Component**            | **Existing RAG**          | **New Bot**                              | **Recommendation**                            |
| ------------------------ | ------------------------- | ---------------------------------------- | --------------------------------------------- |
| **Programming Language** | Python 3.x                | Python 3.x                               | ✅ Aligned                                     |
| **Web Framework**        | FastAPI (`api.py`)        | Not specified                            | ✅ Keep FastAPI for API layer                  |
| **Orchestration**        | LangChain (custom)        | asyncio + Celery (proposed)              | 🔄 Use Prefect for bot scheduling              |
| **Vector Store**         | ChromaDB (HTTP)           | ChromaDB (proposed)                      | ✅ Aligned                                     |
| **Relational DB**        | None                      | PostgreSQL (proposed)                    | ❌ Drop PostgreSQL - use ChromaDB metadata     |
| **Embedding Model**      | all-MiniLM-L6-v2 (384d)   | sentence-transformers (768d)             | 🔄 Upgrade to `all-mpnet-base-v2` (768d)       |
| **LLM**                  | Gemini (gemini-2.5-flash) | Not specified                            | ✅ Use Gemini for bot's NLP tasks too          |
| **Crawling**             | Not implemented           | YouTube API, PRAW, Selenium, newspaper3k | ✅ Adopt bot design                            |
| **Caching**              | None                      | Redis (proposed)                         | ✅ Add Redis for rate limiting + deduplication |
| **Monitoring**           | Basic logging             | Prometheus + Grafana (proposed)          | ✅ Implement for production                    |

### Recommended Unified Stack

```yaml
# config/tech_stack.yml

language:
  python: "3.11+"

orchestration:
  rag_runtime: "langchain"         # Online query processing
  bot_scheduler: "prefect"          # Offline batch crawling
  task_queue: "celery + redis"      # Distributed task execution

storage:
  vector_db:
    provider: "chromadb"
    host: "localhost:8000"          # Docker container
    collection: "autodidact_ai_core"
    embedding_dimension: 768
  
  cache:
    provider: "redis"
    host: "localhost:6379"
    use_for:
      - "rate_limiting"
      - "deduplication_hash"
      - "crawl_checkpoints"

embeddings:
  model: "sentence-transformers/all-mpnet-base-v2"
  dimension: 768
  normalize: true

llm:
  provider: "google_gemini"
  model: "gemini-2.5-flash"
  fallback: "gemini-flash-latest"
  temperature: 0.7
  max_tokens: 2048

crawling:
  youtube:
    api_key: "${YOUTUBE_API_KEY}"
    quota_limit: 10000  # requests/day
  reddit:
    client_id: "${REDDIT_CLIENT_ID}"
    client_secret: "${REDDIT_CLIENT_SECRET}"
    user_agent: "AutodidactBot/1.0"
  quora:
    method: "selenium"  # No official API
    headless: true
  blogs:
    search_api: "google_custom_search"
    api_key: "${GOOGLE_CSE_KEY}"
    cx: "${GOOGLE_CSE_ID}"

monitoring:
  logs:
    level: "INFO"
    format: "json"
    output: "stdout + file"
  metrics:
    provider: "prometheus"
    port: 9090
  visualization:
    provider: "grafana"
    port: 3000
```

---

## Critical Integration Gaps & Solutions

### Gap 1: Embedding Model Mismatch

**Problem**: 
- Existing RAG uses ChromaDB default (`all-MiniLM-L6-v2`, 384 dimensions)
- Bot proposes `sentence-transformers` (typically `all-mpnet-base-v2`, 768 dimensions)
- **Cannot mix embedding dimensions in same ChromaDB collection**

**Impact**: 
- RAG queries will fail if bot adds 768d vectors to collection expecting 384d
- Must re-embed ALL existing content if switching models

**Solution**:
```python
# Option A: Standardize on all-mpnet-base-v2 (RECOMMENDED)
# - Higher quality (768d vs 384d)
# - Re-embed ~10 existing test vectors (trivial cost)
# - Use for all future bot crawling

from sentence_transformers import SentenceTransformer

class UnifiedEmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-mpnet-base-v2')
    
    def embed_text(self, text: str) -> list[float]:
        """Generate 768-dimensional embedding"""
        return self.model.encode(text, normalize_embeddings=True).tolist()

# Update src/db_utils/chroma_client.py
def get_chroma_client():
    return chromadb.HttpClient(
        host=os.getenv("CHROMA_HOST", "localhost"),
        port=int(os.getenv("CHROMA_PORT", 8000)),
        settings=Settings(
            # Force explicit embedding function
            chroma_api_impl="rest",
            anonymized_telemetry=False
        )
    )

# Update collection creation
collection = client.get_or_create_collection(
    name="autodidact_ai_core",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-mpnet-base-v2"
    ),
    metadata={"dimension": 768}
)
```

**Migration Steps**:
1. Create new collection `autodidact_ai_core_v2` with 768d embeddings
2. Re-embed existing 10 test documents with `all-mpnet-base-v2`
3. Update all agents to use new collection
4. Delete old collection once verified
5. Bot uses same embedding function from day 1

---

### Gap 2: Metadata Schema Incompatibility

**Problem**:
- RAG agents expect `instrument_id`, bot generates `domain_id + subdomain_id`
- Bot has rich metadata (platform, author, engagement) that RAG doesn't use
- No clear mapping between 217 domains and existing `instrument_id` values

**Impact**:
- ScopeAgent will fail to extract filters from bot-indexed content
- RAG queries won't retrieve bot-crawled resources

**Solution**:
Implement `UnifiedMetadata` schema (see Section 5) with these key changes:

```python
# src/agents/scope_agent.py - UPDATE
class ScopeAgent:
    def generate_scope_filter(self, user_query: str) -> Dict[str, Any]:
        # ... existing Gemini call ...
        
        # NEW: Extract both legacy and new identifiers
        scope_data = {
            "domain_id": scope_json.get("domain_id"),  # NEW
            "subdomain_id": scope_json.get("subdomain_id"),  # NEW
            "instrument_id": scope_json.get("instrument_id"),  # LEGACY
            "difficulty": scope_json.get("difficulty")
        }
        
        # Auto-generate instrument_id from domain+subdomain if missing
        if not scope_data["instrument_id"] and scope_data["domain_id"]:
            if scope_data["subdomain_id"]:
                scope_data["instrument_id"] = (
                    f"{scope_data['domain_id']}_{scope_data['subdomain_id']}"
                )
            else:
                scope_data["instrument_id"] = scope_data["domain_id"]
        
        return self.build_chroma_where_filter(scope_data)
    
    def build_chroma_where_filter(self, scope_data: Dict[str, Any]) -> Dict[str, Any]:
        where_filter = {"$and": []}
        
        # Support both old and new schema
        if scope_data.get("instrument_id"):
            where_filter["$and"].append({"instrument_id": scope_data["instrument_id"]})
        elif scope_data.get("domain_id"):
            # New schema: filter by domain_id (and optionally subdomain_id)
            where_filter["$and"].append({"domain_id": scope_data["domain_id"]})
            if scope_data.get("subdomain_id"):
                where_filter["$and"].append({"subdomain_id": scope_data["subdomain_id"]})
        
        # ... rest of filters ...
```

---

### Gap 3: No Deduplication Strategy

**Problem**:
- Bot will crawl same content from multiple platforms (e.g., tutorial appears on YouTube AND blog)
- Periodic re-crawls will create duplicate vectors
- No mechanism to detect near-duplicate content

**Impact**:
- Vector database bloat (2-5x unnecessary growth)
- Reduced retrieval quality (duplicate results)
- Wasted storage and compute

**Solution**:
Implement multi-layer deduplication:

```python
# src/db_utils/deduplication.py - NEW FILE
import hashlib
from typing import Optional
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np

class DeduplicationService:
    def __init__(self, chroma_client, redis_client):
        self.chroma = chroma_client
        self.redis = redis_client
        self.similarity_model = SentenceTransformer('all-mpnet-base-v2')
        self.similarity_threshold = 0.95  # 95% similar = duplicate
    
    def is_duplicate(self, content: str, url: str, metadata: dict) -> tuple[bool, Optional[str]]:
        """
        Check if content is duplicate using 3-tier strategy:
        1. URL hash (exact match)
        2. Content hash (exact text match)
        3. Semantic similarity (near-duplicate detection)
        
        Returns: (is_duplicate, existing_doc_id)
        """
        # Tier 1: URL deduplication (fastest)
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        if self.redis.exists(f"url:{url_hash}"):
            existing_id = self.redis.get(f"url:{url_hash}")
            return True, existing_id
        
        # Tier 2: Content hash (fast)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if self.redis.exists(f"content:{content_hash}"):
            existing_id = self.redis.get(f"content:{content_hash}")
            return True, existing_id
        
        # Tier 3: Semantic similarity (slower, only for new content)
        return self._check_semantic_duplicate(content, metadata)
    
    def _check_semantic_duplicate(
        self, content: str, metadata: dict
    ) -> tuple[bool, Optional[str]]:
        """Use vector similarity to detect near-duplicates"""
        # Query ChromaDB for similar content in same domain
        embedding = self.similarity_model.encode(content, normalize_embeddings=True)
        
        results = self.chroma.query(
            query_embeddings=[embedding.tolist()],
            n_results=1,
            where={
                "domain_id": metadata["domain_id"],
                "subdomain_id": metadata.get("subdomain_id")
            }
        )
        
        if results['distances'][0] and results['distances'][0][0] < (1 - self.similarity_threshold):
            # Found near-duplicate (cosine similarity > 0.95)
            existing_id = results['ids'][0][0]
            return True, existing_id
        
        return False, None
    
    def register_content(self, content: str, url: str, doc_id: str):
        """Register content hashes after successful indexing"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Store in Redis with 90-day expiration
        self.redis.setex(f"url:{url_hash}", 90*24*60*60, doc_id)
        self.redis.setex(f"content:{content_hash}", 90*24*60*60, doc_id)
```

**Integration into bot**:
```python
# data/bot/storage_manager.py - UPDATED
class StorageManager:
    def __init__(self):
        self.chroma = get_chroma_client()
        self.redis = get_redis_client()
        self.dedup = DeduplicationService(self.chroma, self.redis)
    
    def store_content(self, content: str, metadata: dict):
        # Check for duplicates BEFORE indexing
        is_dup, existing_id = self.dedup.is_duplicate(
            content, 
            metadata['source'], 
            metadata
        )
        
        if is_dup:
            logger.info(f"Skipping duplicate content: {metadata['source']}")
            # Optionally update metadata (e.g., engagement metrics)
            self._update_engagement_metrics(existing_id, metadata)
            return existing_id
        
        # Add to ChromaDB
        doc_id = str(uuid.uuid4())
        self.chroma.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
        
        # Register hashes
        self.dedup.register_content(content, metadata['source'], doc_id)
        return doc_id
```

---

### Gap 4: Scale Management (200M+ Vectors)

**Problem**:
- Current system: ~10 test vectors
- Bot target: 217 domains × 100 subdomains × 100 questions × 100 sources = **217M vectors**
- ChromaDB performance degrades beyond 10M vectors without proper indexing

**Impact**:
- Query latency explosion (seconds → minutes)
- Memory exhaustion (768d × 217M = ~660GB for vectors alone)
- Cost explosion (cloud hosting, API quotas)

**Solution**:
Implement phased scaling with collection sharding:

```python
# src/db_utils/collection_manager.py - NEW FILE
class CollectionManager:
    """
    Manages ChromaDB collections with domain-based sharding.
    Prevents single collection from exceeding 10M vectors.
    """
    
    SHARD_STRATEGIES = {
        "single": lambda domain_id, subdomain_id: "autodidact_ai_core",
        "by_domain": lambda domain_id, subdomain_id: f"autodidact_{domain_id.lower()}",
        "by_tier": lambda domain_id, subdomain_id: f"autodidact_tier{self._get_tier(domain_id)}"
    }
    
    def __init__(self, strategy="by_tier"):
        self.client = get_chroma_client()
        self.strategy = strategy
    
    def get_collection_name(self, domain_id: str, subdomain_id: str = None) -> str:
        """Determine collection name based on sharding strategy"""
        return self.SHARD_STRATEGIES[self.strategy](domain_id, subdomain_id)
    
    def _get_tier(self, domain_id: str) -> int:
        """
        Assign domains to tiers for balanced sharding:
        - Tier 1: High-priority domains (MUSIC, CODING, LANGUAGES) - ~30 domains
        - Tier 2: Medium-priority (BUSINESS, ARTS, SCIENCES) - ~80 domains
        - Tier 3: Low-priority (NICHE domains) - ~107 domains
        """
        tier1 = ["MUSIC", "CODING_SOFTWARE", "LANGUAGES", "MATHEMATICS"]
        tier2 = ["BUSINESS", "ARTS", "SCIENCES", "ENGINEERING"]
        
        if domain_id in tier1:
            return 1
        elif any(domain_id.startswith(t) for t in tier2):
            return 2
        return 3
    
    def query_across_collections(
        self, query_embedding: list, metadata_filter: dict, n_results: int = 5
    ) -> list:
        """
        Query multiple collections and merge results.
        Used when query doesn't specify domain (broad search).
        """
        domain_id = metadata_filter.get("domain_id")
        
        if domain_id:
            # Targeted query: single collection
            collection_name = self.get_collection_name(domain_id)
            return self._query_collection(collection_name, query_embedding, metadata_filter, n_results)
        
        # Broad query: search all collections, merge top results
        all_results = []
        for tier in [1, 2, 3]:
            collection_name = f"autodidact_tier{tier}"
            results = self._query_collection(
                collection_name, query_embedding, metadata_filter, n_results
            )
            all_results.extend(results)
        
        # Re-rank by distance and return top N
        all_results.sort(key=lambda x: x['distance'])
        return all_results[:n_results]
```

**Phased Rollout Plan**:

| **Phase**           | **Timeline** | **Domains**                                  | **Est. Vectors** | **Collection Strategy**               |
| ------------------- | ------------ | -------------------------------------------- | ---------------- | ------------------------------------- |
| **Phase 0**: Test   | Week 1       | 5 domains (MUSIC_PIANO, CODING_PYTHON, etc.) | 50K              | Single collection                     |
| **Phase 1**: Tier 1 | Weeks 2-4    | 30 high-priority domains                     | 3M               | Single collection                     |
| **Phase 2**: Tier 2 | Weeks 5-8    | 80 medium-priority domains                   | 8M               | Single collection (approaching limit) |
| **Phase 3**: Tier 3 | Weeks 9-12   | All 217 domains                              | 20M+             | **Shard by tier** (3 collections)     |
| **Phase 4**: Depth  | Months 4-6   | Increase sources per question (100 → 200)    | 40M+             | Shard by domain or tier               |

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Objective**: Unify metadata schema and embedding model

**Tasks**:
1. Create `src/models/unified_metadata_schema.py`
   - Implement `UnifiedMetadata` Pydantic model
   - Add validation rules
   - Create migration utilities

2. Upgrade ChromaDB embedding model
   - Install `sentence-transformers`
   - Create new collection `autodidact_ai_core_v2` with `all-mpnet-base-v2`
   - Re-embed existing 10 test documents
   - Update `src/db_utils/chroma_client.py`

3. Update existing agents
   - Modify `IntakeAgent` to accept `UnifiedMetadata`
   - Update `ScopeAgent` to extract `domain_id` and `subdomain_id`
   - Test with existing queries

4. Add deduplication infrastructure
   - Set up Redis (Docker Compose)
   - Create `src/db_utils/deduplication.py`
   - Implement 3-tier dedup strategy

**Validation**:
- Run existing RAG queries against re-embedded content
- Verify same or better retrieval quality
- Test deduplication with synthetic duplicates

---

### Phase 2: Bot Development (Weeks 3-6)

**Objective**: Implement core bot crawler with YouTube + Reddit

**Tasks**:
1. Create bot directory structure
   ```
   src/bot/
   ├── coordinator.py          # MasterCoordinator
   ├── question_engine.py      # Template processor
   ├── crawlers/
   │   ├── base_crawler.py
   │   ├── youtube_crawler.py
   │   ├── reddit_crawler.py
   │   ├── quora_crawler.py    # (Phase 3)
   │   └── blog_crawler.py     # (Phase 3)
   ├── extractor.py            # Content extraction
   ├── quality_scorer.py       # 5-factor scoring
   └── storage_manager.py      # ChromaDB integration
   ```

2. Implement question template system
   - Load `data/prompts/question_template_generation_prompt.md`
   - Generate 100+ templates using Gemini
   - Save to `data/question_templates.json`
   - Implement placeholder substitution

3. Build YouTube crawler
   - YouTube Data API v3 integration
   - Transcript extraction (youtube-transcript-api)
   - Metadata enrichment (views, likes, channel authority)
   - Rate limiting (10K requests/day quota)

4. Build Reddit crawler
   - PRAW integration
   - Subreddit discovery (search for domain-specific communities)
   - Post + comment extraction
   - Karma-based quality filtering

5. Implement quality scorer
   - 5-factor algorithm (relevance, authority, engagement, freshness, completeness)
   - Weighted scoring: helpfulness_score = 0.3×R + 0.25×A + 0.2×E + 0.15×F + 0.1×C
   - Threshold: only index content with score >= 0.8

6. Integrate with ChromaDB
   - Use `StorageManager` with deduplication
   - Store with `UnifiedMetadata` schema
   - Test with 5 Tier 1 domains (MUSIC_PIANO, CODING_PYTHON, LANGUAGES_SPANISH, MATH_CALCULUS, BUSINESS_MARKETING)

**Validation**:
- Crawl 5 test domains → expect ~10K vectors
- Verify deduplication (run crawler twice, no duplicates)
- Test RAG retrieval with bot-indexed content

---

### Phase 3: Scale Testing (Weeks 7-10)

**Objective**: Index Tier 1 domains (30 domains, ~3M vectors)

**Tasks**:
1. Implement Prefect scheduler
   - Daily crawl jobs for new content
   - Weekly re-crawl for engagement updates
   - Checkpoint/resume for long crawls

2. Add Quora + Blog crawlers
   - Quora: Selenium-based extraction
   - Blogs: Google Custom Search API + newspaper3k

3. Expand to Tier 1 domains
   - Crawl all 30 high-priority domains
   - Monitor ChromaDB performance (query latency, memory usage)
   - Adjust quality threshold if needed (e.g., 0.85 instead of 0.8)

4. Implement collection sharding
   - Create `CollectionManager` with "by_tier" strategy
   - Migrate Tier 1 content to `autodidact_tier1` collection
   - Update RAG agents to query correct collection

**Validation**:
- Achieve 3M vectors in Tier 1 collection
- RAG query latency < 500ms (p95)
- Deduplication rate ~15-25% (expected overlap between platforms)

---

### Phase 4: Production Rollout (Weeks 11-16)

**Objective**: Index all 217 domains, implement monitoring

**Tasks**:
1. Expand to Tier 2 and Tier 3 domains
   - Crawl remaining 187 domains
   - Shard across `autodidact_tier1`, `autodidact_tier2`, `autodidact_tier3`
   - Target: 20M+ vectors total

2. Implement monitoring stack
   - Prometheus metrics (crawl rate, error rate, vector count)
   - Grafana dashboards
   - Alerts for quota limits, API failures

3. Optimize performance
   - Batch ChromaDB inserts (1000 docs/batch)
   - Parallel crawler execution (asyncio)
   - Cache frequently accessed domain data in Redis

4. Build API endpoints for manual control
   - `/api/bot/crawl/{domain_id}` - Trigger targeted crawl
   - `/api/bot/status` - Get crawl progress
   - `/api/bot/quality/{threshold}` - Adjust quality threshold

**Validation**:
- 20M+ vectors indexed
- RAG query latency < 1s across all collections
- Bot uptime > 99% (scheduled downtime allowed)

---

### Phase 5: Continuous Improvement (Ongoing)

**Objective**: Maintain content freshness, improve quality

**Tasks**:
1. Implement incremental indexing
   - Daily crawls for new content (last 24 hours)
   - Weekly engagement metric updates
   - Monthly full re-crawl of Tier 1 domains

2. Add feedback loop
   - Track which resources users engage with (via RAG API)
   - Boost `helpfulness_score` for frequently retrieved content
   - Deprecate low-engagement content (score decay over time)

3. Expand question templates
   - Generate domain-specific templates (e.g., music theory vs coding interviews)
   - A/B test template effectiveness (retrieval quality)

4. Explore advanced features
   - Multi-modal embeddings (text + video frames)
   - Cross-domain recommendations
   - Personalized curriculum adaptation

---

## Risk Analysis & Mitigation

### Risk 1: API Quota Exhaustion

**Likelihood**: High  
**Impact**: Critical (bot stops crawling)

**Scenarios**:
- YouTube: 10K requests/day limit (easily hit with 217 domains)
- Reddit: 60 requests/minute (rate limiting)
- Google Custom Search: $5 per 1000 queries (cost explosion)

**Mitigation**:
1. **Implement intelligent caching**:
   ```python
   # Cache search results for 7 days
   cache_key = f"search:{platform}:{query_hash}"
   if cached := redis.get(cache_key):
       return json.loads(cached)
   
   results = api.search(query)
   redis.setex(cache_key, 7*24*60*60, json.dumps(results))
   ```

2. **Prioritize domains**:
   - Tier 1 domains get daily crawls (high quota allocation)
   - Tier 2 domains get weekly crawls
   - Tier 3 domains get monthly crawls

3. **Use free alternatives where possible**:
   - YouTube: Supplement API with RSS feeds (no quota)
   - Blogs: Combine Google CSE with open-source search (DuckDuckGo scraping)

4. **Implement quota monitoring**:
   ```python
   class QuotaManager:
       def check_quota(self, platform: str) -> bool:
           remaining = self.get_remaining_quota(platform)
           threshold = self.get_daily_budget(platform) * 0.1  # 10% buffer
           return remaining > threshold
   ```

---

### Risk 2: Content Quality Degradation

**Likelihood**: Medium  
**Impact**: High (RAG generates poor curricula)

**Scenarios**:
- Bot indexes low-quality content (spam, outdated, inaccurate)
- Quality score algorithm has false positives
- Over-indexing of beginner content (drowns out advanced resources)

**Mitigation**:
1. **Human-in-the-loop validation** (Phase 1):
   - Manually review first 1000 indexed items
   - Adjust quality thresholds based on false positive rate
   - Create blocklist for known spam domains

2. **Multi-tier quality filtering**:
   ```python
   # Tier 1: Platform-specific heuristics
   if platform == "youtube":
       if views < 1000 or likes/views < 0.01:
           return False  # Low engagement
   
   # Tier 2: 5-factor scoring
   if quality_score < 0.8:
       return False
   
   # Tier 3: LLM-based relevance check (sample 10%)
   if random() < 0.1:
       relevance = llm_check_relevance(content, domain_id)
       if relevance < 0.7:
           flag_for_review(content)
   ```

3. **Difficulty distribution balancing**:
   - Track difficulty distribution per domain
   - If beginner content > 60%, boost intermediate/advanced in next crawl
   - Adjust question templates to target underrepresented levels

---

### Risk 3: ChromaDB Performance Bottleneck

**Likelihood**: High  
**Impact**: Critical (RAG queries timeout)

**Scenarios**:
- Single collection exceeds 10M vectors → query latency spikes
- Memory exhaustion on server (768d × 20M vectors = ~60GB)
- Concurrent queries overwhelm ChromaDB HTTP server

**Mitigation**:
1. **Collection sharding** (see Gap 4):
   - Shard by tier or domain to keep collections < 10M vectors
   - Implement smart query routing

2. **Indexing optimization**:
   ```python
   # Use HNSW index for faster similarity search
   collection = client.create_collection(
       name="autodidact_tier1",
       metadata={
           "hnsw:space": "cosine",
           "hnsw:construction_ef": 200,  # Higher = better recall, slower build
           "hnsw:search_ef": 100         # Higher = better recall, slower search
       }
   )
   ```

3. **Caching hot queries**:
   - Cache top 1000 most common queries in Redis
   - Serve from cache if query hash matches
   - TTL = 1 hour

4. **Consider migration to Qdrant or Weaviate** (Phase 5):
   - Better performance at scale (20M+ vectors)
   - Built-in sharding and replication
   - Migration path: export ChromaDB → import to Qdrant

---

### Risk 4: Metadata Drift

**Likelihood**: Medium  
**Impact**: Medium (bot and RAG schemas diverge over time)

**Scenarios**:
- Bot developers add new metadata fields without updating RAG agents
- RAG agents expect fields that bot doesn't populate
- Schema versioning not enforced

**Mitigation**:
1. **Enforce schema with Pydantic** (see Section 5):
   - All metadata MUST pass `UnifiedMetadata.model_validate()`
   - Automated tests check schema compatibility

2. **Schema versioning**:
   ```python
   class UnifiedMetadata(BaseModel):
       schema_version: str = "1.0.0"  # Semver
       
       @validator("schema_version")
       def check_version(cls, v):
           if v not in SUPPORTED_VERSIONS:
               raise ValueError(f"Unsupported schema version: {v}")
           return v
   ```

3. **Backward compatibility contract**:
   - NEVER remove required fields (only deprecate)
   - New fields MUST be optional with defaults
   - Document migration path for breaking changes

---

## Recommended Next Steps (Priority Order)

### Week 1: Foundation Setup

1. **Create unified metadata schema** (8 hours)
   - [ ] Implement `src/models/unified_metadata_schema.py`
   - [ ] Write unit tests for validation
   - [ ] Document all fields with examples

2. **Upgrade embedding model** (4 hours)
   - [ ] Install `sentence-transformers`
   - [ ] Create new ChromaDB collection with `all-mpnet-base-v2`
   - [ ] Re-embed existing test data
   - [ ] Verify retrieval quality unchanged/improved

3. **Update existing agents** (6 hours)
   - [ ] Modify `IntakeAgent` for new schema
   - [ ] Update `ScopeAgent` to extract `domain_id`/`subdomain_id`
   - [ ] Add backward compatibility for `instrument_id`
   - [ ] Run integration tests

### Week 2: Deduplication & Infrastructure

1. **Set up Redis** (2 hours)
   - [ ] Add Redis to `docker-compose.yml`
   - [ ] Create `src/db_utils/redis_client.py`
   - [ ] Write connection tests

2. **Implement deduplication** (10 hours)
   - [ ] Create `src/db_utils/deduplication.py`
   - [ ] Implement 3-tier strategy (URL, content hash, semantic)
   - [ ] Write unit tests with synthetic duplicates
   - [ ] Integration test with ChromaDB

3. **Bot architecture skeleton** (6 hours)
   - [ ] Create `src/bot/` directory structure
   - [ ] Implement `BaseCrawler` interface
   - [ ] Create `MasterCoordinator` scaffold
   - [ ] Set up logging and error handling

### Week 3-4: YouTube Crawler MVP

1. **Question template system** (8 hours)
   - [ ] Use Gemini to generate 100+ templates from prompt
   - [ ] Save to `data/question_templates.json`
   - [ ] Implement `QuestionEngine` with placeholder substitution
   - [ ] Test with 5 domains

2. **YouTube crawler** (16 hours)
   - [ ] YouTube Data API integration
   - [ ] Transcript extraction (youtube-transcript-api)
   - [ ] Metadata enrichment (channel info, engagement metrics)
   - [ ] Rate limiting with quota manager
   - [ ] Unit tests + integration tests

3. **Quality scorer** (8 hours)
   - [ ] Implement 5-factor algorithm
   - [ ] Calibrate weights (30/25/20/15/10)
   - [ ] Test with sample YouTube videos
   - [ ] Adjust threshold if needed

4. **End-to-end test** (4 hours)
   - [ ] Crawl 1 domain (MUSIC_PIANO) from YouTube
   - [ ] Index ~100 videos with deduplication
   - [ ] Query with RAG system
   - [ ] Verify quality of generated curriculum

### Week 5-6: Expand to Reddit

1. **Reddit crawler** (12 hours)
   - [ ] PRAW integration
   - [ ] Subreddit discovery for domains
   - [ ] Post + comment extraction
   - [ ] Karma-based filtering

2. **Multi-platform testing** (8 hours)
   - [ ] Crawl 3 domains from YouTube + Reddit
   - [ ] Measure deduplication rate
   - [ ] Compare quality scores across platforms
   - [ ] Optimize quality thresholds

---

## Conclusion

The Autodidact AI Core project has a **solid foundation** in the existing RAG system (LangChain + Gemini + ChromaDB) but requires **significant integration work** to connect with the newly designed bot crawler.

### Key Takeaways

1. **Architecture Alignment**: Both systems are compatible at a high level (Python, ChromaDB, similar metadata concepts) but need schema unification

2. **Critical Path**: 
   - Unified metadata schema (Week 1)
   - Embedding model upgrade (Week 1)
   - Deduplication layer (Week 2)
   - Bot MVP with YouTube (Weeks 3-4)

3. **Scale Challenges**: Moving from 10 test vectors to 20M+ production vectors requires:
   - Collection sharding
   - Intelligent caching
   - Performance monitoring
   - Phased rollout

4. **Quality Assurance**: The 5-factor quality scoring algorithm is **essential** to prevent garbage-in-garbage-out. Plan for human validation in Phase 1.

5. **Estimated Timeline**:
   - **Phase 1 (Foundation)**: 2 weeks
   - **Phase 2 (Bot MVP)**: 4 weeks
   - **Phase 3 (Scale Testing)**: 4 weeks
   - **Phase 4 (Production)**: 6 weeks
   - **Total**: ~4 months to production-ready system

6. **Resource Requirements**:
   - **Development**: 1-2 engineers full-time
   - **Infrastructure**: ~$150-300/month (API quotas, hosting, monitoring)
   - **Storage**: ~100GB for 20M vectors (ChromaDB + metadata)

### Final Recommendation

**Proceed with integration** using the phased roadmap outlined in Section 8. The architectural design is sound, and the identified gaps have clear mitigation strategies. Focus on getting Phase 1 (foundation) rock-solid before scaling, as metadata schema changes become exponentially harder with millions of vectors.

**Prioritize deduplication and quality scoring** from day 1 - these are the two highest-risk areas that will make or break the system's success.

---

## Appendix: File-Level Integration Checklist

### Files to Create (New)

- [ ] `src/models/unified_metadata_schema.py` - Pydantic schema
- [ ] `src/db_utils/deduplication.py` - 3-tier dedup service
- [ ] `src/db_utils/redis_client.py` - Redis connection
- [ ] `src/db_utils/collection_manager.py` - ChromaDB sharding
- [ ] `src/bot/coordinator.py` - MasterCoordinator
- [ ] `src/bot/question_engine.py` - Template processor
- [ ] `src/bot/crawlers/base_crawler.py` - Abstract interface
- [ ] `src/bot/crawlers/youtube_crawler.py` - YouTube implementation
- [ ] `src/bot/crawlers/reddit_crawler.py` - Reddit implementation
- [ ] `src/bot/crawlers/quora_crawler.py` - Quora implementation
- [ ] `src/bot/crawlers/blog_crawler.py` - Blog implementation
- [ ] `src/bot/extractor.py` - Content extraction
- [ ] `src/bot/quality_scorer.py` - 5-factor scoring
- [ ] `src/bot/storage_manager.py` - ChromaDB integration with dedup
- [ ] `data/question_templates.json` - Generated templates
- [ ] `config/tech_stack.yml` - Unified configuration

### Files to Modify (Existing)

- [ ] `src/agents/intake_agent.py` - Accept `UnifiedMetadata`, use new embedding model
- [ ] `src/agents/scope_agent.py` - Extract `domain_id`/`subdomain_id`, backward compatibility
- [ ] `src/agents/question_agent.py` - Use `CollectionManager` for multi-collection queries
- [ ] `src/db_utils/chroma_client.py` - Configure `all-mpnet-base-v2` embedding function
- [ ] `docker-compose.yml` - Add Redis, update ChromaDB settings
- [ ] `requirements.txt` - Add dependencies (sentence-transformers, redis, praw, selenium, etc.)
- [ ] `main.py` - Add bot orchestration entry point

### Files to Delete (Deprecated)

- [ ] `src/models/curriculum_schema.py` - Empty, replaced by `unified_metadata_schema.py`
- [ ] `src/db_utils/vector_store.py` - Empty, functionality in `collection_manager.py`

### Files to Review (Context)

- [x] `ARCHITECTURE.md` - Original design reference
- [x] `data/bot/architecture.md` - New bot design
- [x] `data/strategy/search_crawl_strategy.md` - Crawling strategies
- [x] `data/domains.json` - Domain list
- [x] `data/domains_with_subdomains.json` - Subdomain mappings

---

**END OF REPORT**
