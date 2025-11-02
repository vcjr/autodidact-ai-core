# GCS Storage Setup Guide

## Why GCS?

Storing video transcripts and metadata in Google Cloud Storage:
- **Saves money**: No re-fetching from Apify ($0.25 per 1000 videos adds up!)
- **Faster**: Instant retrieval vs. waiting for API calls
- **Reliable**: Your data is backed up and always available
- **Scalable**: GCS is dirt cheap ($0.02/GB/month)

## Cost Comparison

**Without GCS:**
- Re-fetch 1000 videos from Apify: **$0.25**
- Do this 10 times during testing/review: **$2.50**

**With GCS:**
- Store 1000 video transcripts (~500MB): **$0.01/month**
- Retrieve unlimited times: **FREE** (egress is negligible)

## Setup Steps

### 1. Install Google Cloud SDK (Optional, for CLI)

```bash
# macOS
brew install --cask google-cloud-sdk

# Initialize
gcloud init
```

### 2. Install Python Library

```bash
pip install google-cloud-storage
```

### 3. Create GCS Bucket

**Option A: Using Web Console**
1. Go to https://console.cloud.google.com/storage
2. Click "Create Bucket"
3. Name: `autodidact-video-content` (or your choice)
4. Location: Choose nearest region (e.g., `us-central1`)
5. Storage class: Standard
6. Access control: Uniform
7. Create

**Option B: Using CLI**
```bash
# Create bucket
gsutil mb -l us-central1 gs://autodidact-video-content

# Verify
gsutil ls
```

### 4. Set Up Authentication

**Option A: Service Account (Recommended for Production)**

1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "Create Service Account"
3. Name: `autodidact-storage`
4. Role: `Storage Object Admin`
5. Click "Create Key" → JSON
6. Download the JSON file

Save to your project:
```bash
mkdir -p ~/.config/gcloud
mv ~/Downloads/autodidact-*.json ~/.config/gcloud/autodidact-storage-key.json
```

Add to `.env`:
```bash
GCS_BUCKET_NAME=autodidact-video-content
GOOGLE_APPLICATION_CREDENTIALS=/Users/YOUR_USERNAME/.config/gcloud/autodidact-storage-key.json
```

**Option B: User Credentials (Development Only)**

```bash
# Login
gcloud auth application-default login

# Add to .env
GCS_BUCKET_NAME=autodidact-video-content
# No GOOGLE_APPLICATION_CREDENTIALS needed - uses default
```

### 5. Test the Setup

```bash
python src/storage/gcs_manager.py
```

Should output:
```
✅ GCS Content Manager initialized (bucket: autodidact-video-content)
📊 Storage Statistics:
   Videos stored: 0
   Total files: 0
   Total size: 0.0 MB (0.0 GB)
```

### 6. Verify Integration

The storage layer is now integrated into:

1. **Transcription Worker** - Automatically stores transcripts after fetching
2. **Admin Dashboard** - Retrieves from GCS (no API calls!)
3. **Queue Scripts** - Checks GCS before re-fetching

Test it:
```bash
# Process a video (will store in GCS)
# ... existing workflow ...

# Check if stored
python -c "
from src.storage.gcs_manager import video_exists_in_gcs
print(video_exists_in_gcs('YOUR_VIDEO_ID'))
"
```

## Usage Examples

### Store Video Content

```python
from src.storage.gcs_manager import store_video_in_gcs

video_id = "dQw4w9WgXcQ"
transcript = "Full video transcript here..."
metadata = {
    "title": "Video Title",
    "channel_name": "Channel Name",
    "views": 1000000,
    # ... more metadata
}

store_video_in_gcs(video_id, transcript, metadata)
```

### Retrieve Video Content

```python
from src.storage.gcs_manager import retrieve_video_from_gcs

video_id = "dQw4w9WgXcQ"
transcript, metadata = retrieve_video_from_gcs(video_id)

if transcript:
    print(f"Got transcript: {len(transcript)} chars")
    print(f"Metadata: {metadata}")
else:
    print("Video not in GCS")
```

### Check if Video Exists

```python
from src.storage.gcs_manager import video_exists_in_gcs

if video_exists_in_gcs("dQw4w9WgXcQ"):
    print("Video already stored!")
else:
    print("Need to fetch and store")
```

### Get Storage Stats

```python
from src.storage.gcs_manager import get_gcs_manager

manager = get_gcs_manager()
stats = manager.get_storage_stats()

print(f"Total videos: {stats['total_videos']}")
print(f"Storage used: {stats['total_size_mb']} MB")
```

## Monitoring

### Check what's stored

```bash
# List all videos in bucket
gsutil ls gs://autodidact-video-content/

# Check storage size
gsutil du -sh gs://autodidact-video-content/

# View specific video metadata
gsutil cat gs://autodidact-video-content/VIDEO_ID/metadata.json
```

### Using Python

```bash
python src/storage/gcs_manager.py
```

## Troubleshooting

### Error: "Could not load credentials"

**Fix:**
```bash
# Check credentials path
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verify file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Re-login if using default credentials
gcloud auth application-default login
```

### Error: "Bucket does not exist"

**Fix:**
```bash
# Create bucket
gsutil mb -l us-central1 gs://autodidact-video-content

# Or update .env with correct bucket name
GCS_BUCKET_NAME=your-actual-bucket-name
```

### Error: "Permission denied"

**Fix:**
- Make sure service account has `Storage Object Admin` role
- Or use `gcloud auth application-default login`

## Migration Script

If you already have videos indexed, migrate them to GCS:

```python
# scripts/migrate_to_gcs.py (create this if needed)
from autodidact.database import database_utils
from src.storage.gcs_manager import store_video_in_gcs, video_exists_in_gcs
from src.scrapers.youtube_transcript_fetcher import get_youtube_transcript

conn = database_utils.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT video_id, video_url FROM videos WHERE status != 'rejected'")

for video_id, video_url in cur.fetchall():
    if not video_exists_in_gcs(video_id):
        print(f"Migrating {video_id}...")
        content, metadata = get_youtube_transcript(video_url, scraper='apify')
        if content:
            store_video_in_gcs(video_id, content, metadata)
        else:
            print(f"  ⚠️  Failed to fetch {video_id}")
```

## Cost Estimation

**Typical video:**
- Transcript: ~50 KB
- Metadata: ~5 KB
- Total: ~55 KB per video

**For 1000 videos:**
- Storage: ~55 MB
- Cost: $0.001/month 🎉

**Comparison:**
- Re-fetching 1000 videos once: $0.25
- GCS storage for 20 years: $0.24

**Winner: GCS by a landslide!**

---

You're now set up with a cost-effective, fast content storage layer! 🚀
