# Codebase Cleanup Plan 🧹

## Summary
This document identifies redundant, obsolete, and deprecated code that can be safely removed or consolidated.

---

## 🗑️ Files to DELETE

### 1. Duplicate/Obsolete API Files
- **`api.py`** - OLD API (replaced by `api_v2.py`)
  - `api_v2.py` is the new FastAPI backend with playlist support
  - No references to `api.py` in active code
  - **Action:** Delete after confirming no production dependencies

- **`main.py`** - Purpose unclear, potentially obsolete
  - Check if this is an old entry point
  - **Action:** Delete if not actively used

### 2. Debug/Test Files in Root
- **`debug_scorer.py`** - One-off debug script
  - Created to test quality scorer bug
  - No longer needed (scorer is fixed)
  - **Action:** Delete

- **`proxy_config.json`** - Duplicate config
  - Real config is in `config/proxy_config.json`
  - This is just a symlink (safe to remove)
  - **Action:** Delete symlink

### 3. Obsolete Scripts
- **`scripts/minimal_index.py`** - OLD indexing approach
  - Replaced by `scripts/index_playlist_mvp.py`
  - Has TODO comments indicating incomplete implementation
  - **Action:** Delete

- **`scripts/minimal_index_queue.py`** - OLD queue-based indexing
  - Replaced by `scripts/quick_mvp_index_queue.py`
  - Has TODO: "You need a YouTube search function here"
  - **Action:** Delete

- **`scripts/quick_mvp_index.py`** - Redundant with `index_playlist_mvp.py`
  - **Action:** Review and delete if truly redundant

- **`scripts/quick_mvp_index_queue.py`** - Redundant with message queue system
  - Now using RabbitMQ workers instead
  - **Action:** Delete

- **`scripts/migrate_to_v2.py`** - One-time migration script
  - Used to migrate from legacy ChromaDB collection (384d → 768d)
  - Migration should be complete by now
  - **Action:** Delete (or move to `scripts/archive/` if keeping for reference)

- **`scripts/normalize_template_categories.py`** - One-time normalization
  - Used for initial template cleanup
  - **Action:** Delete (or archive)

- **`scripts/reorganize_project.sh`** - One-time reorganization
  - Already executed
  - **Action:** Delete (or archive)

- **`scripts/test_filter_syntax.py`** - Test file
  - Should be in `tests/` directory, not `scripts/`
  - **Action:** Move to `tests/unit/` or delete

### 4. Old Documentation
- **`APPROVAL_FIX_SUMMARY.md`** - Temporary fix summary
  - Issue is fixed, documented in `docs/VIDEO_APPROVAL_WORKFLOW.md`
  - **Action:** Delete

- **`Improvements.md`** - Ad-hoc notes
  - Consolidate into `docs/progress/PROGRESS.md`
  - **Action:** Merge then delete

### 5. Example/Demo Files
- **`examples/scraper_selection_example.py`** - Old example
  - Check if still relevant
  - **Action:** Delete if outdated

---

## 🔄 Files to CONSOLIDATE

### 1. Duplicate Indexing Scripts
**Problem:** Too many similar scripts for indexing videos

**Current Scripts:**
- `scripts/index_playlist_mvp.py` ✅ (KEEP - modern, uses GCS)
- `scripts/quick_mvp_index.py` ❌ (redundant)
- `scripts/quick_mvp_index_queue.py` ❌ (redundant)
- `scripts/minimal_index.py` ❌ (old)
- `scripts/minimal_index_queue.py` ❌ (old)

**Action:** Keep only `index_playlist_mvp.py`, delete the rest

### 2. Test Files Organization
**Current:** Test files scattered across multiple locations
- Root directory (old)
- `tests/integration/`
- `tests/unit/`
- `scripts/` (wrong location)

**Action:**
- Move `scripts/test_filter_syntax.py` → `tests/unit/`
- Delete any test files remaining in root

---

## 🔧 Code to REFACTOR

### 1. Remove Deprecated Parameters
**File:** `src/bot/bot_indexer.py`
```python
# Lines 95-103 - Remove deprecated parameters:
youtube_api_key: YouTube Data API v3 key (defaults to env var) - DEPRECATED, use Apify instead
use_proxies: Enable proxy rotation for transcript requests (default False) - DEPRECATED
proxy_config: Path to proxy config file or None for default - DEPRECATED
```

**Action:** Remove these parameters and update docstrings

### 2. Remove Legacy ChromaDB Collection References
**File:** `src/db_utils/chroma_client.py`
```python
# Line 16
COLLECTION_NAME_LEGACY = "autodidact_ai_core"  # Old collection (384d, deprecated)
```

**Action:** 
- Delete legacy collection if migration is complete
- Remove `COLLECTION_NAME_LEGACY` constant
- Update all references to use only v2 collection

### 3. Clean Up TODOs
**Files with TODOs:**
- `api_v2.py` - Line 329: Get actual queue position from RabbitMQ
- `scripts/queue_approved_video.py` - Lines 121, 126: Add domain/difficulty classification
- `src/bot/crawlers/youtube_crawler.py` - Lines 498-499: Fetch channel subscriber/verified from API

**Action:** Either implement or remove TODOs

---

## 📁 Directory Cleanup

### 1. Root Directory
**Current clutter:**
- `__pycache__/` - Add to `.gitignore`, delete
- `venv/` - Duplicate of `.venv/`, delete
- `proxy_config.json` - Symlink, delete

### 2. Data Directory
**Keep:**
- `data/domains.json`
- `data/question_templates.json`
- `data/bot/` documentation

**Delete:**
- `data/debug_*.txt` - Old debug outputs

### 3. Reports Directory
**Check if needed:**
- `reports/curriculum_v1_query*.md` - Old test outputs
- **Action:** Delete if no longer referenced

### 4. Logs Directory
**Action:** Add to `.gitignore`, clean up old logs

---

## 🚀 Recommended Cleanup Order

### Phase 1: Safe Deletions (No Impact)
1. Delete `debug_scorer.py`
2. Delete `APPROVAL_FIX_SUMMARY.md`
3. Delete old scripts:
   - `scripts/minimal_index.py`
   - `scripts/minimal_index_queue.py`
   - `scripts/quick_mvp_index.py`
   - `scripts/quick_mvp_index_queue.py`
4. Delete `scripts/reorganize_project.sh`
5. Delete `data/debug_*.txt` files

### Phase 2: Archive One-Time Scripts
Move to `scripts/archive/`:
- `scripts/migrate_to_v2.py`
- `scripts/normalize_template_categories.py`

### Phase 3: Code Refactoring
1. Remove deprecated parameters from `bot_indexer.py`
2. Remove `COLLECTION_NAME_LEGACY` after confirming migration complete
3. Clean up TODOs (implement or remove)

### Phase 4: Verify & Delete Old APIs
1. Confirm `api.py` is not used in production
2. Delete `api.py` and `main.py` if obsolete

---

## 📊 Expected Impact

### Lines of Code Reduced
- **~2,000 lines** from deleted scripts
- **~500 lines** from removed deprecated code

### Files Removed
- **~15 files** deleted
- **~5 files** archived

### Benefits
- ✅ Clearer project structure
- ✅ Faster navigation
- ✅ Less confusion for new developers
- ✅ Easier maintenance
- ✅ Smaller repo size

---

## ⚠️ Before Deleting Anything

1. **Create a backup branch:**
   ```bash
   git checkout -b cleanup-backup
   git checkout phase1-message-system
   ```

2. **Search for references:**
   ```bash
   # For each file to delete, search for imports/references
   grep -r "import minimal_index" .
   grep -r "from scripts.minimal_index" .
   ```

3. **Test after each phase:**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Try starting services
   streamlit run autodidact/ui/admin_dashboard.py
   python api_v2.py
   ```

---

## 📝 Execution Checklist

- [ ] Phase 1: Safe deletions
- [ ] Phase 2: Archive scripts
- [ ] Phase 3: Code refactoring
- [ ] Phase 4: Verify & delete old APIs
- [ ] Update `.gitignore` for generated files
- [ ] Run full test suite
- [ ] Update README.md if needed
- [ ] Commit changes with clear message

---

**Generated:** November 1, 2025
**Status:** Ready for review and execution
