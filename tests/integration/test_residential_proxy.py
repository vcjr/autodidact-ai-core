#!/usr/bin/env python3
"""
Test BrightData Residential Proxy Connection
"""

import requests
import time
import warnings

# Suppress SSL warnings since BrightData uses self-signed certificates
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

print("=" * 70)
print("Testing BrightData Residential Proxy")
print("=" * 70)

# Residential proxy credentials
proxy_url = "http://brd-customer-hl_1cc34631-zone-residential_proxy1:j0zj8p7yyka4@brd.superproxy.io:33335"

print(f"\n📡 Proxy: brd.superproxy.io:33335")
print(f"🏘️  Zone: residential_proxy1 (rotating residential IPs)")
print(f"💰 Cost: $15/GB")
print(f"💵 Balance: $0.95")

# Test 1: Basic connection
print("\n" + "-" * 70)
print("Test 1: Basic Connection")
print("-" * 70)

try:
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    response = requests.get('https://geo.brdtest.com/welcome.txt', proxies=proxies, timeout=10, verify=False)
    
    if response.status_code == 200:
        print(f"✅ Status: {response.status_code}")
        print(f"📋 Response: {response.text[:200]}")
    else:
        print(f"❌ Status: {response.status_code}")
        
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: IP Rotation (3 requests should show different IPs)
print("\n" + "-" * 70)
print("Test 2: IP Rotation (Should see different IPs)")
print("-" * 70)

ips_seen = set()

for i in range(3):
    try:
        response = requests.get('https://geo.brdtest.com/welcome.txt', proxies=proxies, timeout=10, verify=False)
        
        # Extract country/IP info from response
        text = response.text
        if "Country:" in text:
            # Parse the response
            lines = text.split('\n')
            for line in lines:
                if 'Country:' in line or 'IP:' in line:
                    print(f"   Request {i+1}: {line.strip()}")
                    if 'IP:' in line:
                        ip = line.split('IP:')[1].strip().split(',')[0]
                        ips_seen.add(ip)
        
        time.sleep(1)  # Small delay between requests
        
    except Exception as e:
        print(f"   ❌ Request {i+1} failed: {e}")

print(f"\n📊 Unique IPs seen: {len(ips_seen)}")
if len(ips_seen) > 1:
    print("✅ IP rotation is working!")
else:
    print("⚠️  IP rotation might not be enabled (saw same IP multiple times)")

# Test 3: YouTube Transcript (Real test)
print("\n" + "-" * 70)
print("Test 3: YouTube Transcript Fetch (Critical Test)")
print("-" * 70)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import GenericProxyConfig
    
    video_id = "ipcm-Ub22UY"  # Video that was blocked before
    
    proxy_config = GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url
    )
    
    print(f"📹 Video ID: {video_id}")
    print(f"🔄 Using residential proxy...")
    
    api = YouTubeTranscriptApi(proxy_config=proxy_config)
    transcript = api.fetch(video_id, languages=['en'])
    
    snippet_count = len(transcript.snippets)
    full_text = ' '.join([snippet.text for snippet in transcript.snippets])
    word_count = len(full_text.split())
    
    print(f"✅ SUCCESS! Transcript retrieved:")
    print(f"   📊 Snippets: {snippet_count}")
    print(f"   📝 Words: {word_count}")
    print(f"   📄 Preview: {full_text[:200]}...")
    
except ImportError:
    print("⚠️  youtube-transcript-api not installed, skipping test")
except Exception as e:
    error_type = type(e).__name__
    print(f"❌ FAILED: {error_type}")
    print(f"   Error: {str(e)[:300]}")

# Cost estimation
print("\n" + "=" * 70)
print("Cost Estimation")
print("=" * 70)
print(f"💰 Rate: $15/GB")
print(f"📦 1 transcript ≈ 100KB")
print(f"💵 1000 transcripts ≈ 100MB ≈ $1.50")
print(f"📊 Your $0.95 balance ≈ ~633 transcripts")
print(f"⚠️  NOTE: This is 150x more expensive than datacenter ($0.10/GB)")
print(f"   But it's the only way to bypass YouTube's IP blocks reliably")
