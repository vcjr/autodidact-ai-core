"""
Google Cloud Storage Manager for Video Content
===============================================

Stores video transcripts and metadata in GCS to avoid re-fetching from YouTube.

Structure:
- Bucket: autodidact-video-content
- Path: {video_id}/transcript.txt
- Path: {video_id}/metadata.json

Setup:
1. Install: pip install google-cloud-storage
2. Set up GCS credentials:
   - Create a service account with Storage Object Admin role
   - Download JSON key
   - Set GOOGLE_APPLICATION_CREDENTIALS environment variable
   
3. Create bucket:
   gsutil mb gs://autodidact-video-content
   
4. Set in .env:
   GCS_BUCKET_NAME=autodidact-video-content
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

Benefits:
- No re-fetching transcripts (saves Apify costs)
- Fast retrieval for admin dashboard
- Backup of all indexed content
- Easy to migrate or export data
"""

import os
import json
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from google.cloud import storage
from google.oauth2 import service_account


class GCSContentManager:
    """
    Manages video content storage in Google Cloud Storage.
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize GCS content manager.
        
        Args:
            bucket_name: GCS bucket name (or use GCS_BUCKET_NAME env var)
            credentials_path: Path to service account JSON (or use GOOGLE_APPLICATION_CREDENTIALS)
        """
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME', 'autodidact-video-content')
        
        # Initialize GCS client
        credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.client = storage.Client(credentials=credentials)
        else:
            # Use default credentials (works on GCP)
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(self.bucket_name)
        
        print(f"✅ GCS Content Manager initialized (bucket: {self.bucket_name})")
    
    def _get_transcript_path(self, video_id: str) -> str:
        """Get GCS path for transcript."""
        return f"{video_id}/transcript.txt"
    
    def _get_metadata_path(self, video_id: str) -> str:
        """Get GCS path for metadata."""
        return f"{video_id}/metadata.json"
    
    def store_video_content(
        self,
        video_id: str,
        transcript: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store video transcript and metadata in GCS.
        
        Args:
            video_id: YouTube video ID
            transcript: Full video transcript
            metadata: Video metadata dict
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add storage timestamp
            storage_metadata = {
                **metadata,
                'stored_at': datetime.utcnow().isoformat(),
                'video_id': video_id
            }
            
            # Store transcript
            transcript_blob = self.bucket.blob(self._get_transcript_path(video_id))
            transcript_blob.upload_from_string(
                transcript,
                content_type='text/plain; charset=utf-8'
            )
            
            # Store metadata
            metadata_blob = self.bucket.blob(self._get_metadata_path(video_id))
            metadata_blob.upload_from_string(
                json.dumps(storage_metadata, indent=2),
                content_type='application/json'
            )
            
            print(f"   ✅ Stored content for {video_id} in GCS")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to store {video_id} in GCS: {e}")
            return False
    
    def retrieve_video_content(
        self,
        video_id: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Retrieve video transcript and metadata from GCS.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Tuple of (transcript, metadata) or (None, None) if not found
        """
        try:
            # Check if content exists
            transcript_blob = self.bucket.blob(self._get_transcript_path(video_id))
            metadata_blob = self.bucket.blob(self._get_metadata_path(video_id))
            
            if not transcript_blob.exists() or not metadata_blob.exists():
                return None, None
            
            # Download content
            transcript = transcript_blob.download_as_text()
            metadata_json = metadata_blob.download_as_text()
            metadata = json.loads(metadata_json)
            
            print(f"   ✅ Retrieved content for {video_id} from GCS")
            return transcript, metadata
            
        except Exception as e:
            print(f"   ⚠️  Failed to retrieve {video_id} from GCS: {e}")
            return None, None
    
    def content_exists(self, video_id: str) -> bool:
        """
        Check if video content exists in GCS.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if both transcript and metadata exist
        """
        transcript_blob = self.bucket.blob(self._get_transcript_path(video_id))
        metadata_blob = self.bucket.blob(self._get_metadata_path(video_id))
        
        return transcript_blob.exists() and metadata_blob.exists()
    
    def delete_video_content(self, video_id: str) -> bool:
        """
        Delete video content from GCS.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if successful
        """
        try:
            transcript_blob = self.bucket.blob(self._get_transcript_path(video_id))
            metadata_blob = self.bucket.blob(self._get_metadata_path(video_id))
            
            if transcript_blob.exists():
                transcript_blob.delete()
            if metadata_blob.exists():
                metadata_blob.delete()
            
            print(f"   ✅ Deleted content for {video_id} from GCS")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to delete {video_id} from GCS: {e}")
            return False
    
    def list_stored_videos(self, prefix: str = "") -> list:
        """
        List all stored video IDs.
        
        Args:
            prefix: Optional prefix to filter by
            
        Returns:
            List of video IDs
        """
        video_ids = set()
        
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        for blob in blobs:
            # Extract video_id from path (format: {video_id}/...)
            parts = blob.name.split('/')
            if len(parts) >= 2:
                video_ids.add(parts[0])
        
        return sorted(list(video_ids))
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dict with stats (total_videos, total_size_mb, etc.)
        """
        blobs = list(self.client.list_blobs(self.bucket_name))
        
        total_size = sum(blob.size for blob in blobs)
        video_ids = set()
        
        for blob in blobs:
            parts = blob.name.split('/')
            if len(parts) >= 2:
                video_ids.add(parts[0])
        
        return {
            'total_videos': len(video_ids),
            'total_files': len(blobs),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 3),
        }


# Singleton instance
_gcs_manager = None


def get_gcs_manager() -> GCSContentManager:
    """Get or create GCS content manager singleton."""
    global _gcs_manager
    if _gcs_manager is None:
        _gcs_manager = GCSContentManager()
    return _gcs_manager


# ============================================================================
# HELPER FUNCTIONS FOR EXISTING CODE
# ============================================================================

def store_video_in_gcs(video_id: str, transcript: str, metadata: dict) -> bool:
    """
    Convenience function to store video content.
    
    Args:
        video_id: YouTube video ID
        transcript: Full transcript text
        metadata: Video metadata dict
        
    Returns:
        True if successful
    """
    manager = get_gcs_manager()
    return manager.store_video_content(video_id, transcript, metadata)


def retrieve_video_from_gcs(video_id: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Convenience function to retrieve video content.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Tuple of (transcript, metadata) or (None, None) if not found
    """
    manager = get_gcs_manager()
    return manager.retrieve_video_content(video_id)


def video_exists_in_gcs(video_id: str) -> bool:
    """
    Convenience function to check if video exists in GCS.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        True if video content exists
    """
    manager = get_gcs_manager()
    return manager.content_exists(video_id)


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("=" * 80)
    print("GCS Content Manager Demo")
    print("=" * 80)
    
    # Initialize manager
    manager = GCSContentManager()
    
    # Get stats
    print("\n📊 Storage Statistics:")
    stats = manager.get_storage_stats()
    print(f"   Videos stored: {stats['total_videos']}")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']} MB ({stats['total_size_gb']} GB)")
    
    # List videos
    print("\n📹 Stored Videos:")
    videos = manager.list_stored_videos()
    print(f"   Found {len(videos)} videos")
    for i, video_id in enumerate(videos[:10], 1):
        print(f"   {i}. {video_id}")
    
    if len(videos) > 10:
        print(f"   ... and {len(videos) - 10} more")
    
    print("\n" + "=" * 80)
