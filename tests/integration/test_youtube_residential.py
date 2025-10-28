#!/usr/bin/env python3
"""
Direct test of YouTube transcript API with residential proxy
"""

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

print("=" * 70)
print("YouTube Transcript API - Residential Proxy Test")
print("=" * 70)

# BrightData residential proxy
proxy_url = "http://brd-customer-hl_1cc34631-zone-residential_proxy1:j0zj8p7yyka4@brd.superproxy.io:33335"

# Test videos
test_videos = [
    ("ipcm-Ub22UY", "Piano video (was blocked before)"),
    ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),
]

print(f"\n🔄 Proxy: brd.superproxy.io:33335 (residential)")
print(f"📊 Testing {len(test_videos)} videos\n")

successes = 0
failures = 0

for video_id, description in test_videos:
    print("-" * 70)
    print(f"📹 Video: {video_id}")
    print(f"   {description}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    
    try:
        # Create proxy config
        proxy_config = GenericProxyConfig(
            http_url=proxy_url,
            https_url=proxy_url
        )
        
        # Fetch transcript with proxy
        api = YouTubeTranscriptApi(proxy_config=proxy_config)
        transcript = api.fetch(video_id, languages=['en'])
        
        snippet_count = len(transcript.snippets)
        full_text = ' '.join([snippet.text for snippet in transcript.snippets])
        word_count = len(full_text.split())
        
        print(f"   ✅ SUCCESS!")
        print(f"      Snippets: {snippet_count}")
        print(f"      Words: {word_count}")
        print(f"      Preview: {full_text[:150]}...")
        
        successes += 1
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:300]
        print(f"   ❌ FAILED: {error_type}")
        print(f"      {error_msg}")
        failures += 1

print("\n" + "=" * 70)
print(f"Results: {successes} succeeded, {failures} failed")
print("=" * 70)

if successes > 0:
    print("\n✅ Residential proxy is working for YouTube transcripts!")
    print("   You can now run the bot_indexer.py successfully")
else:
    print("\n❌ All attempts failed")
    print("   Possible issues:")
    print("   1. BrightData residential zone not properly configured")
    print("   2. Need to whitelist YouTube domains in BrightData")
    print("   3. Insufficient balance ($0.95 remaining)")
    print("   4. youtube-transcript-api compatibility issue")
