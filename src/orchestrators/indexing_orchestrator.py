import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from typing import Dict, Any, Optional

# Import all agents and utilities
# NOTE: Ensure these import paths match your file structure exactly
from src.scrapers.youtube_spider import get_youtube_transcript 
from src.agents.validation_agent import ValidationAgent
from src.agents.intake_agent import IntakeAgent 

def run_indexing_pipeline(youtube_url: str) -> Optional[Dict[str, Any]]:
    """
    Executes the full Autodidact AI Indexing Pipeline for a single resource:
    Scrape -> Validate/Score -> Ingest/Embed.
    
    Returns:
        The final combined metadata dictionary if successful, or None if rejected/failed.
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

    # 2. VALIDATE: Use the LLM to score the content quality and categorize it
    validator = ValidationAgent()
    validation_data = validator.validate_and_score(content, metadata)

    if not validation_data:
        print("❌ Pipeline Halted: Validation Agent failed to produce structured data.")
        return None

    # Check if the score meets the minimum quality threshold (0.8)
    # The score comes from the 'args' dictionary of the function call
    helpfulness_score = validation_data.get("helpfulness_score", 0.0)
    
    # Ensure score is treated as a float for comparison
    try:
        helpfulness_score = float(helpfulness_score)
    except (TypeError, ValueError):
        print(f"❌ Pipeline Halted: Invalid helpfulness_score received: {helpfulness_score}")
        return None

    if helpfulness_score < 0.8:
        print(f"⚠️ Resource Rejected: Helpfulness score {helpfulness_score:.2f} is below threshold (0.8).")
        return None
    
    print(f"✅ Resource Accepted: Score {helpfulness_score:.2f} is sufficient.")

    # 3. COMBINE METADATA: Merge scraped data with validation data
    # Validation data (LLM tags) takes precedence and includes the score
    final_metadata = {
        **metadata, # Scraped rich data (title, views, channel, etc.)
        **validation_data # LLM-determined quality score, instrument_id, difficulty, technique
    }
    
    # 4. INGEST: Chunk, Embed, and write to ChromaDB
    ingestor = IntakeAgent()
    first_chunk_id = ingestor.process_and_add_document(
        content=content,
        source_url=youtube_url, 
        metadata=final_metadata
    )

    if first_chunk_id:
        print("\n✅ INDEXING PIPELINE COMPLETE. Document Ingested.")
        return final_metadata
    else:
        print("\n❌ INDEXING PIPELINE FAILED at ingestion step.")
        return None

# --- END-TO-END TEST ---
if __name__ == "__main__":
    # Test URL that should succeed (often used for reliable testing)
    test_url_success = "https://www.youtube.com/watch?v=5QjRzD-oUaQ" 
    
    # --- Run the full pipeline ---
    result = run_indexing_pipeline(test_url_success)
    
    if result:
        print("\n--- FINAL INGESTION RESULT SUMMARY ---")
        print(json.dumps({
            "Title": result.get('title'),
            "Score": result.get('helpfulness_score'),
            "Instrument": result.get('instrument_id'),
            "Technique": result.get('technique'),
            "First Chunk ID": result.get('video_id') + "-0" # Manual check of ID format
        }, indent=2))
        
    print("\n" + "="*60)