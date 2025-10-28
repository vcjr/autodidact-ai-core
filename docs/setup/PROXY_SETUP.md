# Proxy Configuration Guide

## Overview

The YouTubeCrawler supports proxy rotation to bypass IP blocks and rate limits when fetching video transcripts. This guide explains how to configure and use proxies.

## Why Proxies?

YouTube's transcript API is aggressive about blocking repeated requests from the same IP address. Proxies help by:
- **Rotating IPs**: Each request comes from a different IP address
- **Geographic Distribution**: Avoid regional rate limits
- **Reliability**: Automatic failover if one proxy fails
- **Production Scale**: Handle high-volume crawling

## Supported Proxy Types

1. **HTTP/HTTPS Proxies**: Standard web proxies
2. **SOCKS5 Proxies**: More secure, better for API requests
3. **Residential Proxies**: Real user IPs (recommended for YouTube)
4. **Datacenter Proxies**: Cheaper but more likely to be blocked

## Recommended Proxy Providers

### For Production (Paid):
1. **BrightData** (formerly Luminati)
   - Best for YouTube scraping
   - Residential & datacenter IPs
   - ~$500/month for 40GB
   - Website: https://brightdata.com

2. **SmartProxy**
   - Good balance of price/quality
   - 40M+ residential IPs
   - ~$75/month for 5GB
   - Website: https://smartproxy.com

3. **Oxylabs**
   - Enterprise-grade
   - Excellent for large-scale scraping
   - ~$600/month minimum
   - Website: https://oxylabs.io

### For Development (Free/Cheap):
1. **Free Proxy Lists**
   - http://free-proxy-list.net
   - https://www.sslproxies.org
   - ⚠️ Unreliable, slow, often blocked

2. **ProxyScrape**
   - Free tier available
   - Better quality than public lists
   - Website: https://proxyscrape.com

## Configuration

### Step 1: Create Proxy Config File

Copy the example configuration:
```bash
cp proxy_config.example.json proxy_config.json
```

### Step 2: Add Your Proxies

Edit `proxy_config.json`:

```json
{
  "proxies": [
    {
      "url": "http://username:password@proxy1.brightdata.com:22225",
      "type": "http",
      "location": "us-east",
      "notes": "BrightData residential proxy - US East"
    },
    {
      "url": "socks5://username:password@proxy2.brightdata.com:22225",
      "type": "socks5",
      "location": "eu-west",
      "notes": "BrightData residential proxy - EU West"
    }
  ],
  "strategy": "performance",
  "allow_direct": true,
  "max_failures": 3,
  "timeout_seconds": 10
}
```

#### Proxy URL Formats:
- HTTP: `http://username:password@host:port`
- HTTPS: `https://username:password@host:port`
- SOCKS5: `socks5://username:password@host:port`
- No Auth: `http://host:port`

#### Configuration Options:
- **strategy**: Proxy selection strategy
  - `"round_robin"`: Rotate through proxies sequentially
  - `"random"`: Pick random proxy each time
  - `"performance"`: Use fastest/most reliable proxy (default)
  
- **allow_direct**: Fallback to direct connection if all proxies fail (default: true)
  
- **max_failures**: Mark proxy as dead after N consecutive failures (default: 3)
  
- **timeout_seconds**: Request timeout per proxy attempt (default: 10)

### Step 3: Enable Proxies in Code

#### Option 1: BotIndexer (Recommended)
```python
from src.bot.bot_indexer import BotIndexer

# Initialize with proxies enabled
indexer = BotIndexer(
    use_proxies=True,
    proxy_config="proxy_config.json",  # Optional: defaults to proxy_config.json
    min_quality_score=0.6
)

# Index content (proxies used automatically for transcripts)
indexer.index_domain(
    domain_id="MUSIC",
    subdomain_id="PIANO",
    num_queries=5
)
```

#### Option 2: YouTubeCrawler Directly
```python
from src.bot.crawlers.youtube_crawler import YouTubeCrawler

# Initialize crawler with proxies
crawler = YouTubeCrawler(
    use_proxies=True,
    proxy_config="proxy_config.json"
)

# Crawl videos (proxies used for transcripts)
results = crawler.search_and_extract(query, max_results=10)
```

#### Option 3: Environment Variable
```bash
# Set default proxy config path
export PROXY_CONFIG_FILE="/path/to/proxy_config.json"

# Then use without specifying path
indexer = BotIndexer(use_proxies=True)
```

## Proxy Rotation Strategies

### Performance Strategy (Default)
Selects proxy with best score based on:
- Success rate (80% weight)
- Average response time (20% weight)

**Best for:** Production use, maximizing reliability

```json
{
  "strategy": "performance"
}
```

### Round Robin Strategy
Cycles through proxies sequentially, distributing load evenly.

**Best for:** Testing all proxies equally, avoiding overuse

```json
{
  "strategy": "round_robin"
}
```

### Random Strategy
Randomly selects proxy for each request.

**Best for:** Unpredictable patterns, avoiding detection

```json
{
  "strategy": "random"
}
```

## Monitoring Proxy Performance

### Get Statistics
```python
# After crawling, check proxy stats
stats = crawler.get_statistics()

proxy_stats = stats.get('proxy_manager', {})
print(f"Total Proxies: {proxy_stats['total_proxies']}")
print(f"Active Proxies: {proxy_stats['active_proxies']}")
print(f"Success Rate: {proxy_stats['success_rate']:.1%}")
print(f"Best Proxy: {proxy_stats['best_proxy']}")
```

### View Detailed Proxy Info
```python
from src.bot.proxy_manager import ProxyManager

manager = ProxyManager(config_file="proxy_config.json")

# Print proxy details
for proxy in manager.proxies:
    print(f"\n{proxy.url}")
    print(f"  Active: {proxy.is_active}")
    print(f"  Requests: {proxy.total_requests}")
    print(f"  Success Rate: {proxy.success_rate:.1%}")
    print(f"  Avg Response: {proxy.avg_response_time:.2f}s")
```

## Troubleshooting

### Problem: All proxies failing
**Solution:**
1. Check proxy credentials are correct
2. Verify proxies are active (test with curl)
3. Check if proxy provider has rate limits
4. Enable direct fallback: `"allow_direct": true`

```bash
# Test proxy manually
curl -x http://username:password@proxy.com:port https://youtube.com
```

### Problem: Slow transcript extraction
**Solution:**
1. Use `"strategy": "performance"` to prefer fast proxies
2. Reduce `timeout_seconds` to fail faster
3. Add more proxies to pool
4. Use residential proxies instead of datacenter

### Problem: Proxies marked as dead incorrectly
**Solution:**
1. Increase `max_failures` threshold
2. Check network connectivity
3. Verify proxy provider isn't blocking YouTube

### Problem: High cost from proxy usage
**Solution:**
1. Use mock crawler for development: `use_mock_crawler=True`
2. Cache transcripts locally (future feature)
3. Reduce `max_results_per_query`
4. Use cheaper datacenter proxies for testing

## Best Practices

### 1. Separate Dev/Prod Proxies
```json
// dev_proxies.json - free/cheap proxies
{
  "proxies": [
    {"url": "http://free-proxy1.com:8080", ...}
  ]
}

// prod_proxies.json - premium residential proxies
{
  "proxies": [
    {"url": "http://username:password@premium-proxy.com:22225", ...}
  ]
}
```

### 2. Monitor Costs
```python
# Track proxy usage per session
stats = crawler.get_statistics()
requests = stats['proxy_manager']['total_requests']
cost_per_request = 0.001  # $0.001 per request
total_cost = requests * cost_per_request
print(f"Proxy cost this session: ${total_cost:.2f}")
```

### 3. Gradual Rollout
```python
# Start with proxies disabled
indexer = BotIndexer(use_proxies=False)

# Test on small batch
indexer.index_domain("MUSIC", num_queries=2)

# If successful, enable proxies for larger batch
indexer = BotIndexer(use_proxies=True)
indexer.index_batch(domains, num_queries=10)
```

### 4. Rotate Providers
Keep multiple proxy providers configured for redundancy:
```json
{
  "proxies": [
    {"url": "http://user:pass@brightdata.com:22225", "notes": "Provider A"},
    {"url": "http://user:pass@smartproxy.com:7000", "notes": "Provider B"},
    {"url": "socks5://user:pass@oxylabs.io:7777", "notes": "Provider C"}
  ]
}
```

## Security Notes

### Protect Credentials
1. **Never commit `proxy_config.json` to git**
   ```bash
   echo "proxy_config.json" >> .gitignore
   ```

2. **Use environment variables for sensitive data**
   ```json
   {
     "proxies": [
       {
         "url": "http://${PROXY_USER}:${PROXY_PASS}@proxy.com:port"
       }
     ]
   }
   ```

3. **Encrypt config files in production**
   ```bash
   # Encrypt
   gpg -c proxy_config.json
   
   # Decrypt at runtime
   gpg -d proxy_config.json.gpg > proxy_config.json
   ```

## Cost Estimation

### BrightData Example:
- **Price**: $500/month for 40GB
- **Avg request size**: 100KB (transcript fetch)
- **Requests per GB**: ~10,000
- **Total requests**: 400,000/month
- **Cost per request**: $0.00125

### Usage Calculation:
```python
# 100 domains × 10 queries × 5 videos = 5,000 videos
# 5,000 videos × 100KB = 500MB = 0.5GB
# Cost: $500 × (0.5GB / 40GB) = $6.25 per batch
```

## Advanced: Custom Proxy Logic

### Implement Custom Strategy
```python
from src.bot.proxy_manager import ProxyManager, ProxyInfo

class GeoTargetedProxyManager(ProxyManager):
    def get_proxy(self, target_location=None):
        """Get proxy from specific geographic region."""
        if target_location:
            # Filter proxies by location
            regional_proxies = [
                p for p in self.proxies 
                if p.location == target_location and p.is_active
            ]
            if regional_proxies:
                return self._select_best_proxy(regional_proxies)
        
        # Fallback to default logic
        return super().get_proxy()

# Usage
manager = GeoTargetedProxyManager()
proxy = manager.get_proxy(target_location="us-east")
```

## Next Steps

1. **Set up proxies**: Copy `proxy_config.example.json` → `proxy_config.json`
2. **Get proxy credentials**: Sign up for BrightData or SmartProxy
3. **Test integration**: Run `python src/bot/proxy_manager.py`
4. **Enable in pipeline**: `BotIndexer(use_proxies=True)`
5. **Monitor performance**: Check stats after each crawl session

## Resources

- [BrightData Documentation](https://docs.brightdata.com/)
- [SmartProxy Setup Guide](https://help.smartproxy.com/)
- [SOCKS5 vs HTTP Proxies](https://www.imperva.com/learn/performance/socks-proxy/)
- [Residential vs Datacenter Proxies](https://oxylabs.io/blog/residential-vs-datacenter-proxies)
