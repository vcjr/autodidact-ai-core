import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# Load enviroment variables from .env file
# This must be done before attempting to access os.environ
load_dotenv()

# Configure the Gemini API key
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
except ValueError as e:
    print(f"ERROR: {e}")
    print("Please ensure your GEMINI_API_KEY is set correctly in the .env file.")
    exit(1)


def get_llm_client():
  """Initialize and returns the Gemini API client."""
  try:
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
