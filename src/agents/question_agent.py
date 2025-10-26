import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import textwrap
from google import generativeai
from src.db_utils.llm_client import get_llm_client
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection, COLLECTION_NAME_V2
from src.agents.scope_agent import ScopeAgent

# Use v2 collection with 768d embeddings and UnifiedMetadata schema
COLLECTION_NAME = COLLECTION_NAME_V2

# --- 1. RETRIEVAL AGENT LOGIC (Integrated into the RAG class) ---

class QuestionAgent:
  """
  The Question Agent (the final RAG generator) executes the full workflow:
  1. Scopes the user query (Scope Agent).
  2. Retrieves filtered, relevant context (Retrieval Agent).
  3. Generates the custom curriculum using the augmented context.
  
  NOW USES:
  - autodidact_ai_core_v2 collection (768d embeddings)
  - UnifiedMetadata schema with domain_id/subdomain_id
  - Enhanced context formatting with new metadata fields
  """
  def __init__(self, collection_name: str = COLLECTION_NAME):
    self.llm_client = get_llm_client()
    self.chroma_client = get_chroma_client()
    self.scope_agent = ScopeAgent()
    self.collection_name = collection_name
    
    # Load the v2 collection with 768d embeddings
    self.collection = get_or_create_collection(
        self.chroma_client, 
        self.collection_name
    )
    self.llm_model = "gemini-2.5-flash" # Use a capable model for generation

  def _retrieve_context(self, query: str, chroma_filter: dict, k: int = 5) -> str:
    """
    Retrieval Agent's core function: Queries ChromaDB with a filter and returns context.
    Now uses UnifiedMetadata schema fields for enhanced context formatting.
    """
    print(f"\nRetrieval Agent: Searching for top {k} documents...")
    
    # 1. Execute the filtered vector search
    results = self.collection.query(
        query_texts=[query],
        n_results=k,
        where=chroma_filter 
        # The 'where' filter ensures only high-quality, relevant documents are considered
    )
    
    # 2. Format the retrieved documents into a context string with new metadata
    context_parts = []
    
    for doc, meta in zip(results.get('documents', [[]])[0], results.get('metadatas', [[]])[0]):
        # Extract UnifiedMetadata fields
        source = meta.get('source', 'N/A')
        domain_id = meta.get('domain_id', 'N/A')
        subdomain_id = meta.get('subdomain_id', 'N/A')
        technique = meta.get('technique', 'N/A')
        platform = meta.get('platform', 'N/A')
        difficulty = meta.get('difficulty', 'N/A')
        quality_score = meta.get('helpfulness_score', meta.get('quality_score', 'N/A'))
        
        # Format the context for the LLM with enhanced metadata
        context_parts.append(
            f"-- [Source: {source} | Platform: {platform} | Domain: {domain_id}/{subdomain_id}] --\n"
            f"[Difficulty: {difficulty} | Quality Score: {quality_score} | Technique: {technique}]\n"
            f"{doc}"
        )

    context = "\n\n".join(context_parts)
    print(f"Retrieval Agent: Found {len(context_parts)} high-quality context chunks.")
    
    return context

  def generate_curriculum(self, user_query: str) -> str:
    """
    Question Agent's core function: Executes the full RAG process.
    """
    # 1. SCOPE: Get the filtering criteria
    chroma_filter = self.scope_agent.build_chroma_where_filter(user_query)
    
    # Simple error check on the filter generation
    if "error" in chroma_filter:
          return f"Error in RAG workflow (Scope Agent): {chroma_filter['error']}"

    # 2. RETRIEVE: Get the context using the filter
    context = self._retrieve_context(user_query, chroma_filter)

    if not context:
        return "Curriculum Generation Failed: Could not find any high-quality, relevant documents in the database."

    # 3. GENERATE: Create the augmented prompt
    system_prompt = textwrap.dedent("""
      You are the Autodidact AI Curriculum Generator. 
      Your goal is to act as an expert music instructor.
      
      Based ONLY on the provided context, you must generate a structured, multi-step 
      learning roadmap (a curriculum) to address the user's request. 
      
      The curriculum must be step-by-step and cite the exact source URL 
      for each piece of advice from the context.
      
      User Request: {query}
      
      Context (Retrieved High-Quality Documents):
      ---
      {context}
      ---
    """).strip()
    
    # 4. Final LLM Call for Curriculum Generation
    print("\nQuestion Agent: Generating final curriculum...")
    
    response = self.llm_client.generate_content(
      contents=[system_prompt.format(query=user_query, context=context)]
    )
    
    return response.text

# --- END-TO-END TEST ---
if __name__ == "__main__":
    
  # NOTE: The Intake Agent test must have run successfully prior to this test 
  # for the collection and the single document to exist.
  
  test_query = "Create a learning path for Electric Guitar focusing on advanced techniques for sweeping."
  
  try:
    # Initialize the final agent
    question_agent = QuestionAgent()
    
    # Run the full RAG pipeline
    curriculum = question_agent.generate_curriculum(test_query)
    
    print("\n" + "="*50)
    print("FINAL CUSTOMIZED CURRICULUM")
    print("="*50)
    print(curriculum)
    print("="*50)

  except Exception as e:
    print(f"\nFATAL ERROR: Question Agent failed. Details: {e}")