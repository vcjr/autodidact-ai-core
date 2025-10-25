import os
from dotenv import load_dotenv
import chromadb
from chromadb.errors import InvalidDimensionException as InvalidCollectionName

# Load environment variables (Host and Port for Chroma)
load_dotenv()

# The HOST and PORT variables should be defined in your .env file
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

def get_chroma_client():
    """Initializes and returns the ChromaDB HTTP client."""
    try:
        print(f"Attempting to connect to Chroma at: http://{CHROMA_HOST}:{CHROMA_PORT}")
        
        # Use host and port arguments, not url
        client = chromadb.HttpClient(
            host=CHROMA_HOST, 
            port=CHROMA_PORT
        )
        return client
        
    except Exception as e:
        print("ERROR: Failed to initialize ChromaDB Client.")
        print(f"Please ensure ChromaDB is running and accessible at {CHROMA_HOST}:{CHROMA_PORT}.")
        raise e

def test_chroma_connection():
    """Tests the connection by attempting to list existing collections."""
    client = get_chroma_client()
    try:
        # Pinging the server is the most basic test
        client.heartbeat()
        print("✅ ChromaDB Heartbeat Successful! The server is running.")

        # Test listing collections
        collections = client.list_collections()
        print(f"Found {len(collections)} existing collections.")
        
    except Exception as e:
        print(f"❌ ChromaDB Connection Test Failed: {e}")
        print("Please ensure your Docker container is running (docker-compose up -d).")

if __name__ == "__main__":
    test_chroma_connection()