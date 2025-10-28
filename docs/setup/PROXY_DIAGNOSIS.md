# YouTube Transcript Proxy Diagnosis

## Current Situation

✅ **Proxy Integration: WORKING**
- ProxyManager correctly loads BrightData credentials
- GenericProxyConfig properly passes proxy to YouTubeTranscriptApi
- Proxy is being used for all transcript requests

❌ **IP Blocking Issues: BOTH IPs BLOCKED**
- Your work VPN IP: **BLOCKED** by YouTube (`IpBlocked` error)
- BrightData datacenter proxy IP: **BLOCKED** by YouTube (`RequestBlocked` error)

## Test Results

```
Direct Connection (Work VPN):
- Video ipcm-Ub22UY: ❌ IpBlocked
- Video Wzqa44N-sIU: ❌ IpBlocked
- Video xv6w9mC33E8: ❌ IpBlocked

With BrightData Datacenter Proxy:
- Video ipcm-Ub22UY: ❌ RequestBlocked (despite using proxy)
- Video Wzqa44N-sIU: ❌ RequestBlocked (despite using proxy)
- Video xv6w9mC33E8: ❌ RequestBlocked (despite using proxy)
```

## Root Cause

YouTube aggressively blocks:
1. **Corporate VPN IPs** - Your work VPN is on YouTube's blocklist
2. **Datacenter Proxy IPs** - BrightData's datacenter proxies are also blocked

## Solutions (In Order of Recommendation)

### Option 1: Switch to Residential Proxies (Production Ready) ⭐

**What to do:**
1. Log into BrightData dashboard
2. Create a new proxy zone with type "Residential" (NOT "Datacenter")
3. Update `proxy_config.json`:
   ```json
   {
     "proxies": [
       {
         "url": "http://brd-customer-hl_1cc34631-zone-RESIDENTIAL:PASSWORD@brd.superproxy.io:22225",
         "type": "http",
         "location": "random",
         "notes": "BrightData residential proxy - Rotating IPs"
       }
     ],
     "strategy": "performance",
     "allow_direct": true,
     "max_failures": 3
   }
   ```
4. Note: Port is usually 22225 for residential, not 33335

**Cost:**
- ~$8.50/GB (vs $0.10/GB for datacenter)
- ~$0.85 per 1000 videos (vs $0.01 with datacenter)
- For 10,000 videos: ~$8.50

**Success Rate:** Very high (72M+ rotating residential IPs)

### Option 2: Test from Home Network (Quick Test)

**What to do:**
1. Disconnect from work VPN
2. Connect to your home WiFi
3. Run the crawler directly (no proxy needed)

**To disable proxies temporarily:**

Edit `src/bot/bot_indexer.py` line ~367:
```python
stats = indexer.index_domain(
    domain_id="MUSIC",
    subdomain_id="PIANO",
    platform="youtube",
    skill_level="beginner",
    num_queries=2,
    videos_per_query=2,
    delay_seconds=1.0
    # Note: YouTubeCrawler was initialized with use_proxies=False in __init__
)
```

And edit line ~340 where YouTubeCrawler is initialized:
```python
self.youtube_crawler = YouTubeCrawler(
    api_key=os.getenv("YOUTUBE_API_KEY"),
    max_results_per_query=max_results_per_query,
    use_proxies=False,  # Changed from True
    min_quality_score=min_quality_score
)
```

**Cost:** $0 (uses your home IP)

**Success Rate:** High (if your home ISP IP isn't blocked)

### Option 3: Alternative Proxy Provider

Try Webshare residential proxies (mentioned in youtube-transcript-api docs):
- https://www.webshare.io
- Similar pricing to BrightData residential
- Has direct integration with youtube-transcript-api

## Recommendation

**For immediate testing:** Use Option 2 (home network)
**For production:** Use Option 1 (residential proxies)

The good news: Your code is 100% correct and working. You just need residential IPs instead of datacenter IPs.

## Next Steps

1. **Short term:** Test from home to validate everything works
2. **Production:** Upgrade to BrightData residential proxies
3. **Monitor:** Track success rate and costs in BrightData dashboard
4. **Optimize:** If costs are high, consider:
   - Caching transcripts (don't re-fetch)
   - Rate limiting (avoid unnecessary requests)
   - Filtering videos before transcript fetch (check duration, views, etc.)
