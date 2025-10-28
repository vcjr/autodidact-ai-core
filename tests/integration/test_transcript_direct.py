#!/usr/bin/env python3
"""
Test YouTube transcript extraction WITHOUT proxies.
This will help determine if the issue is:
1. Your IP is blocked (cloud provider IP)
2. Only datacenter proxy IPs are blocked
"""

from youtube_transcript_api import YouTubeTranscriptApi

# Test video IDs from recent crawl attempts
test_videos = [
    "ipcm-Ub22UY",  # Piano video
    "Wzqa44N-sIU",  # Piano video
    "xv6w9mC33E8",  # Piano video
]

print("=" * 70)
print("Testing YouTube Transcript API - Direct Connection (No Proxy)")
print("=" * 70)
print()

for video_id in test_videos:
    print(f"📹 Video: {video_id}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=['en'])
        
        snippet_count = len(transcript.snippets)
        first_text = transcript.snippets[0].text if snippet_count > 0 else ""
        
        print(f"   ✅ SUCCESS!")
        print(f"   📊 Snippets: {snippet_count}")
        print(f"   📝 First line: {first_text[:80]}...")
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:300]
        print(f"   ❌ FAILED: {error_type}")
        print(f"   📋 Error: {error_msg}")
    
    print()

print("=" * 70)
print("Diagnosis:")
print("=" * 70)
print()
print("If all videos SUCCEED:")
print("  → Your IP is NOT blocked by YouTube")
print("  → The datacenter proxy IP IS blocked")
print("  → Solution: Switch to residential proxies OR run crawler from local IP")
print()
print("If all videos FAIL with 'RequestBlocked' or 'IPBlocked':")
print("  → Your IP IS blocked (likely cloud provider IP)")
print("  → Solution: MUST use residential proxies")
print()
