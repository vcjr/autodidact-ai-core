#!/bin/bash

# ============================================================================
# Autodidact AI Core - Setup Script
# ============================================================================
# This script sets up your development environment following Phase 1, Week 1
# of the integration roadmap.
#
# Usage: ./setup.sh

set -e  # Exit on error

echo "🚀 Autodidact AI Core - Environment Setup"
echo "=========================================="
echo ""

# Check Python version
echo "📍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

if [[ "$python_version" < "3.11" ]]; then
    echo "   ⚠️  Warning: Python 3.11+ recommended (you have $python_version)"
else
    echo "   ✅ Python version OK"
fi
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ⚠️  Virtual environment already exists. Skipping."
else
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "   ✅ pip upgraded"
echo ""

# Install dependencies
echo "📚 Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "   ✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
echo "🔐 Setting up environment variables..."
if [ -f ".env" ]; then
    echo "   ⚠️  .env file already exists. Skipping."
else
    cat > .env << 'EOF'
# ============================================================================
# Autodidact AI Core - Environment Configuration
# ============================================================================

# ChromaDB Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Google Gemini API (Primary LLM)
GEMINI_API_KEY=your_gemini_api_key_here

# YouTube Data API v3 (for bot crawler)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Reddit API (for bot crawler)
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=AutodidactBot/1.0

# Google Custom Search API (for blog crawler)
GOOGLE_CSE_KEY=your_google_custom_search_key_here
GOOGLE_CSE_ID=your_google_custom_search_engine_id_here

# Optional: OpenAI API (if using GPT-4 instead of Gemini)
# OPENAI_API_KEY=your_openai_api_key_here

# Optional: Anthropic API (if using Claude)
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
EOF
    echo "   ✅ .env file created"
    echo "   ⚠️  IMPORTANT: Edit .env and add your API keys!"
fi
echo ""

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p chroma_data
mkdir -p redis_data
mkdir -p data/bot
mkdir -p data/strategy
mkdir -p data/prompts
mkdir -p logs
mkdir -p tests
echo "   ✅ Directories created"
echo ""

# Start Docker containers
echo "🐳 Starting Docker containers (ChromaDB + Redis)..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo "   ✅ Docker containers started"
    echo ""
    echo "   Waiting for services to be ready..."
    sleep 5
    
    # Test ChromaDB connection
    echo "   🔍 Testing ChromaDB connection..."
    python3 -c "
import chromadb
try:
    client = chromadb.HttpClient(host='localhost', port=8000)
    client.heartbeat()
    print('   ✅ ChromaDB is ready')
except Exception as e:
    print(f'   ❌ ChromaDB connection failed: {e}')
    print('   Try: docker-compose logs chromadb')
"
    
    # Test Redis connection
    echo "   🔍 Testing Redis connection..."
    python3 -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print('   ✅ Redis is ready')
except Exception as e:
    print(f'   ❌ Redis connection failed: {e}')
    print('   Try: docker-compose logs redis')
"
else
    echo "   ⚠️  docker-compose not found. Please install Docker and Docker Compose."
    echo "   You can start services manually with: docker-compose up -d"
fi
echo ""

# Run tests
echo "🧪 Running tests..."
if command -v pytest &> /dev/null; then
    pytest tests/test_unified_metadata.py -v
    echo "   ✅ Tests passed"
else
    echo "   ⚠️  pytest not installed. Skipping tests."
    echo "   Install with: pip install pytest"
fi
echo ""

# Summary
echo "✨ Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys (especially GEMINI_API_KEY)"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Test ChromaDB connection: python src/db_utils/chroma_client.py"
echo "4. Test LLM connection: python src/db_utils/llm_client.py"
echo "5. Review INTEGRATION_ANALYSIS.md for the full roadmap"
echo ""
echo "Useful commands:"
echo "  - Start services: docker-compose up -d"
echo "  - Stop services: docker-compose down"
echo "  - View logs: docker-compose logs -f"
echo "  - Run tests: pytest tests/ -v"
echo ""
echo "Happy coding! 🎉"
