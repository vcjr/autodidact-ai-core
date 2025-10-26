# Question Template Strategy

**Date**: October 25, 2025  
**Status**: Phase 2 - Template Generation

---

## Current Approach

### Template Generation
- **Target**: 150-200 generic templates
- **Format**: JSON (`data/question_templates.json`)
- **Coverage**: 217 domains + 350 subdomains
- **Total Query Potential**: ~35,000 unique queries (150 templates × 217 domains)

### Why This Works for Phase 2
✅ **API cost control**: Single Gemini call, ~60-90 seconds generation  
✅ **Quality over quantity**: Manageable review size (150-200 templates)  
✅ **Readable format**: JSON is human-editable, git-friendly  
✅ **Fast iteration**: Easy to regenerate if templates need tweaking  
✅ **Sufficient coverage**: 35K queries is MORE than enough to validate crawler  

---

## Template Structure

### Generic Templates (Current)
Work across ALL domains via placeholders:
```
"How to learn ${DOMAIN}?"
"Best ${DOMAIN} resources for ${LEVEL}?"
"${DOMAIN} vs ${DOMAIN_B}: which to learn first?"
"Common mistakes when learning ${DOMAIN}?"
```

### Subdomain-Aware Templates (Included)
Specific enough for subdomains:
```
"How to transition from ${SUBDOMAIN_A} to ${SUBDOMAIN_B}?"
"Prerequisites for learning ${SUBDOMAIN}?"
"Is ${SUBDOMAIN} harder than ${SUBDOMAIN_B}?"
"Best ${SUBDOMAIN} tutorials for ${LEVEL}?"
```

### Platform-Specific Templates
Optimized for each platform's search behavior:
```
YouTube:  "[${SUBDOMAIN}] tutorial for beginners"
Reddit:   "Best resources for learning ${SUBDOMAIN} in 2025?"
Quora:    "Is ${SUBDOMAIN} harder than ${SUBDOMAIN_B}?"
Blogs:    "${SUBDOMAIN} complete guide from scratch"
```

---

## Validation Criteria

### Current Requirements
- ✅ **Count**: 150-200 templates
- ✅ **Subdomain coverage**: ≥25% templates subdomain-specific
- ✅ **Categories**: 15 diverse types (how-to, comparison, resource, troubleshooting, etc.)
- ✅ **Skill levels**: beginner, intermediate, advanced, all
- ✅ **Platforms**: youtube, reddit, quora, blogs

### Quality Checks
- Unique IDs (no duplicates)
- Required fields present (id, category, template, placeholders, example, platforms, skill_level)
- Placeholder syntax validation (`${PLACEHOLDER}` format)

---

## Future Scaling Strategy

### When to Expand (Phase 3+)

**Trigger Conditions:**
1. Phase 2 crawler validates templates work well
2. Need category-specific templates (e.g., MUSIC templates different from CODING)
3. Analytics show certain templates underperform
4. Want 1000+ templates for deeper coverage

### Hierarchical Template System (Recommended)

#### Tier 1: Generic Templates (150-200)
- **Current approach**: Works across all 217 domains
- **Storage**: `data/question_templates.json`
- **Generation**: Single Gemini call

#### Tier 2: Category-Specific Templates (20-30 per category)
- **When**: After Phase 2 validation
- **Storage**: Separate files per category:
  ```
  data/templates/
  ├── music_templates.json          (30 music-specific)
  ├── coding_templates.json         (30 coding-specific)
  ├── martial_arts_templates.json   (30 martial-arts-specific)
  └── ...                           (45 categories total)
  ```
- **Benefit**: 150 generic + (30 × 45 categories) = ~1,500 total templates
- **Coverage**: ~325,000 unique queries across taxonomy

#### Tier 3: Platform-Optimized Templates
- **When**: After analyzing which platforms perform best
- **Storage**: Platform-specific files:
  ```
  data/templates/
  ├── youtube_specific.json
  ├── reddit_specific.json
  ├── quora_specific.json
  └── blog_specific.json
  ```

---

## Storage Format Comparison

### JSON (Current - RECOMMENDED for Phase 2)
**Pros:**
- ✅ Universal compatibility (Python, JS, any language)
- ✅ Human-readable, easy to review/edit
- ✅ Git-friendly (clear diffs)
- ✅ No dependencies (Python stdlib)
- ✅ Direct Gemini API integration

**Cons:**
- ❌ Must load entire file into RAM
- ❌ No querying without loading all
- ❌ Linear search (O(n) lookups)

**Best for**: <1,000 templates, rapid iteration

---

### SQLite (Future - Phase 3+)
**Pros:**
- ✅ Efficient querying (category, platform, skill level filters)
- ✅ Indexing for fast lookups
- ✅ Analytics support (track template performance)
- ✅ Handles 100K+ templates easily
- ✅ Single file, no server needed

**Cons:**
- ❌ Less human-readable
- ❌ Requires schema definition
- ❌ Git diffs harder to read

**Best for**: 1,000+ templates, production scale

**Schema (when ready):**
```sql
CREATE TABLE question_templates (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    template TEXT NOT NULL,
    placeholders TEXT,      -- JSON array
    example TEXT,
    platforms TEXT,         -- JSON array
    skill_level TEXT,
    quality_score REAL,     -- track which templates work best
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_category ON question_templates(category);
CREATE INDEX idx_platform ON question_templates(platforms);
CREATE INDEX idx_skill_level ON question_templates(skill_level);
CREATE INDEX idx_quality ON question_templates(quality_score DESC);
```

**Migration (when needed):**
```python
import json
import sqlite3

# Load JSON
with open('data/question_templates.json') as f:
    data = json.load(f)

# Create SQLite DB
conn = sqlite3.connect('data/question_templates.db')
cursor = conn.cursor()

# Insert templates
for template in data['question_templates']:
    cursor.execute("""
        INSERT INTO question_templates 
        (id, category, template, placeholders, example, platforms, skill_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        template['id'],
        template['category'],
        template['template'],
        json.dumps(template['placeholders']),
        template['example'],
        json.dumps(template['platforms']),
        template['skill_level']
    ))

conn.commit()
```

---

## Action Plan

### Phase 2 (Current)
1. ✅ Generate 150-200 templates with subdomain coverage
2. ⏳ Test templates with YouTube crawler on 5-10 domains
3. ⏳ Validate template quality (do they produce good content?)
4. ⏳ Measure coverage (are 150-200 templates sufficient?)

### Phase 3 (After Validation)
Based on Phase 2 results, choose ONE:

**Option A: Keep JSON, Add Category Files**
- If 150-200 templates work well but want more specificity
- Add category-specific template files
- Total: ~1,500 templates across 45+ files
- Still JSON-based, easy to manage

**Option B: Migrate to SQLite**
- If need >1,000 templates
- If want template analytics (which templates perform best?)
- If need complex querying (category + platform + skill level filters)
- Overkill if current approach works

**Option C: Do Nothing**
- If 150-200 templates provide sufficient coverage
- If crawlers generate enough quality content
- Simplest approach, least maintenance

---

## Key Decisions to Make

### After Phase 2 Testing

**Question 1: Are 150-200 templates enough?**
- ✅ YES → Keep current approach, focus on crawler quality
- ❌ NO → Implement Tier 2 (category-specific templates)

**Question 2: Do we need template analytics?**
- ✅ YES → Migrate to SQLite for quality tracking
- ❌ NO → Keep JSON, simpler is better

**Question 3: Do templates need platform-specific variants?**
- ✅ YES → Create platform-specific template files
- ❌ NO → Generic templates work across all platforms

**Question 4: Are category-specific templates needed?**
- ✅ YES → MUSIC templates differ significantly from CODING
- ❌ NO → Generic templates work well across domains

---

## Metrics to Track (Phase 2)

### Template Performance
- **Coverage**: How many domains produce good content?
- **Quality**: Average quality_score of crawled content per template
- **Diversity**: Do templates produce varied content types?
- **Platform fit**: Do templates work equally well on all platforms?

### Operational Metrics
- **Generation time**: ~60-90 seconds acceptable?
- **File size**: <1MB for 150-200 templates (easily manageable)
- **Load time**: <100ms to load all templates (negligible)
- **Memory usage**: <5MB in RAM (not a concern)

### Success Criteria
- ✅ 80%+ domains produce quality content with current templates
- ✅ Templates generate diverse content types (tutorials, comparisons, guides)
- ✅ No major gaps in coverage (all skill levels, platforms represented)

**If success criteria met → No changes needed, proceed to Phase 4**

---

## Notes

### Advantages of Starting Small
1. **Faster iteration**: Regenerate 150-200 templates in <2 minutes
2. **Easier review**: Can manually inspect all templates
3. **Lower cost**: Single Gemini API call (<$0.10)
4. **Simpler debugging**: Fewer templates = easier to identify issues
5. **Proven approach**: Validate before scaling

### When More Templates Needed
- After crawler shows specific domain gaps
- When analytics reveal underperforming categories
- If expanding to more platforms (TikTok, Instagram, podcasts)
- When adding new domain categories beyond current 217

### Migration Path is Easy
```
JSON → SQLite = 20-line Python script
SQLite → PostgreSQL = pg_dump export
```
Starting with JSON doesn't lock us into anything.

---

## Recommendation: Start with JSON, Scale Only If Needed

**Current plan is optimal for Phase 2 validation.**  
Re-evaluate after crawler testing shows real-world results.
