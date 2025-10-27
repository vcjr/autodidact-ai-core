"""
Test BrightData Proxy Connection
=================================

Verifies that your BrightData proxy is working correctly.
"""

import os
import sys
import requests
import json

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.bot.proxy_manager import ProxyManager

print("=" * 70)
print("BrightData Proxy Connection Test")
print("=" * 70)

# Load proxy config
print("\n📋 Loading proxy configuration...")
try:
    with open("proxy_config.json", 'r') as f:
        config = json.load(f)
    
    proxy_url = config['proxies'][0]['url']
    print(f"✅ Proxy loaded: brd.superproxy.io:33335")
    print(f"   Zone: static")
    print(f"   Type: {config['proxies'][0]['type']}")
except Exception as e:
    print(f"❌ Error loading config: {e}")
    sys.exit(1)

# Test 1: Direct connection to BrightData test endpoint
print("\n\n📊 Test 1: Direct Proxy Connection")
print("-" * 70)

try:
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    # BrightData test endpoint
    response = requests.get(
        'https://geo.brdtest.com/welcome.txt',
        proxies=proxies,
        timeout=10
    )
    
    print(f"✅ Connection successful!")
    print(f"   Status: {response.status_code}")
    print(f"   Response preview: {response.text[:100]}...")
    
except requests.exceptions.ProxyError as e:
    print(f"❌ Proxy connection failed: {e}")
    print("\n💡 Possible issues:")
    print("   - Check username/password are correct")
    print("   - Verify proxy zone is active in BrightData dashboard")
    print("   - Ensure you have account balance ($1 minimum)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

# Test 2: ProxyManager integration
print("\n\n📊 Test 2: ProxyManager Integration")
print("-" * 70)

try:
    manager = ProxyManager(config_file="proxy_config.json")
    
    proxy_config = manager.get_proxy()
    print(f"✅ ProxyManager initialized")
    print(f"   Proxies loaded: {len(manager.stats)}")
    print(f"   Selected proxy: brd.superproxy.io:33335")
    print(f"   Strategy: {manager.strategy.value}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 3: Multiple requests to check stability
print("\n\n📊 Test 3: Proxy Stability Test (5 requests)")
print("-" * 70)

success_count = 0
for i in range(5):
    try:
        response = requests.get(
            'https://geo.brdtest.com/welcome.txt',
            proxies=proxies,
            timeout=10
        )
        if response.status_code == 200:
            success_count += 1
            print(f"   Request {i+1}/5: ✅ Success ({response.elapsed.total_seconds():.2f}s)")
        else:
            print(f"   Request {i+1}/5: ⚠️  Status {response.status_code}")
    except Exception as e:
        print(f"   Request {i+1}/5: ❌ Failed - {e}")

print(f"\n📊 Success Rate: {success_count}/5 ({success_count/5*100:.0f}%)")

# Summary
print("\n\n" + "=" * 70)
print("Test Summary")
print("=" * 70)

if success_count >= 4:
    print("\n✅ BrightData proxy is working correctly!")
    print("\n📋 Next Steps:")
    print("   1. Run bot_indexer with use_proxies=True")
    print("   2. Monitor proxy usage in BrightData dashboard")
    print("   3. Check account balance (traffic cost: $0.10/GB)")
    
    print("\n💡 Ready to crawl YouTube transcripts:")
    print("   python src/bot/bot_indexer.py")
    print("   (modify demo to set use_proxies=True)")
    
    print("\n💰 Cost Estimation:")
    print("   - Monthly fee: $2.50")
    print("   - Traffic cost: $0.10/GB")
    print("   - Avg transcript: ~100KB")
    print("   - 1000 videos ≈ 100MB ≈ $0.01")
    print("   - Account balance: $1.00 (enough for ~10,000 videos)")
    
elif success_count > 0:
    print("\n⚠️  Proxy is partially working")
    print("   Some requests failed - check network stability")
    print("   You can proceed but monitor for errors")
    
else:
    print("\n❌ Proxy is not working")
    print("   All requests failed - check credentials and account status")
    print("   Verify in BrightData dashboard that zone is active")

print()
