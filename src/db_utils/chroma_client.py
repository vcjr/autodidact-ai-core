import os
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from chromadb.errors import InvalidDimensionException as InvalidCollectionName

# Load environment variables (Host and Port for Chroma)
load_dotenv()

# The HOST and PORT variables should be defined in your .env file
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

# Collection name
COLLECTION_NAME_V2 = "autodidact_ai_core_v2"   # Current collection (768d embeddings)

def get_embedding_function():
    """
    Returns the configured embedding function (EMBEDDING_PROVIDER=local|gemini).

    Default ``local`` is sentence-transformers all-mpnet-base-v2 (768d), which matches
    existing collections. See src/retrieval/embeddings.py.
    """
    from src.retrieval.embeddings import get_embedding_function as _get

    return _get()


def default_collection_name() -> str:
    """Collection matching the configured embedding provider."""
    from src.retrieval.embeddings import collection_name_for

    return collection_name_for()

def get_chroma_client():
    """Initializes and returns the ChromaDB HTTP client."""
    try:
        print(f"Attempting to connect to Chroma at: http://{CHROMA_HOST}:{CHROMA_PORT}")
        
        # Use host and port arguments, not url
        client = chromadb.HttpClient(
            host=CHROMA_HOST, 
            port=CHROMA_PORT,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        return client
        
    except Exception as e:
        print("ERROR: Failed to initialize ChromaDB Client.")
        print(f"Please ensure ChromaDB is running and accessible at {CHROMA_HOST}:{CHROMA_PORT}.")
        raise e

def get_or_create_collection(client=None, collection_name=None):
    """
    Gets or creates a ChromaDB collection with the upgraded embedding model.
    
    Args:
        client: ChromaDB client instance (creates new one if None)
        collection_name: Name of collection (defaults to v2 with 768d embeddings)
    
    Returns:
        ChromaDB collection instance
    """
    if client is None:
        client = get_chroma_client()
    if collection_name is None:
        collection_name = default_collection_name()
    
    embedding_function = get_embedding_function()
    
    try:
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={
                "description": "Autodidact AI Core - Educational content vectors",
                "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "local"),
                "embedding_dimension": 768,
                "schema_version": "1.0.0"
            }
        )
        print(f"✅ Collection '{collection_name}' ready")
        return collection
    
    except Exception as e:
        print(f"❌ Failed to create collection '{collection_name}': {e}")
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
        print(f"Found {len(collections)} existing collections:")
        for col in collections:
            print(f"  - {col.name}")
        
        # Test creating/getting the v2 collection
        print("\n🔧 Testing v2 collection with 768d embeddings...")
        collection = get_or_create_collection(client)
        print(f"✅ Collection '{collection.name}' is ready with {collection.count()} documents")
        
    except Exception as e:
        print(f"❌ ChromaDB Connection Test Failed: {e}")
        print("Please ensure your Docker container is running (docker-compose up -d).")

if __name__ == "__main__":
    test_chroma_connection()