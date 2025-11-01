import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from typing import Dict, Any, Optional

# Import all agents and utilities
from src.scrapers.youtube_spider import get_youtube_transcript 
from src.agents.validation_agent import ValidationAgent
from src.agents.intake_agent import IntakeAgent 
from autodidact.database import database_utils # Import the new database utilities

def run_indexing_pipeline(youtube_url: str) -> Optional[Dict[str, Any]]:
    """
    Executes the full Autodidact AI Indexing Pipeline for a single resource.
    This version includes logging all scraped videos to a persistent database.
    """
    print("="*60)
    print(f"STARTING INDEXING FOR URL: {youtube_url}")
    print("="*60)

    # 1. SCRAPE: Get raw text and rich metadata
    print("PHASE 1: Scraping YouTube content...")
    content, metadata = get_youtube_transcript(youtube_url)

    if not content or not metadata:
        print("❌ Pipeline Halted: Failed to scrape content or metadata.")
        return None

    # --- NEW: Log all scraped videos to PostgreSQL database ---
    try:
        print("PHASE 1.5: Logging video metadata to persistent database...")
        database_utils.log_channel_and_video(metadata)
        print(f"✅ Successfully logged video '{metadata.get('title')}' for tracking.")
    except Exception as e:
        print(f"❌ CRITICAL: Failed to log video to PostgreSQL. Error: {e}")
        # Halt the pipeline if we can't even log the initial record.
        return None
    # ---------------------------------------------------------

    # 2. VALIDATE: Use the LLM to score the content quality and categorize it
    print("PHASE 2: Validating content with ValidationAgent...")
    validator = ValidationAgent()
    validation_data = validator.validate_and_score(content, metadata)

    if not validation_data:
        print("❌ Pipeline Halted: Validation Agent failed to produce structured data.")
        # Update status to reflect the error
        database_utils.update_video_status(metadata['video_id'], 'error_validation', reason="Validation agent failed.")
        return None

    helpfulness_score = validation_data.get("helpfulness_score", 0.0)
    video_id = metadata.get('video_id')
    
    try:
        helpfulness_score = float(helpfulness_score)
    except (TypeError, ValueError):
        print(f"❌ Pipeline Halted: Invalid helpfulness_score received: {helpfulness_score}")
        database_utils.update_video_status(video_id, 'error_validation', reason=f"Invalid score format: {helpfulness_score}")
        return None

    # --- MODIFIED: Decision point now updates status instead of discarding ---
    if helpfulness_score < 0.8:
        rejection_reason = f"Helpfulness score {helpfulness_score:.2f} is below threshold (0.8)."
        print(f"⚠️ Resource Pended: {rejection_reason}")
        database_utils.update_video_status(video_id, 'pending_review', score=helpfulness_score, reason=rejection_reason)
        return None # Stop the pipeline for this video, it's now in the review queue
    
    print(f"✅ Resource Accepted: Score {helpfulness_score:.2f} is sufficient.")
    database_utils.update_video_status(video_id, 'approved', score=helpfulness_score, reason="Passed quality threshold.")
    # ----------------------------------------------------------------------

    # 3. COMBINE METADATA: Merge scraped data with validation data
    final_metadata = {
        **metadata,
        **validation_data
    }
    
    # 4. INGEST: Chunk, Embed, and write to ChromaDB
    print("PHASE 3: Ingesting document into ChromaDB...")
    ingestor = IntakeAgent()
    first_chunk_id = ingestor.process_and_add_document(
        content=content,
        source_url=youtube_url, 
        metadata=final_metadata
    )

    if first_chunk_id:
        print("\n✅ INDEXING PIPELINE COMPLETE. Document Ingested.")
        database_utils.update_video_status(video_id, 'ingested') # Final status update
        return final_metadata
    else:
        print("\n❌ INDEXING PIPELINE FAILED at ingestion step.")
        database_utils.update_video_status(video_id, 'error_ingestion', reason="IntakeAgent failed.")
        return None

# --- END-TO-END TEST ---
if __name__ == "__main__":
    # Test URL that should be approved
    print("--- RUNNING SUCCESS CASE ---")
    test_url_success = "https://www.youtube.com/watch?v=vpn4qv4A1Aw" 
    run_indexing_pipeline(test_url_success)

    if result:
        print("\n--- FINAL INGESTION RESULT SUMMARY ---")
        print(json.dumps({
            "Title": result.get('title'),
            "Score": result.get('helpfulness_score'),
            "Instrument": result.get('instrument_id'),
            "Technique": result.get('technique'),
            "First Chunk ID": result.get('video_id') + "-0"
        }, indent=2))
    
    print("\n" + "="*60 + "\n")

    # Test URL that should be sent to the review queue
    # Assuming a low-quality or irrelevant video would get a low score
    print("--- RUNNING PENDING REVIEW CASE ---")
    test_url_pending = "https://www.youtube.com/watch?v=afRiqumTOPA"
    run_indexing_pipeline(test_url_pending)
        
    print("\n" + "="*60)