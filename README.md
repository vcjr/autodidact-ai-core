# Autodidact AI Core 🎓

> **Intelligent curriculum generation powered by community-validated educational content**

An AI-driven platform that discovers, curates, and synthesizes personalized learning paths across 217+ domains by leveraging the collective wisdom of YouTube, Reddit, Quora, and educational blogs.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![ChromaDB](https://img.shields.io/badge/vectordb-ChromaDB-orange.svg)](https://www.trychroma.com/)
[![Gemini AI](https://img.shields.io/badge/llm-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 What Makes This Different?

Traditional learning platforms rely on static, curator-created content. **Autodidact AI** takes a fundamentally different approach:

1. **🤖 Intelligent Discovery**: Multi-platform bot crawlers systematically discover educational content across YouTube, Reddit, Quora, and blogs using 100+ question templates
2. **⭐ Quality Validation**: 5-factor scoring algorithm (relevance, authority, engagement, freshness, completeness) ensures only high-quality resources are indexed
3. **🎯 Semantic Retrieval**: 768-dimensional vector embeddings enable nuanced similarity search beyond keyword matching
4. **📚 AI Synthesis**: Google Gemini LLM generates structured, step-by-step curricula grounded in community-validated sources

**Result**: Learning paths that combine the comprehensiveness of human expertise with the scale and personalization of AI.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    OFFLINE INDEXING (Bot System)                │
│  YouTube + Reddit + Quora + Blog Crawlers → Quality Scorer      │
│                           ↓                                      │
│              ChromaDB (768d Embeddings + Metadata)              │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                   ONLINE QUERY (RAG System)                     │
│  User Query → ScopeAgent → Filtered Retrieval → Gemini → Path  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component           | Technology                              | Purpose                                                    |
| ------------------- | --------------------------------------- | ---------------------------------------------------------- |
| **Vector Store**    | ChromaDB (HTTP)                         | Semantic search over 768d embeddings                       |
| **Embedding Model** | sentence-transformers/all-mpnet-base-v2 | High-quality text embeddings (768 dimensions)              |
| **LLM**             | Google Gemini (gemini-2.5-flash)        | Structured output generation, curriculum synthesis         |
| **Metadata Schema** | UnifiedMetadata (Pydantic)              | Domain/subdomain taxonomy, quality scores, platform data   |
| **Orchestration**   | Custom Agents (LangChain-style)         | IntakeAgent, ScopeAgent, QuestionAgent                     |
| **Deduplication**   | Redis (planned)                         | 3-tier dedup (URL hash, content hash, semantic similarity) |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Docker** (for ChromaDB and Redis)
- **Google Gemini API Key** ([Get one here](https://ai.google.dev/))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/vcjr/autodidact-ai-core.git
cd autodidact-ai-core

# 2. Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Start Docker services (ChromaDB + Redis)
docker-compose up -d

# 6. Run setup script
./setup.sh
```

### Test the RAG Pipeline

```bash
# Ingest a sample document
python src/agents/intake_agent.py

# Test the full RAG pipeline
python src/agents/question_agent.py
```

**Expected Output**: A structured curriculum for advanced electric guitar sweeping with source citations.

---

## 📈 Professional Analysis & Scaling Roadmap

As an architect-level AI and software engineer, I have conducted a detailed analysis of this project. The following is a summary of recommendations for evolving `autodidact-ai-core` into a robust, production-grade system, as a full engineering team would.

The full, detailed roadmap with implementation instructions for an AI agent or engineer is available here:
**[📄 Detailed Optimization and Scaling Roadmap](./docs/OPTIMIZATION_ROADMAP.md)**

### Summary of Recommendations

-   **Phase 1: Foundational Scaling**
    -   **Decouple Components:** Introduce a message queue (e.g., RabbitMQ) to evolve from a monolithic to a scalable, resilient microservices architecture.
    -   **Production Orchestration:** Migrate from `docker-compose` to Kubernetes for scalable, production-ready deployments.
    -   **Automate Deployments:** Implement a full CI/CD pipeline with GitHub Actions to automate testing, image building, and deployment.

-   **Phase 2: AI/ML & Vector DB Optimization**
    -   **Production Vector DB:** Migrate from ChromaDB to a managed, scalable vector database like Pinecone or Weaviate to handle production loads.
    -   **Advanced Retrieval:** Implement hybrid search and a re-ranking layer to significantly improve search accuracy and relevance.

-   **Phase 3: Maturity and Intelligence**
    -   **Custom Models:** Fine-tune custom embedding and generator models on domain-specific data to achieve state-of-the-art performance.
    -   **Human-in-the-Loop:** Build a system for human experts to review and correct AI outputs, creating a continuous feedback loop for model improvement.
    -   **ML Monitoring:** Implement comprehensive monitoring to track model performance, detect data drift, and ensure long-term system health.

---

## 📖 Usage Examples

### 1. Manual Document Ingestion

```python
from src.agents.intake_agent import IntakeAgent
from src.models.unified_metadata_schema import create_manual_metadata, Difficulty

# Create metadata
metadata = create_manual_metadata(
    instrument_id="CODING_SOFTWARE_PYTHON",
    source="https://realpython.com/python-async-features/",
    difficulty=Difficulty.INTERMEDIATE,
    text_length=2500,
    helpfulness_score=0.92,
    technique="async/await",
    tags=["python", "asyncio", "concurrency"]
)

# Ingest content
agent = IntakeAgent()
doc_id = agent.process_and_add_document(
    content="Comprehensive guide to Python's asyncio...",
    source_url="https://realpython.com/python-async-features/",
    metadata=metadata
)
```

### 2. Generate a Custom Curriculum

```python
from src.agents.question_agent import QuestionAgent

agent = QuestionAgent()
curriculum = agent.generate_curriculum(
    "Create a learning path for Python focusing on async programming"
)

print(curriculum)
```

**Output**: Step-by-step curriculum with resource citations, filtered by quality score ≥ 0.8.

### 3. Scope Analysis (Query Understanding)

```python
from src.agents.scope_agent import ScopeAgent

agent = ScopeAgent()
filters = agent.build_chroma_where_filter(
    "Learn advanced jazz piano improvisation"
)

# Returns:
# {
#   "$and": [
#     {"domain_id": "MUSIC"},
#     {"subdomain_id": "PIANO"},
#     {"difficulty": "advanced"},
#     {"helpfulness_score": {"$gte": 0.8}}
#   ]
# }
```

---

## 📊 Project Status

### ✅ Phase 1: Foundation (Weeks 1-2) - **COMPLETE**

- [x] Unified metadata schema (`UnifiedMetadata`)
- [x] ChromaDB embedding upgrade (384d → 768d)
- [x] IntakeAgent updated for new schema
- [x] ScopeAgent with domain/subdomain extraction
- [x] Legacy data migration (1 test document → v2 collection)
- [x] Full RAG pipeline tested successfully

### 🚧 Phase 2: Bot Development (Weeks 3-6) - **IN PROGRESS**

- [ ] Question template generation (100+ templates)
- [ ] YouTube crawler (YouTube Data API v3)
- [ ] Reddit crawler (PRAW)
- [ ] Quora crawler (Selenium)
- [ ] Blog crawler (Google Custom Search + newspaper3k)
- [ ] 5-factor quality scorer
- [ ] Redis-backed deduplication layer

### 📅 Phase 3: Scale Testing (Weeks 7-10) - **PLANNED**

- [ ] Tier 1 domains crawl (30 domains, ~3M vectors)
- [ ] Collection sharding strategy
- [ ] Performance optimization (query latency < 500ms)
- [ ] Prefect/Airflow scheduling

### 🎯 Phase 4: Production (Weeks 11-16) - **PLANNED**

- [ ] All 217 domains indexed (20M+ vectors)
- [ ] Prometheus + Grafana monitoring
- [ ] API endpoints for bot control
- [ ] Incremental indexing (daily/weekly updates)

---

## 🗂️ Project Structure

```
autodidact-ai-core/
├── src/
│   ├── agents/                   # RAG system agents
│   │   ├── intake_agent.py       # Document ingestion + embedding
│   │   ├── scope_agent.py        # Query analysis + filter generation
│   │   ├── question_agent.py     # Full RAG orchestration
│   │   └── validation_agent.py   # (Future) Quality validation
│   ├── db_utils/                 # Database clients
│   │   ├── chroma_client.py      # ChromaDB HTTP client
│   │   ├── llm_client.py         # Gemini API wrapper
│   │   └── vector_store.py       # (Future) Advanced vector ops
│   ├── models/                   # Pydantic schemas
│   │   └── unified_metadata_schema.py  # UnifiedMetadata model
│   └── bot/                      # (Future) Crawler system
│       ├── coordinator.py        # Master orchestrator
│       ├── question_engine.py    # Template processor
│       ├── crawlers/             # Platform-specific crawlers
│       ├── quality_scorer.py     # 5-factor scoring
│       └── storage_manager.py    # ChromaDB integration
├── data/
│   ├── domains.json              # 217 learning domains
│   ├── domains_with_subdomains.json  # 45 domains + subdomains
│   ├── prompts/                  # LLM prompts
│   ├── bot/                      # Bot architecture docs
│   └── strategy/                 # Crawl strategy docs
├── scripts/
│   └── migrate_to_v2.py          # Legacy → v2 migration
├── tests/
│   └── test_unified_metadata.py  # Schema validation tests
├── docker-compose.yml            # ChromaDB + Redis
├── requirements.txt              # Python dependencies
├── setup.sh                      # One-command setup
├── ARCHITECTURE.md               # Original design doc
├── INTEGRATION_ANALYSIS.md       # Expert integration report
└── README.md                     # This file
```

---

## 🔬 Technical Deep Dive

### Metadata Schema

The `UnifiedMetadata` schema bridges the bot crawler and RAG system:

```python
{
    # Domain taxonomy
    "domain_id": "MUSIC",
    "subdomain_id": "ELECTRIC_GUITAR",
    "instrument_id": "MUSIC_ELECTRIC_GUITAR",  # Auto-generated for backward compat
    
    # Content metadata
    "source": "https://youtube.com/watch?v=...",
    "platform": "youtube",
    "content_type": "video",
    "author": "GuitarLessons",
    "created_at": "2024-01-15T10:00:00Z",
    
    # Learning metadata
    "difficulty": "advanced",
    "technique": "sweeping",
    "tags": ["guitar", "technique", "metal"],
    
    # Quality metrics
    "helpfulness_score": 0.87,  # Overall score (0.0-1.0)
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
    }
}
```

### Embedding Strategy

- **Model**: `sentence-transformers/all-mpnet-base-v2`
- **Dimensions**: 768 (vs 384 for all-MiniLM-L6-v2)
- **Normalization**: Cosine similarity enabled
- **Collection**: `autodidact_ai_core_v2` (legacy: `autodidact_ai_core`)

**Why 768d?** Higher dimensionality captures semantic nuance better, critical for distinguishing between similar educational concepts (e.g., "Python decorators" vs "Python generators").

### Quality Scoring Algorithm

5-factor weighted scoring ensures only high-quality content is indexed:

| Factor           | Weight | Criteria                                                  |
| ---------------- | ------ | --------------------------------------------------------- |
| **Relevance**    | 30%    | Semantic similarity to domain/subdomain                   |
| **Authority**    | 25%    | Creator reputation, channel subscribers, domain authority |
| **Engagement**   | 20%    | Views, likes, comments (normalized by recency)            |
| **Freshness**    | 15%    | Publication date (decay curve over 3 years)               |
| **Completeness** | 10%    | Content length, depth, code examples, citations           |

**Threshold**: `helpfulness_score ≥ 0.8` to enter the index.

---

## 🎯 Supported Domains

Currently targeting **217 domains** across:

- **Creative Arts**: Music (12 instruments), Visual Arts, Film/Video, Writing, Design
- **Technology**: Coding/Software (20+ languages), Data Science, Cybersecurity, DevOps
- **Languages**: 15+ natural languages (Spanish, Mandarin, French, etc.)
- **Sciences**: Mathematics, Physics, Chemistry, Biology, Astronomy
- **Business**: Marketing, Finance, Entrepreneurship, Management
- **And more**: Health/Fitness, Personal Development, Gaming, Crafts, etc.

See [`data/domains.json`](data/domains.json) for the complete list.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run schema validation tests
pytest tests/test_unified_metadata.py -v

# Test individual agents
python src/agents/intake_agent.py
python src/agents/scope_agent.py
python src/agents/question_agent.py

# Test ChromaDB connection
python src/db_utils/chroma_client.py

# Run migration script
python scripts/migrate_to_v2.py
```

**Current Test Coverage**: 14/14 schema validation tests passing ✅

---

## 📈 Scaling Strategy

### Current State (Phase 1)
- **Vectors**: ~2 test documents
- **Collection**: Single `autodidact_ai_core_v2`
- **Query Latency**: < 50ms

### Phase 3 Target (Tier 1)
- **Vectors**: ~3M (30 domains)
- **Collection**: Single (ChromaDB sweet spot < 10M)
- **Query Latency**: < 500ms (p95)

### Phase 4 Target (Full Scale)
- **Vectors**: 20M+ (217 domains)
- **Collections**: Sharded by tier (3 collections)
- **Query Latency**: < 1s (p95)
- **Deduplication Rate**: 15-25% (cross-platform overlap)

**Future**: Migrate to Milvus/Weaviate if scaling beyond 50M vectors.

---

## 🔐 Environment Variables

Create a `.env` file with:

```bash
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Redis (for deduplication)
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys (Phase 2+)
YOUTUBE_API_KEY=your_youtube_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
GOOGLE_CSE_KEY=your_google_custom_search_key
GOOGLE_CSE_ID=your_search_engine_id
```

---

## 🤝 Contributing

We welcome contributions! Areas of focus:

1. **Platform Crawlers**: Implement Quora, blog, or new platform crawlers
2. **Quality Scoring**: Improve the 5-factor algorithm with domain-specific heuristics
3. **Question Templates**: Expand the template library for niche domains
4. **Performance**: Optimize ChromaDB queries, implement caching strategies
5. **Testing**: Increase test coverage, add integration tests

See [`INTEGRATION_ANALYSIS.md`](INTEGRATION_ANALYSIS.md) for architectural context.

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Original system design (100×100×100 scale concept)
- **[INTEGRATION_ANALYSIS.md](INTEGRATION_ANALYSIS.md)**: Expert architectural analysis (30+ pages)
- **[data/bot/architecture.md](data/bot/architecture.md)**: Bot crawler design (~8,500 words)
- **[data/strategy/search_crawl_strategy.md](data/strategy/search_crawl_strategy.md)**: Platform-specific crawl strategies
- **[Phase 1 README](PHASE1_README.md)**: Week-by-week progress (auto-generated by setup)

---

## 🐛 Known Issues & Limitations

1. **Limited Test Data**: Only 2 documents in v2 collection (Phase 1 complete, Phase 2 pending)
2. **Single Query at a Time**: No batch processing or concurrent queries yet
3. **No Deduplication**: Redis layer designed but not implemented (Phase 2)
4. **Fixed Quality Threshold**: `helpfulness_score ≥ 0.8` is hardcoded (should be configurable)
5. **ChromaDB Metadata Limitations**: All values stored as strings (workaround: JSON serialization)

---

## 🗺️ Roadmap

### Q4 2025
- ✅ Phase 1: Foundation complete
- 🚧 Phase 2: Bot MVP (YouTube + Reddit)

### Q1 2026
- Phase 3: Scale testing (3M vectors)
- Phase 4: Production rollout (20M vectors)

### Q2 2026
- Incremental indexing (daily/weekly updates)
- User feedback loop (boost engaged resources)
- Multi-modal embeddings (text + video frames)

### Q3 2026
- Cross-domain recommendations
- Personalized curriculum adaptation
- API for third-party integrations

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **ChromaDB** for the simple yet powerful vector database
- **Google Gemini** for structured LLM output capabilities
- **Sentence Transformers** (Hugging Face) for state-of-the-art embeddings
- **LangChain** for agentic architecture inspiration
- **The open-source community** for creating the educational content we index

---

## 📞 Contact

**Victor Crispin**  
- GitHub: [@vcjr](https://github.com/vcjr)
- Repository: [autodidact-ai-core](https://github.com/vcjr/autodidact-ai-core)

---

<div align="center">

**Built with 🤖 AI, powered by 📚 collective human knowledge**

[Report Bug](https://github.com/vcjr/autodidact-ai-core/issues) · [Request Feature](https://github.com/vcjr/autodidact-ai-core/issues) · [Documentation](INTEGRATION_ANALYSIS.md)

</div>
