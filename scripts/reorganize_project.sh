#!/bin/bash
# Enterprise Project Reorganization Script
# Organizes the autodidact-ai-core project into a production-ready structure

set -e

echo "🏗️  Reorganizing project structure..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Move test files to appropriate directories
echo -e "${BLUE}📁 Organizing test files...${NC}"

# Integration tests
[ -f test_apify_integration.py ] && mv test_apify_integration.py tests/integration/ && echo -e "${GREEN}✓${NC} Moved test_apify_integration.py"
[ -f test_residential_proxy.py ] && mv test_residential_proxy.py tests/integration/ && echo -e "${GREEN}✓${NC} Moved test_residential_proxy.py"
[ -f test_youtube_residential.py ] && mv test_youtube_residential.py tests/integration/ && echo -e "${GREEN}✓${NC} Moved test_youtube_residential.py"
[ -f test_transcript_direct.py ] && mv test_transcript_direct.py tests/integration/ && echo -e "${GREEN}✓${NC} Moved test_transcript_direct.py"

# Unit tests  
[ -f tests/test_unified_metadata.py ] && mv tests/test_unified_metadata.py tests/unit/ && echo -e "${GREEN}✓${NC} Moved test_unified_metadata.py"

# Move documentation files
echo -e "${BLUE}📚 Organizing documentation...${NC}"

# Architecture docs
[ -f ARCHITECTURE.md ] && mv ARCHITECTURE.md docs/architecture/ && echo -e "${GREEN}✓${NC} Moved ARCHITECTURE.md"
[ -f INTEGRATION_ANALYSIS.md ] && mv INTEGRATION_ANALYSIS.md docs/architecture/ && echo -e "${GREEN}✓${NC} Moved INTEGRATION_ANALYSIS.md"

# Setup docs
[ -f APIFY_SETUP.md ] && mv APIFY_SETUP.md docs/setup/ && echo -e "${GREEN}✓${NC} Moved APIFY_SETUP.md"
[ -f PROXY_SETUP.md ] && mv PROXY_SETUP.md docs/setup/ && echo -e "${GREEN}✓${NC} Moved PROXY_SETUP.md"
[ -f PROXY_DIAGNOSIS.md ] && mv PROXY_DIAGNOSIS.md docs/setup/ && echo -e "${GREEN}✓${NC} Moved PROXY_DIAGNOSIS.md"

# Progress docs
[ -f PROGRESS.md ] && mv PROGRESS.md docs/progress/ && echo -e "${GREEN}✓${NC} Moved PROGRESS.md"

# Move config files
echo -e "${BLUE}⚙️  Organizing configuration files...${NC}"

[ -f proxy_config.json ] && mv proxy_config.json config/ && echo -e "${GREEN}✓${NC} Moved proxy_config.json"
[ -f proxy_config.example.json ] && mv proxy_config.example.json config/ && echo -e "${GREEN}✓${NC} Moved proxy_config.example.json"

# Create symlinks for backward compatibility
echo -e "${BLUE}🔗 Creating backward compatibility symlinks...${NC}"

# Symlink config files so existing code still works
[ ! -f proxy_config.json ] && [ -f config/proxy_config.json ] && ln -s config/proxy_config.json proxy_config.json && echo -e "${GREEN}✓${NC} Created symlink: proxy_config.json"

echo -e "${GREEN}✅ Project reorganization complete!${NC}"
echo ""
echo "New structure:"
echo "  tests/"
echo "    ├── unit/          - Component-level tests"
echo "    ├── integration/   - Multi-component tests"  
echo "    └── e2e/           - End-to-end workflows"
echo "  docs/"
echo "    ├── architecture/  - System design docs"
echo "    ├── setup/         - Installation guides"
echo "    └── progress/      - Development progress"
echo "  config/              - Configuration files"
echo "  scripts/             - Utility scripts"
echo "  src/                 - Application code"
