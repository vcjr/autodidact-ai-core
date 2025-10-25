import re
import logging
from typing import Optional, Tuple, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) 

def extract_youtube_id(url: str) -> Optional[str]:
  """Extracts the unique YouTube video ID from a common URL format."""
  logger.debug(f"Extracting video ID from URL: {url}")
  youtube_regex = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([\w-]{11})'
  match = re.search(youtube_regex, url)
  video_id = match.group(1) if match else None
  logger.debug(f"Extracted video ID: {video_id}")
  return video_id

def get_youtube_transcript(url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
  """
  Fetches the transcript text, video title, and rich metadata for a given YouTube URL.
  
  Returns:
      A tuple of (transcript_text, metadata_dict).
  """
  logger.info(f"Starting transcript fetch for URL: {url}")
  video_id = extract_youtube_id(url)
  if not video_id:
    logger.error(f"Could not extract video ID from URL: {url}")
    print(f"Error: Could not extract video ID from URL: {url}")
    return None, None

  logger.info(f"Processing video ID: {video_id}")

  try:
    # Initialize the YouTubeTranscriptApi client instance
    logger.debug("Initializing YouTubeTranscriptApi instance")
    ytt_api = YouTubeTranscriptApi()
    logger.debug("YouTubeTranscriptApi instance created")
    
    # 1. Fetch Transcript using the CORRECTED API CALL: instance.list(video_id)
    logger.debug(f"Fetching transcript list for video ID: {video_id}")
    transcript_list = ytt_api.list(video_id)
    logger.debug(f"Transcript list fetched successfully. Available transcripts: {len(transcript_list._manually_created_transcripts) + len(transcript_list._generated_transcripts)}")
    
    # Prioritize English ('en'), then fall back to the first available transcript
    try:
      # find_transcript is a method of the TranscriptList object
      logger.debug("Attempting to find English ('en') transcript")
      transcript = transcript_list.find_transcript(['en'])
      logger.info(f"Found English transcript for video {video_id}")
    except:
      # Fallback to the first available transcript if 'en' is not found
      logger.warning("English transcript not found, falling back to first available transcript")
      transcript = transcript_list[0]
      logger.info(f"Using fallback transcript with language: {transcript.language_code}")

    logger.debug(f"Fetching transcript content...")
    fetched_transcript = transcript.fetch()
    logger.debug(f"Transcript content fetched. Number of items: {len(fetched_transcript)}")

    # Combine the list of transcript snippets into a single string
    transcript_text = " ".join([item.text for item in fetched_transcript])
    logger.info(f"Transcript text combined. Total characters: {len(transcript_text)}")

    # 2. Prepare Enhanced Metadata from the transcript API
    logger.debug("Gathering video metadata from transcript API")
    
    # Extract video title from the transcript list metadata if available
    video_title = getattr(transcript_list, 'video_title', None) or f"Video {video_id}"
    
    metadata = {
      "source_url": url,
      "video_id": video_id,
      "title": video_title,
      "language": transcript.language_code, 
      "is_generated": transcript.is_generated,
      "transcript_language": transcript.language,
      "is_translatable": transcript.is_translatable
    }
    logger.debug(f"Metadata gathered: {metadata}")
    
    logger.info(f"SUCCESS: Fetched video '{video_title}' with {len(transcript_text)} characters.")
    print(f"Scraper: Success. Fetched video '{video_title}' with {len(transcript_text)} characters.")
    return transcript_text, metadata

  except TranscriptsDisabled as e:
    logger.error(f"Transcripts are disabled for video ID: {video_id}. Exception: {e}")
    print(f"Error: Transcripts are disabled for video ID: {video_id}")
    return None, None
  except Exception as e:
    logger.exception(f"Unexpected error fetching resource for video ID {video_id}: {e}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error(f"Error details: {str(e)}")
    print(f"Error fetching resource for video ID {video_id}: {e}")
    return None, None

# Test the scraper in isolation
if __name__ == "__main__":
  # A URL for a popular video with a known transcript
  test_url = "https://www.youtube.com/watch?v=gKVjC7RPBrU"
  logger.info("="*60)
  logger.info("Starting YouTube Spider Test")
  logger.info("="*60)
  transcript, metadata = get_youtube_transcript(test_url)
  
  if transcript and metadata:
    logger.info("="*60)
    logger.info("Test completed successfully")
    logger.info("="*60)
    print("\n--- Scraper Test Result (Enhanced Metadata) ---")
    print(f"Title: {metadata['title']}")
    print(f"Video ID: {metadata['video_id']}")
    print(f"Language: {metadata['language']}")
    print(f"Is Generated: {metadata['is_generated']}")
    print(f"Transcript Length: {len(transcript)} characters")
    print(f"Snippet: {transcript[:100]}...")
  else:
    logger.error("="*60)
    logger.error("Test failed - no transcript or metadata returned")
    logger.error("="*60)