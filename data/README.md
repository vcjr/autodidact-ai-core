# Autodidact Content Crawler - Project Overview

## 📚 Documentation Index

This project contains comprehensive documentation for building an intelligent content crawler that discovers, extracts, and indexes educational resources across multiple platforms.

---

## 📁 File Structure

```
autodidact-ai-core/
├── data/
│   ├── bot/
│   │   ├── architecture.md              # Complete bot architecture
│   │   └── quick_start.md               # Quick start implementation guide
│   │
│   ├── strategy/
│   │   ├── search_crawl_strategy.md     # Platform-specific strategies
│   │   └── implementation_notes.md      # Code examples & best practices
│   │
│   ├── prompts/
│   │   ├── subdomain_generation_prompt.md
│   │   └── question_template_generation_prompt.md
│   │
│   ├── domains.json                     # 217 learning domains
│   └── domains_with_subdomains.json     # 45 domains with subdomains
```

---

## 📖 Documentation Guide

### 1. **Bot Architecture** ([bot/architecture.md](./bot/architecture.md))
**Read this first to understand the system design.**

**Contents:**
- System architecture overview
- Component descriptions (Coordinator, Question Engine, Crawlers, etc.)
- Data flow diagrams
- Storage strategy (PostgreSQL + Chroma)
- Workflow execution patterns
- Configuration examples
- Performance optimization strategies

**Key Sections:**
- Master Coordinator design
- Question Generation Engine
- Platform-specific crawlers (YouTube, Reddit, Quora, Blogs)
- Content extraction and quality scoring
- Error handling and resilience

---

### 2. **Search & Crawl Strategy** ([strategy/search_crawl_strategy.md](./strategy/search_crawl_strategy.md))
**Read this to understand how to effectively discover content.**

**Contents:**
- Platform-specific search strategies
- Query construction patterns
- Quality indicators and filtering
- Content prioritization
- Crawl scheduling and phases
- Resource allocation
- Performance metrics

**Key Sections:**
- YouTube search optimization
- Reddit subreddit discovery
- Quora web scraping approach
- Blog discovery methods
- Query generation strategy
- Quality control pipeline

---

### 3. **Implementation Notes** ([strategy/implementation_notes.md](./strategy/implementation_notes.md))
**Read this when you're ready to code.**

**Contents:**
- Platform-specific API setup instructions
- Code examples for each crawler
- Quality scoring implementation
- Performance optimization techniques
- Error handling patterns
- Testing strategies
- Deployment checklist

**Key Sections:**
- YouTube API integration code
- Reddit PRAW implementation
- Quora Selenium scraping
- Blog extraction with newspaper3k
- Quality scoring algorithm details
- Async processing examples

---

### 4. **Quick Start Guide** ([bot/quick_start.md](./bot/quick_start.md))
**Read this for step-by-step setup instructions.**

**Contents:**
- Directory structure setup
- Environment configuration
- Dependency installation
- Database initialization
- Testing procedures
- Deployment steps
- Monitoring commands

---

### 5. **Question Template Prompt** ([prompts/question_template_generation_prompt.md](./prompts/question_template_generation_prompt.md))
**Use this to generate the question templates.**

**Contents:**
- Detailed prompt for AI to generate 100+ question templates
- Template structure and placeholder system
- 15 question categories
- Platform-specific considerations
- Output schema definition
- Quality guidelines

---

## 🎯 Project Goals

### Primary Objective
Build a comprehensive knowledge base of educational content covering 217 learning domains by intelligently crawling YouTube, Reddit, Quora, and educational blogs.

### Coverage Targets
- **Minimum:** 50 high-quality resources per domain
- **Target:** 200-500 resources per domain  
- **Stretch:** 1000+ resources for high-demand domains

### Quality Standards
- Minimum quality score: 60/100
- Multi-dimensional scoring (relevance, authority, engagement, freshness, completeness)
- Automatic deduplication
- Platform diversity

---

## 🚀 Quick Start Path

### For Architects/Planners:
1. Read **Bot Architecture** → Understand the system
2. Read **Search & Crawl Strategy** → Understand the approach
3. Review **Quick Start Guide** → Plan implementation

### For Developers:
1. Skim **Bot Architecture** → Get context
2. Read **Implementation Notes** → See code examples
3. Follow **Quick Start Guide** → Build the system
4. Reference **Search & Crawl Strategy** → Optimize queries

### For Product Managers:
1. Read **Project Overview** (this file) → Understand scope
2. Review **Search & Crawl Strategy** → Understand phases and timelines
3. Check **Bot Architecture** → Understand capabilities

---

## 🔑 Key Concepts

### Question Templates
100+ template questions with placeholders that generate thousands of specific queries:
- Template: `"How to learn ${DOMAIN}?"`
- Generated: `"How to learn piano?"`, `"How to learn Python?"`, etc.

### Multi-Platform Strategy
Each platform requires different approaches:
- **YouTube:** API-based, video + transcript extraction
- **Reddit:** API-based, discussion + comment mining
- **Quora:** Web scraping, Q&A extraction
- **Blogs:** Google CSE + direct crawling

### Quality Scoring
Multi-factor scoring system (0-100):
- Relevance: 30%
- Authority: 25%
- Engagement: 20%
- Freshness: 15%
- Completeness: 10%

### Phased Rollout
- **Phase 1** (Weeks 1-2): Top 50 domains, foundation
- **Phase 2** (Weeks 3-6): All 217 domains, expansion
- **Phase 3** (Weeks 7-10): Subdomain depth, refinement
- **Phase 4** (Ongoing): Maintenance and updates

---

## 📊 Technical Stack

### Core Technologies
- **Python 3.9+**
- **PostgreSQL** (metadata storage)
- **Chroma** (vector database)
- **Sentence Transformers** (embeddings)

### Platform APIs
- **YouTube Data API v3**
- **Reddit API (PRAW)**
- **Google Custom Search API**
- **Selenium** (for Quora)

### Content Processing
- **BeautifulSoup4** (HTML parsing)
- **newspaper3k** (article extraction)
- **youtube-transcript-api** (captions)

---

## 📈 Expected Outcomes

### Data Volume
- **~43,400 resources** (217 domains × 200 avg)
- **~3GB** total storage (content + embeddings)
- **~500MB** vector embeddings

### Time Investment
- **Initial build:** 2-4 weeks
- **Initial crawl:** 8-12 weeks
- **Ongoing maintenance:** 5-10 hours/week

### API Costs
- **YouTube:** Free (within quota)
- **Reddit:** Free
- **Google CSE:** Free tier or ~$50/month
- **Proxies (optional):** $50-100/month
- **Total:** $0-$150/month

---

## 🎓 Use Cases

### For Learners
- Discover high-quality learning resources
- Find curated content by skill level
- Access diverse learning formats (video, text, discussion)

### For Platform
- Power search and recommendation engine
- Enable semantic search across all resources
- Provide personalized learning paths
- Track resource quality over time

### For Creators
- Identify content gaps
- Understand learner questions
- Benchmark against existing resources

---

## ⚠️ Important Considerations

### Legal & Ethical
- ✅ Respect platform Terms of Service
- ✅ Follow robots.txt
- ✅ Implement rate limiting
- ✅ Attribute content to creators
- ✅ Store metadata, not full content (where appropriate)

### Technical
- ⚠️ API quotas are limited (manage carefully)
- ⚠️ Quora requires web scraping (detection risk)
- ⚠️ Content quality varies (need robust filtering)
- ⚠️ Storage grows quickly (plan capacity)

### Operational
- 📊 Monitor quality metrics continuously
- 🔄 Re-crawl periodically for freshness
- 🐛 Handle errors gracefully
- 📈 Scale gradually to avoid platform bans

---

## 🛠️ Next Steps

### Immediate (Week 1)
1. [ ] Set up development environment
2. [ ] Configure API credentials
3. [ ] Generate question templates
4. [ ] Test individual platform crawlers
5. [ ] Initialize databases

### Short-term (Weeks 2-4)
6. [ ] Implement quality scoring
7. [ ] Test on 5-10 domains
8. [ ] Refine quality thresholds
9. [ ] Set up monitoring
10. [ ] Begin Phase 1 crawl

### Medium-term (Weeks 5-12)
11. [ ] Complete Phase 2 (all domains)
12. [ ] Optimize query templates
13. [ ] Implement incremental updates
14. [ ] Build analytics dashboard

### Long-term (Months 4+)
15. [ ] Machine learning quality scorer
16. [ ] Real-time content monitoring
17. [ ] Multi-language support
18. [ ] User feedback integration

---

## 📞 Support & Resources

### Documentation Files
- [Bot Architecture](./bot/architecture.md) - System design
- [Search Strategy](./strategy/search_crawl_strategy.md) - Platform strategies
- [Implementation Notes](./strategy/implementation_notes.md) - Code examples
- [Quick Start](./bot/quick_start.md) - Setup guide

### External Resources
- [YouTube Data API Docs](https://developers.google.com/youtube/v3)
- [Reddit API (PRAW) Docs](https://praw.readthedocs.io/)
- [Google Custom Search Docs](https://developers.google.com/custom-search)
- [Chroma Documentation](https://docs.trychroma.com/)

---

## 📝 Changelog

### Version 1.0 (2025-10-25)
- Initial architecture design
- Platform-specific strategies defined
- Question template system designed
- Implementation guides created
- Quality scoring algorithm defined

---

## 🤝 Contributing

### Adding New Domains
1. Add to `domains.json`
2. Map to subreddits (if applicable)
3. Add to blog database (if applicable)
4. Generate question templates

### Improving Quality Scoring
1. Collect sample content
2. Manual quality assessment
3. Tune scoring weights
4. Test on diverse content

### Adding New Platforms
1. Design crawler following `BaseCrawler` interface
2. Document platform-specific strategy
3. Add to coordinator
4. Test thoroughly

---

**Project Status:** ✅ Architecture Complete - Ready for Implementation  
**Last Updated:** October 25, 2025  
**Version:** 1.0.0
