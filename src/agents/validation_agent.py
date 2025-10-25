import sys
import os
import json
from google import generativeai
from google.genai import types
from typing import Dict, Any, Optional

# Add the project root to the Python path (retained for safety)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# NOTE: Using the import path from your last submission
from src.db_utils.llm_client import get_llm_client

class ValidationAgent:
    """
    The Validation Agent uses an LLM to analyze the scraped transcript 
    and metadata to generate a quality score and structured tags.
    This score is CRITICAL for the RAG filter.
    """
    def __init__(self):
        self.client = get_llm_client()
        # Using the model specified in your submission
        self.model_name = "gemini-1.5-pro-latest"

    def _get_validation_schema(self) -> Dict[str, Any]:
      """Defines the required structured output for the LLM as a tool definition."""
      return {
        "name": "validate_content",
        "description": "Extracts quality score and metadata from a video transcript.",
        "parameters": {
            "properties": {
                "instrument_id": {
                    "type": "STRING",
                    "description": "The primary instrument the content teaches (e.g., 'electric_guitar', 'piano')."
                },
                "difficulty": {
                    "type": "STRING",
                    "description": "The primary target skill level: 'beginner', 'intermediate', or 'advanced'."
                },
                "technique": {
                    "type": "STRING",
                    "description": "The specific technique or topic being taught (e.g., 'sweeping', 'power_chords', 'minor_scales')."
                },
                "helpfulness_score": {
                    "type": "NUMBER",
                    "description": "A quality score from 0.0 to 1.0 (with two decimal places) based on clarity, depth, and relevance. Must be 0.8 or higher to be considered useful for the core curriculum."
                },
                "validation_notes": {
                    "type": "STRING",
                    "description": "A brief note explaining the score and the content's focus."
                }
            },
            "required": ["instrument_id", "difficulty", "technique", "helpfulness_score", "validation_notes"]
        }
      }
    def validate_and_score(self, content: str, scraped_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generates the helpfulness score and core metadata fields using LLM function calling.
        """
        # Limit content to 4000 characters for token efficiency
        transcript_snippet = content[:4000]
        
        system_prompt = (
            "You are the Autodidact AI Validation Agent. Your task is to analyze the "
            "provided YouTube transcript and metadata to generate a structured JSON object "
            "for indexing. You must be strict: only content that is highly instructional, "
            "clear, and covers a defined topic should receive a helpfulness_score of 0.8 or higher. "
            "If the content is rambling, unclear, or too general, score it below 0.8. "
            "Call the `validate_content` function with the results of your analysis."
            f"The video title is: '{scraped_metadata.get('title', 'N/A')}' "
            f"The video channel is: '{scraped_metadata.get('channel_name', 'N/A')}'"
            f"Video Views: {scraped_metadata.get('views', 'N/A')}. "
            f"Video Length: {scraped_metadata.get('video_length_seconds', 'N/A')} seconds. "
        )
        
        user_prompt = f"Analyze this transcript content and provide the structured validation:\n\n{transcript_snippet}"

        try:
            print(f"\nValidation Agent: Analyzing '{scraped_metadata.get('title')}' for quality score...")
            
            # Initialize the model object
            model = generativeai.GenerativeModel(
                model_name=self.model_name,
            )
            print("Validation Agent: Model initialized.")

            response = model.generate_content(
                [system_prompt, user_prompt],
                tools=[self._get_validation_schema()],
                # Set tool_config to 'ANY' to ensure the model uses the function
                tool_config={'function_calling_config': "ANY"} 
            )
            print("Validation Agent: generate_content completed.")
            
            # --- Extract the function call result ---
            function_call = None
            if response.candidates:
                print("Validation Agent: response.candidates exists.")
                if response.candidates[0].content.parts:
                    print("Validation Agent: response.candidates[0].content.parts exists.")
                    function_call = response.candidates[0].content.parts[0].function_call
                    print("Validation Agent: function_call extracted.")
                else:
                    print("Validation Agent: No parts in content.")
            else:
                print("Validation Agent: No candidates in response.")

            if function_call and function_call.name == "validate_content":
                print("Validation Agent: Function call name is validate_content.")
                # Convert the FunctionCall object to a dictionary
                validation_data = types.FunctionCall.to_dict(function_call)
                print("Validation Agent: to_dict completed.")
                # The arguments are in a nested 'args' dictionary
                args = validation_data.get('args', {})
                
                print(f"Validation Agent: Scored {args.get('helpfulness_score', 'N/A')}")
                return args
            else:
                # This could happen if the model decided not to call the function
                print("❌ Validation Agent failed: The LLM did not call the `validate_content` function.")
                return None
            
        except Exception as e:
            print(f"❌ Validation Agent failed to generate score: {e}")
            print(f"Exception type: {type(e)}")
            print(f"Exception class: {e.__class__}")
            import traceback
            traceback.print_exc()
            return None

# --- EXAMPLE USAGE/TEST ---
if __name__ == "__main__":
  # Mock data to simulate the scraper output
  mock_scraped_data = {
      "title": "Easy Guitar Lesson: Minor Pentatonic Scale Mastery",
      "channel_name": "GuitarGurus",
      "video_id": "1234567890a",
      "views": 150000,
      "video_length_seconds": 950,
      "transcript": "Hey everyone, welcome back to the channel. Today, we're diving deep into the minor pentatonic scale. It's a foundational scale for blues, rock, and a ton of other genres. We'll start with the basic shape in the key of A minor. The notes are A, C, D, E, G. Okay, let's break it down. First finger on the 5th fret of the low E string, that's your A. Then, fourth finger on the 8th fret, that's C. Move to the A string, first finger on the 5th fret for D, third finger on the 7th for E. It's a really versatile scale and once you get the hang of it, you can fly all over the neck. We'll go over some licks and tricks later in the video, but for now, just practice going up and down the scale. Get it into your muscle memory. Repetition is key. Don't worry about speed at first, focus on clean notes. Make sure each note rings out. A common mistake is not pressing down hard enough. You want a clean, clear tone. Alright, let's try it with a backing track..."
  }
  
  agent = ValidationAgent()
  
  validation_result = agent.validate_and_score(
      content=mock_scraped_data["transcript"],
      scraped_metadata=mock_scraped_data
  )
  
  print("\n--- Validation Agent Output ---")
  if validation_result:
      # validation_result is the clean dictionary of arguments
      print(json.dumps(validation_result, indent=2))
  else:
      print("No validation data was generated.")