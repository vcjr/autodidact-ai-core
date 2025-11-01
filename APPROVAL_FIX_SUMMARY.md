# 🚀 FIXED: Video Approval Not Queueing for Ingestion

## Problem
When you approved videos in the admin dashboard, they were being marked as `'approved'` in PostgreSQL but **not automatically queued for ingestion** into ChromaDB.

## Root Cause
The `update_status_callback()` function in `admin_dashboard.py` only updated the database status - it didn't trigger the queueing workflow.

## Solution Implemented

### 1. Auto-Queue on Approval (admin_dashboard.py)
✅ Added `queue_approved_video_for_ingestion()` function  
✅ Modified approval callback to automatically queue videos  
✅ Added batch "Approve & Queue All" button  

### 2. Batch Queue Script (NEW)
✅ Created `scripts/batch_queue_approved.py`  
✅ Queues all previously approved videos  
✅ Includes dry-run mode for safety  

### 3. Status Checker (NEW)
✅ Created `scripts/check_video_status.py`  
✅ Shows database, queue, and ChromaDB stats  
✅ Provides actionable recommendations  

## How to Use

### Quick Fix for Your Current Situation
```bash
# Queue all your already-approved videos
python scripts/batch_queue_approved.py
```

### Going Forward
1. **Approve videos normally in the dashboard** - they auto-queue now! ✨
2. **Use batch approve button** for bulk processing
3. **Check status anytime:**
   ```bash
   python scripts/check_video_status.py
   ```

## Testing
```bash
# 1. Check current status
python scripts/check_video_status.py

# 2. Queue approved videos (dry run first)
python scripts/batch_queue_approved.py --dry-run

# 3. Queue for real
python scripts/batch_queue_approved.py

# 4. Monitor workers
docker-compose logs -f embedding_worker

# 5. Check status again
python scripts/check_video_status.py
```

## Files Modified/Created

**Modified:**
- `autodidact/ui/admin_dashboard.py` - Auto-queue on approval

**Created:**
- `scripts/batch_queue_approved.py` - Batch queue script
- `scripts/check_video_status.py` - Status checker
- `docs/VIDEO_APPROVAL_WORKFLOW.md` - Complete workflow guide

## Complete Workflow Now

```
User approves video in dashboard
         ↓
Status updated to 'approved'
         ↓
Transcript fetched (Apify)
         ↓
Message published to RabbitMQ queue 'tasks.video.validated'
         ↓
Embedding worker consumes message
         ↓
Video embedded into ChromaDB
         ↓
✅ Available for curriculum generation!
```

---

**You're all set!** 🎉 Videos approved in the dashboard will now automatically queue and ingest.
