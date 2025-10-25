import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
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
  """
  def __init__(self):
    self.client = get_llm_client()
    self.model_name = "gemini-2.5-flash" # Fast and effective for structured output

  def generate_scope_filter(self, user_query: str) -> dict:
    """
    Generates a ChromaDB filter dictionary based on the user's request.
    
    The filter is designed to target instrument, difficulty, and
    only high-quality, 'helpful' documents (helpfulness_score >= 0.8).
    
    Example Output:
    {
      "instrument_id": "electric_guitar",
      "difficulty": "advanced"
    }
    """
    
    # 1. Define the desired structured output using a Pydantic schema (or in this case, a JSON schema hint)
    # Note: While the Google GenAI SDK supports Pydantic for function calling, 
    # we'll use a strong prompt for simple structured JSON for this prototype.
    
    json_schema_hint = {
      "type": "object",
      "properties": {
          "instrument_id": {
              "type": "string", 
              "description": "The primary instrument the user wants to learn (e.g., 'electric_guitar', 'piano')."},
          "difficulty": {
              "type": "string", 
              "description": "The skill level requested (e.g., 'beginner', 'intermediate', 'advanced')."}
      },
      "required": ["instrument_id", "difficulty"]
    }
    
    # 2. Construct the system prompt
    system_prompt = (
      "You are the Scope Agent for the Autodidact AI curriculum generator. "
      "Your task is to analyze the user's request and extract the core **instrument** "
      "and **difficulty** level. Your response MUST be a single JSON object that "
      "matches the provided schema hint. Do not include any other text or explanation."
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
      print("Scope Agent: Analysis complete.")
      return filter_data
      
    except Exception as e:
      print(f"❌ Scope Agent failed to generate filter: {e}")
      return {"error": str(e)}

  def build_chroma_where_filter(self, user_query: str) -> dict:
    """
    Converts the LLM-generated scope data into a full ChromaDB 'where' filter 
    that includes the critical helpfulness_score check.
    """
    # Get the scope data (instrument_id, difficulty)
    scope_data = self.generate_scope_filter(user_query)
    
    # Check for errors in the LLM output
    if "error" in scope_data:
        return scope_data

    # ChromaDB 'where' filter requires a specific syntax. 
    # We combine the LLM output with our predetermined quality filter.
    chroma_filter = {
      "$and": [
          {"instrument_id": scope_data["instrument_id"]},
          {"difficulty": scope_data["difficulty"]},
          # CRITICAL VALUE-ADD: Filter out low-quality content
          {"helpfulness_score": {"$gte": 0.8}} 
      ]
    }
    
    print(f"Generated ChromaDB Filter: {chroma_filter}")
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