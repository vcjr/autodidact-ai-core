import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from typing import Optional
from google import generativeai
from google.genai import types

# Import our LLM Client
from src.db_utils.llm_client import get_llm_client
from src.db_utils.chroma_client import get_chroma_client

class ScopeAgent:
  """
  The Scope Agent uses an LLM to analyze a user query and determine 
  the necessary metadata filters for efficient, targeted vector retrieval 
  from ChromaDB. This ensures only high-quality, relevant documents are searched.
  
  NOW SUPPORTS:
  - UnifiedMetadata schema with domain_id/subdomain_id
  - Backward compatibility with instrument_id
  - Flexible filtering for both new and legacy data
  """
  def __init__(self):
    self.client = get_llm_client()
    self.model_name = "gemini-2.5-flash" # Fast and effective for structured output

  def generate_scope_filter(self, user_query: str) -> dict:
    """
    Generates metadata filters based on the user's request.
    
    NOW EXTRACTS:
    - domain_id (e.g., "MUSIC")
    - subdomain_id (e.g., "ELECTRIC_GUITAR")  
    - difficulty (e.g., "advanced")
    - instrument_id (for backward compatibility)
    
    The LLM will extract domain and subdomain, and we'll auto-generate
    instrument_id for backward compatibility with legacy queries.
    
    Example Output:
    {
      "domain_id": "MUSIC",
      "subdomain_id": "ELECTRIC_GUITAR",
      "instrument_id": "MUSIC_ELECTRIC_GUITAR",
      "difficulty": "advanced"
    }
    """
    
    # 1. Updated JSON schema to extract domain and subdomain
    json_schema_hint = {
      "type": "object",
      "properties": {
          "domain_id": {
              "type": "string", 
              "description": "The top-level domain (e.g., 'MUSIC', 'CODING_SOFTWARE', 'LANGUAGES'). Use uppercase."},
          "subdomain_id": {
              "type": "string", 
              "description": "The specific subdomain/instrument within the domain (e.g., 'ELECTRIC_GUITAR', 'PIANO', 'PYTHON'). Use uppercase. Optional."},
          "difficulty": {
              "type": "string", 
              "description": "The skill level requested (e.g., 'beginner', 'intermediate', 'advanced'). Use lowercase."}
      },
      "required": ["domain_id", "difficulty"]
    }
    
    # 2. Updated system prompt to guide extraction
    system_prompt = (
      "You are the Scope Agent for the Autodidact AI curriculum generator. "
      "Your task is to analyze the user's request and extract:\n"
      "1. The **domain_id**: The broad category (e.g., MUSIC, CODING_SOFTWARE, LANGUAGES)\n"
      "2. The **subdomain_id**: The specific topic within that domain (e.g., ELECTRIC_GUITAR for MUSIC, PYTHON for CODING_SOFTWARE)\n"
      "3. The **difficulty**: The skill level (beginner, intermediate, or advanced)\n\n"
      "Use UPPERCASE for domain_id and subdomain_id, lowercase for difficulty.\n"
      "Your response MUST be a single JSON object matching the schema. No explanations."
    )

    # 3. Call the Gemini API for structured generation
    try:
      print(f"Scope Agent: Analyzing query for filter generation...")
      response = self.client.generate_content(
          contents=[system_prompt, f"User Query: {user_query}"],
          generation_config={
              "response_mime_type": "application/json",
              "response_schema": json_schema_hint
          }
      )
      
      # 4. Parse the structured JSON response
      filter_data = json.loads(response.text)
      
      # 5. Auto-generate instrument_id for backward compatibility
      if filter_data.get("subdomain_id"):
        filter_data["instrument_id"] = f"{filter_data['domain_id']}_{filter_data['subdomain_id']}"
      else:
        filter_data["instrument_id"] = filter_data["domain_id"]
      
      print(f"Scope Agent: Extracted filters - {filter_data}")
      return filter_data
      
    except Exception as e:
      print(f"❌ Scope Agent failed to generate filter: {e}")
      return {"error": str(e)}

  def build_chroma_where_filter(self, user_query: str) -> dict:
    """
    Converts the LLM-generated scope data into a full ChromaDB 'where' filter 
    that includes the critical helpfulness_score check.
    
    SUPPORTS BOTH:
    - New schema: domain_id + subdomain_id filtering
    - Legacy schema: instrument_id filtering
    
    The filter will work for both old and new data in the collection.
    """
    # Get the scope data (domain_id, subdomain_id, difficulty)
    scope_data = self.generate_scope_filter(user_query)
    
    # Check for errors in the LLM output
    if "error" in scope_data:
        return scope_data

    # Build filter with both new and legacy support
    filter_conditions = []
    
    # Option 1: Use new schema (domain_id + subdomain_id) if available
    if scope_data.get("domain_id"):
        filter_conditions.append({"domain_id": scope_data["domain_id"]})
        
        if scope_data.get("subdomain_id"):
            filter_conditions.append({"subdomain_id": scope_data["subdomain_id"]})
    
    # Option 2: Also support legacy instrument_id for backward compatibility
    # This OR condition allows matching either new or old schema
    if scope_data.get("instrument_id"):
        # Create an $or condition to match either new schema or legacy schema
        filter_conditions.append({"instrument_id": scope_data["instrument_id"]})
    
    # Add difficulty filter
    filter_conditions.append({"difficulty": scope_data["difficulty"]})
    
    # CRITICAL VALUE-ADD: Filter out low-quality content
    filter_conditions.append({"helpfulness_score": {"$gte": 0.8}})
    
    # Combine all conditions
    chroma_filter = {"$and": filter_conditions}
    
    print(f"Generated ChromaDB Filter: {json.dumps(chroma_filter, indent=2)}")
    return chroma_filter

# --- EXAMPLE USAGE/TEST ---
if __name__ == "__main__":
    
  # 1. Define a user query that needs to be scoped
  test_query = "Create a learning path for Electric Guitar focusing on advanced techniques for sweeping."

  try:
      scope_agent = ScopeAgent()
      
      # 2. Run the agent to generate the full retrieval filter
      final_filter = scope_agent.build_chroma_where_filter(test_query)
      
      print("\n--- Scope Agent Test Result ---")
      print(json.dumps(final_filter, indent=4))
      
      # You would then pass this 'final_filter' to your Retrieval Agent 
      # to filter the collection query.

  except Exception as e:
      print(f"\nFATAL ERROR: Scope Agent failed during execution. Details: {e}")