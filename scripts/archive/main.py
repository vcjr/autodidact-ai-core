import os
from src.agents.question_agent import QuestionAgent
from dotenv import load_dotenv

load_dotenv()

def run_curriculum_generator(query: str):
  """
  Main function to run the full Autodidact AI RAG pipeline.
  """
  try:
    # 1. Initialize the QuestionAgent (which initializes ScopeAgent)
    generator = QuestionAgent()
    
    print(f"\n--- Starting Autodidact AI RAG Process ---")
    print(f"User Query: {query}")

    # 2. Run the full RAG pipeline: Scope -> Retrieve -> Augment -> Generate
    curriculum = generator.generate_curriculum(query)
    
    print("\n" + "="*70)
    print("✅ FINAL CUSTOMIZED CURRICULUM GENERATED")
    print("="*70)
    print(curriculum)
    print("="*70)
  except Exception as e:
    print(f"\nFATAL ORCHESTRATION ERROR: Failed to run the curriculum generator. Details: {e}")
    # Hint to check core dependencies
    if not os.getenv("GEMINI_API_KEY"):
          print("HINT: GEMINI_API_KEY is missing from environment. Check your .env file.")

if __name__ == "__main__":
  # --- Test Case 1: Advanced Guitar (Matches Ingested Data) ---
  guitar_query = "Create a learning path for Electric Guitar focusing on advanced techniques for sweeping."
  run_curriculum_generator(guitar_query)
  
  # --- Test Case 2: Beginner Piano (Should return 'No documents found') ---
  print("\n\n" + "-"*70)
  piano_query = "Give me a curriculum for beginner piano scales and chords."
  run_curriculum_generator(piano_query)