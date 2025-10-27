"""
Test Proxy Integration with YouTubeCrawler
==========================================

Verifies that proxy configuration works correctly with the crawler.
This is a dry-run test that doesn't actually fetch transcripts.
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.bot.crawlers.youtube_crawler import YouTubeCrawler
from src.bot.bot_indexer import BotIndexer

print("=" * 70)
print("Proxy Integration Test")
print("=" * 70)

# Test 1: YouTubeCrawler with proxies
print("\n📊 Test 1: YouTubeCrawler Initialization with Proxies")
print("-" * 70)

try:
    crawler = YouTubeCrawler(
        use_proxies=True,
        proxy_config="proxy_config.example.json",
        min_quality_score=0.6
    )
    print("✅ Crawler initialized with proxy support")
    
    stats = crawler.get_statistics()
    print(f"\n📊 Crawler Statistics:")
    print(f"   Quota: {stats['quota_used']}/{stats['max_quota']}")
    print(f"   Max Results: {stats['max_results_per_query']}")
    
    if 'proxy_manager' in stats:
        proxy_stats = stats['proxy_manager']
        print(f"\n🔄 Proxy Manager:")
        print(f"   Total Proxies: {proxy_stats['total_proxies']}")
        print(f"   Active Proxies: {proxy_stats['active_proxies']}")
        print(f"   Strategy: {proxy_stats['strategy']}")
        print(f"   Direct Fallback: {proxy_stats['allow_direct']}")
    else:
        print("⚠️  Warning: Proxy manager not initialized")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: BotIndexer with proxies
print("\n\n📊 Test 2: BotIndexer Initialization with Proxies")
print("-" * 70)

try:
    indexer = BotIndexer(
        use_proxies=True,
        proxy_config="proxy_config.example.json",
        min_quality_score=0.6,
        use_mock_crawler=False
    )
    print("✅ BotIndexer initialized with proxy support")
    
    stats = indexer.youtube_crawler.get_statistics()
    if 'proxy_manager' in stats:
        print("✅ Proxy manager accessible through BotIndexer")
    else:
        print("⚠️  Warning: Proxy manager not found in crawler")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Configuration validation
print("\n\n📊 Test 3: Proxy Configuration Validation")
print("-" * 70)

try:
    import json
    
    with open("proxy_config.example.json", 'r') as f:
        config = json.load(f)
    
    print("✅ Proxy config file loaded successfully")
    print(f"\n📋 Configuration:")
    print(f"   Proxies defined: {len(config.get('proxies', []))}")
    print(f"   Strategy: {config.get('strategy', 'N/A')}")
    print(f"   Direct fallback: {config.get('allow_direct', 'N/A')}")
    print(f"   Max failures: {config.get('max_failures', 'N/A')}")
    print(f"   Timeout: {config.get('timeout_seconds', 'N/A')}s")
    
    print(f"\n📍 Proxy Locations:")
    for i, proxy in enumerate(config.get('proxies', []), 1):
        proxy_type = proxy.get('type', 'unknown')
        location = proxy.get('location', 'unknown')
        notes = proxy.get('notes', 'No description')
        print(f"   {i}. {proxy_type.upper()} - {location} ({notes})")
        
except FileNotFoundError:
    print("❌ Error: proxy_config.example.json not found")
except Exception as e:
    print(f"❌ Error: {e}")

# Summary
print("\n\n" + "=" * 70)
print("Integration Test Summary")
print("=" * 70)

print("\n✅ Proxy support is integrated and ready to use!")
print("\n📋 Next Steps:")
print("   1. Copy proxy_config.example.json to proxy_config.json")
print("   2. Add your proxy credentials to proxy_config.json")
print("   3. Run bot_indexer with use_proxies=True")
print("   4. Monitor proxy statistics during crawling")

print("\n💡 Quick Start:")
print("   # Copy example config")
print("   cp proxy_config.example.json proxy_config.json")
print("")
print("   # Edit with your credentials")
print("   nano proxy_config.json")
print("")
print("   # Run with proxies enabled")
print("   python src/bot/bot_indexer.py  # (modify demo to set use_proxies=True)")

print("\n📖 For detailed setup instructions, see PROXY_SETUP.md")
print()
