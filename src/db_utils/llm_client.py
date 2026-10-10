import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# Load enviroment variables from .env file
# This must be done before attempting to access os.environ
load_dotenv()

_configured = False


def _configure() -> None:
    """Configure the (legacy) Gemini SDK on first use, not at import time.

    Importing this module must not require GEMINI_API_KEY, otherwise a deployment
    that only uses Claude would crash when the legacy v1/v2 agents are imported.
    """
    global _configured
    if _configured:
        return
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables "
            "(required by the legacy v1/v2 agents; the v3 agents use src.llm.get_llm)."
        )
    genai.configure(api_key=api_key)
    _configured = True


def get_llm_client():
  """Initialize and returns the legacy Gemini API client (deprecated: use src.llm.get_llm)."""
  try:
    _configure()
    model = genai.GenerativeModel('models/gemini-flash-latest')
    return model
  except Exception as e:
    print("ERROR: Failed to initialize Gemini Client.")
    raise e


def test_llm_connection():
  """Tests the connection by making a simple API call."""
  try:
    client = get_llm_client()

    print("Pinging Gemini model: models/gemini-flash-lite-latest...")

    response = client.generate_content(
      "hello",
      generation_config={"max_output_tokens": 100}
    )

    if not response.parts:
        print(f"❌ LLM Connection Test Failed: The response was empty. Finish reason: {response.candidates[0].finish_reason.name}")
        return

    print("✅ LLM Connection Test Passed!")
    print(f"Response: {response.text.strip()}")


  except google_exceptions.NotFound as e:
    print(f"\n❌ API Error during connection test: {e}")
    print("This usually means the API key is invalid or you hit a rate limit.")
  except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")




if __name__ == "__main__":
  test_llm_connection()
