import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uuid
from typing import List, Dict, Any, Union

# Import the utility functions for our core engines
from src.db_utils.llm_client import get_llm_client
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection, COLLECTION_NAME_V2
from src.models.unified_metadata_schema import UnifiedMetadata

COLLECTION_NAME = COLLECTION_NAME_V2  # Use new v2 collection with 768d embeddings

class IntakeAgent:
  """
  The Intake Agent is responsible for data ingestion, cleaning,
  chunking, and generating initial vector embeddings for storage.
  
  NOW USES:
  - UnifiedMetadata schema for backward compatibility with bot crawler
  - sentence-transformers/all-mpnet-base-v2 (768d) embeddings
  - autodidact_ai_core_v2 collection
  """

  def __init__(self, collection_name: str = COLLECTION_NAME):
    self.chroma_client = get_chroma_client()
    self.llm_client = get_llm_client()
    self.collection_name = collection_name
    self._collection = None

  def _get_or_create_collection(self):
    """Ensures the vector collection exists and returns it."""
    if self._collection is None:
      print(f"Ensuring collection '{self.collection_name}' exists...")
      self._collection = get_or_create_collection(
          client=self.chroma_client,
          collection_name=self.collection_name
      )
    return self._collection

  def process_and_add_document(
      self, 
      content: str, 
      source_url: str, 
      metadata: Union[Dict[str, Any], UnifiedMetadata]
  ) -> str:
    """
    Simulates the full ingestion pipeline: 
    1. Prepares the document (e.g., simple chunking).
    2. Validates metadata against UnifiedMetadata schema.
    3. Adds the document to the collection with 768d embeddings.
    
    Args:
        content: Document text content
        source_url: URL or identifier of source
        metadata: Either UnifiedMetadata instance or dict (will be validated)
    
    Returns:
        Document ID of first chunk
    """
    collection = self._get_or_create_collection()
    
    # --- 1. VALIDATE METADATA ---
    if isinstance(metadata, dict):
      # Convert dict to UnifiedMetadata for validation
      try:
        unified_metadata = UnifiedMetadata(**metadata)
      except Exception as e:
        raise ValueError(f"Invalid metadata: {e}")
    else:
      unified_metadata = metadata
    
    # --- 2. SIMULATED CHUNKING ---
    # For this prototype, we'll treat the whole content as a single chunk.
    # In a real RAG application, you'd use a text splitter (like LangChain's RecursiveCharacterTextSplitter)
    chunks = [content]

    # --- 3. PREPARE DATA FOR CHROMA ---
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for i, chunk in enumerate(chunks):
      # Create a unique ID for each chunk
      chunk_id = f"{unified_metadata.instrument_id}-{str(uuid.uuid4())[:8]}-{i}"
      
      # Convert UnifiedMetadata to ChromaDB-compatible dict
      chunk_metadata = unified_metadata.to_chroma_metadata()
      chunk_metadata["text_length"] = len(chunk)
      
      documents.append(chunk)
      metadatas.append(chunk_metadata)
      ids.append(chunk_id)
    
    # --- 4. ADD TO CHROMA ---
    # Chroma calculates the 768d embeddings using all-mpnet-base-v2
    print(f"Adding {len(documents)} chunk(s) to collection '{self.collection_name}'...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print("✅ Document successfully ingested and embedded with 768d vectors.")
    
    return ids[0] if ids else "No documents added"

# --- EXAMPLE USAGE/TEST ---
if __name__ == "__main__":
    from src.models.unified_metadata_schema import create_manual_metadata, Difficulty
    
    # 1. Define the data we want to ingest (simulating a scraped YouTube transcript)
    sample_content = (
        "The fastest way to master the guitar technique of 'sweeping' is not to play fast, "
        "but to start slowly with a metronome and ensure every note is perfectly clean. "
        "This specific technique requires a single, smooth motion of the pick across three "
        "or more strings, similar to sweeping dust with a broom, hence the name. "
        "Remember to mute the unused strings with your fret hand for a clear sound."
    )
    sample_url = "https://youtube.com/watch?v=gTr1A74xYyY"
    
    # 2. Create UnifiedMetadata using helper function
    sample_metadata = create_manual_metadata(
        instrument_id="MUSIC_ELECTRIC_GUITAR",
        source=sample_url,
        difficulty=Difficulty.ADVANCED,
        text_length=len(sample_content),
        helpfulness_score=0.95,
        technique="sweeping",
        tags=["guitar", "technique", "sweeping", "advanced"]
    )

    try:
        intake_agent = IntakeAgent()
        
        # Process and add the document
        new_doc_id = intake_agent.process_and_add_document(
            content=sample_content,
            source_url=sample_url,
            metadata=sample_metadata
        )
        
        print(f"\n--- Verification ---")
        print(f"Ingested ID: {new_doc_id}")
        
        # Optional: Retrieve the document to verify storage
        collection = intake_agent._get_or_create_collection()
        retrieved = collection.get(ids=[new_doc_id])
        
        print(f"Successfully retrieved metadata: {retrieved['metadatas'][0]}")
        print(f"Successfully retrieved content (first 50 chars): '{retrieved['documents'][0][:50]}...'")
        print(f"\n✅ IntakeAgent upgraded to UnifiedMetadata + 768d embeddings!")

    except Exception as e:
        print(f"\nFATAL ERROR: Intake Agent failed. Details: {e}")
        import traceback
        traceback.print_exc()