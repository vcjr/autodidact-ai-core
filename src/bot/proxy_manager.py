"""
Proxy Manager for YouTube Transcript Extraction
================================================

Manages proxy rotation to bypass IP-based blocking on YouTube transcript API.

Supports:
- Manual proxy list (HTTP/HTTPS/SOCKS5)
- Proxy rotation strategies (round-robin, random, performance-based)
- Health checking and failure tracking
- Fallback to direct connection

Usage:
    from src.bot.proxy_manager import ProxyManager
    
    # Initialize with proxies
    manager = ProxyManager(proxies=[
        "http://user:pass@proxy1.example.com:8080",
        "socks5://proxy2.example.com:1080"
    ])
    
    # Get next proxy
    proxy = manager.get_proxy()
    
    # Mark proxy as failed
    manager.mark_failed(proxy)
    
    # Mark proxy as successful
    manager.mark_success(proxy)
"""

import os
import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ProxyRotationStrategy(Enum):
    """Proxy rotation strategies."""
    ROUND_ROBIN = "round_robin"  # Cycle through proxies in order
    RANDOM = "random"  # Random selection
    PERFORMANCE = "performance"  # Prioritize fastest/most reliable proxies


@dataclass
class ProxyStats:
    """Statistics for a single proxy."""
    proxy_url: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    avg_response_time: float = 0.0
    consecutive_failures: int = 0
    is_active: bool = True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 - 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def score(self) -> float:
        """
        Calculate proxy quality score for performance-based selection.
        
        Factors:
        - Success rate (50%)
        - Response time (30%)
        - Recency (20%)
        """
        if not self.is_active or self.total_requests == 0:
            return 0.0
        
        # Success rate component (0-1)
        success_component = self.success_rate * 0.5
        
        # Response time component (faster = better, normalized)
        # 1s = 1.0, 5s = 0.5, 10s+ = 0.0
        time_component = max(0, 1 - (self.avg_response_time / 10)) * 0.3
        
        # Recency component (recent success = better)
        recency_component = 0.0
        if self.last_success:
            hours_since_success = (datetime.now() - self.last_success).total_seconds() / 3600
            recency_component = max(0, 1 - (hours_since_success / 24)) * 0.2
        
        return success_component + time_component + recency_component


class ProxyManager:
    """
    Manages proxy rotation with health tracking and intelligent selection.
    
    Attributes:
        proxies: List of proxy URLs
        strategy: Rotation strategy (round_robin, random, performance)
        max_consecutive_failures: Max failures before marking proxy inactive
        cooldown_minutes: Minutes to wait before retrying failed proxy
        stats: Statistics for each proxy
    """
    
    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        strategy: ProxyRotationStrategy = ProxyRotationStrategy.PERFORMANCE,
        max_consecutive_failures: int = 3,
        cooldown_minutes: int = 30,
        enable_direct_fallback: bool = True
    ):
        """
        Initialize proxy manager.
        
        Args:
            proxies: List of proxy URLs (http://user:pass@host:port)
            config_file: Path to JSON config file (overrides proxies param)
            strategy: Rotation strategy (default: PERFORMANCE)
            max_consecutive_failures: Max failures before marking inactive (default: 3)
            cooldown_minutes: Minutes before retrying failed proxy (default: 30)
            enable_direct_fallback: Allow direct connection if all proxies fail (default: True)
        """
        # Load proxies from config file if provided
        if config_file:
            proxy_list, config = self._load_from_config_file(config_file)
            # Override settings from config file
            if 'strategy' in config:
                strategy = ProxyRotationStrategy(config['strategy'])
            if 'max_failures' in config:
                max_consecutive_failures = config['max_failures']
            if 'allow_direct' in config:
                enable_direct_fallback = config['allow_direct']
        else:
            # Load proxies from parameter or environment
            proxy_list = proxies or self._load_proxies_from_env()
        
        # Initialize proxy stats
        self.stats: Dict[str, ProxyStats] = {}
        for proxy in proxy_list:
            self.stats[proxy] = ProxyStats(proxy_url=proxy)
        
        self.strategy = strategy
        self.max_consecutive_failures = max_consecutive_failures
        self.cooldown_minutes = cooldown_minutes
        self.enable_direct_fallback = enable_direct_fallback
        
        # Round-robin index
        self._current_index = 0
        
        print(f"✅ ProxyManager initialized:")
        print(f"   🔄 Proxies loaded: {len(self.stats)}")
        print(f"   📊 Strategy: {strategy.value}")
        print(f"   ⚡ Direct fallback: {'enabled' if enable_direct_fallback else 'disabled'}")
    
    def _load_from_config_file(self, config_file: str) -> tuple:
        """Load proxies from JSON configuration file."""
        import json
        
        # Try default location if file doesn't exist
        if not os.path.exists(config_file):
            default_path = os.path.join(os.getcwd(), 'proxy_config.json')
            if os.path.exists(default_path):
                config_file = default_path
            else:
                print(f"⚠️  Config file not found: {config_file}")
                return [], {}
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Extract proxy URLs
        proxies = []
        for proxy_config in config.get('proxies', []):
            proxies.append(proxy_config['url'])
        
        return proxies, config
    
    def _load_proxies_from_env(self) -> List[str]:
        """Load proxies from PROXY_LIST environment variable."""
        proxy_list = os.getenv("PROXY_LIST", "")
        if not proxy_list:
            return []
        
        # Parse comma-separated list
        proxies = [p.strip() for p in proxy_list.split(',') if p.strip()]
        return proxies
    
    def get_proxy(self) -> Optional[str]:
        """
        Get next proxy based on rotation strategy.
        
        Returns:
            Proxy URL string or None for direct connection
        """
        # Filter active proxies
        active_proxies = self._get_active_proxies()
        
        if not active_proxies:
            if self.enable_direct_fallback:
                print("⚠️  No active proxies available, using direct connection")
                return None
            else:
                raise RuntimeError("No active proxies available and direct fallback is disabled")
        
        # Select proxy based on strategy
        if self.strategy == ProxyRotationStrategy.ROUND_ROBIN:
            proxy = self._get_round_robin(active_proxies)
        elif self.strategy == ProxyRotationStrategy.RANDOM:
            proxy = self._get_random(active_proxies)
        elif self.strategy == ProxyRotationStrategy.PERFORMANCE:
            proxy = self._get_performance_based(active_proxies)
        else:
            proxy = active_proxies[0]
        
        # Update last used time
        self.stats[proxy].last_used = datetime.now()
        
        return proxy
    
    def _get_active_proxies(self) -> List[str]:
        """Get list of currently active proxies (respecting cooldown)."""
        active = []
        now = datetime.now()
        
        for proxy_url, stats in self.stats.items():
            # Check if marked inactive
            if not stats.is_active:
                # Check if cooldown period has passed
                if stats.last_failure:
                    cooldown_elapsed = (now - stats.last_failure).total_seconds() / 60
                    if cooldown_elapsed >= self.cooldown_minutes:
                        # Reset proxy
                        stats.is_active = True
                        stats.consecutive_failures = 0
                        print(f"🔄 Proxy {self._mask_proxy(proxy_url)} cooled down, marking active")
                    else:
                        continue
                else:
                    continue
            
            active.append(proxy_url)
        
        return active
    
    def _get_round_robin(self, proxies: List[str]) -> str:
        """Round-robin selection."""
        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        return proxy
    
    def _get_random(self, proxies: List[str]) -> str:
        """Random selection."""
        return random.choice(proxies)
    
    def _get_performance_based(self, proxies: List[str]) -> str:
        """Performance-based selection (weighted by success rate and speed)."""
        # Calculate scores for all proxies
        scored_proxies = [(proxy, self.stats[proxy].score) for proxy in proxies]
        
        # Sort by score descending
        scored_proxies.sort(key=lambda x: x[1], reverse=True)
        
        # Weighted random selection (bias toward higher scores)
        total_score = sum(score for _, score in scored_proxies)
        
        if total_score == 0:
            # No proxy has been used yet, random selection
            return random.choice(proxies)
        
        # Weighted random
        rand = random.uniform(0, total_score)
        cumulative = 0
        for proxy, score in scored_proxies:
            cumulative += score
            if rand <= cumulative:
                return proxy
        
        return scored_proxies[0][0]  # Fallback to best
    
    def mark_success(self, proxy_url: Optional[str], response_time: float = 0.0):
        """
        Mark proxy request as successful.
        
        Args:
            proxy_url: Proxy that succeeded (None for direct connection)
            response_time: Response time in seconds
        """
        if proxy_url is None or proxy_url not in self.stats:
            return
        
        stats = self.stats[proxy_url]
        stats.total_requests += 1
        stats.successful_requests += 1
        stats.consecutive_failures = 0
        stats.last_success = datetime.now()
        
        # Update average response time (exponential moving average)
        if stats.avg_response_time == 0:
            stats.avg_response_time = response_time
        else:
            stats.avg_response_time = (stats.avg_response_time * 0.7) + (response_time * 0.3)
    
    def mark_failed(self, proxy_url: Optional[str]):
        """
        Mark proxy request as failed.
        
        Args:
            proxy_url: Proxy that failed (None for direct connection)
        """
        if proxy_url is None or proxy_url not in self.stats:
            return
        
        stats = self.stats[proxy_url]
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.consecutive_failures += 1
        stats.last_failure = datetime.now()
        
        # Check if should mark inactive
        if stats.consecutive_failures >= self.max_consecutive_failures:
            stats.is_active = False
            print(f"❌ Proxy {self._mask_proxy(proxy_url)} marked inactive ({stats.consecutive_failures} consecutive failures)")
    
    def record_success(self, proxy_url: Optional[str], response_time: float = 0.0):
        """
        Alias for mark_success() for backward compatibility.
        
        Args:
            proxy_url: Proxy that succeeded (None for direct connection)
            response_time: Response time in seconds
        """
        self.mark_success(proxy_url, response_time)
    
    def record_failure(self, proxy_url: Optional[str]):
        """
        Alias for mark_failed() for backward compatibility.
        
        Args:
            proxy_url: Proxy that failed (None for direct connection)
        """
        self.mark_failed(proxy_url)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get proxy manager statistics."""
        active_count = sum(1 for s in self.stats.values() if s.is_active)
        total_requests = sum(s.total_requests for s in self.stats.values())
        total_successes = sum(s.successful_requests for s in self.stats.values())
        
        overall_success_rate = (total_successes / total_requests) if total_requests > 0 else 0.0
        
        # Best proxy
        best_proxy = None
        best_score = 0.0
        for proxy_url, stats in self.stats.items():
            if stats.score > best_score:
                best_score = stats.score
                best_proxy = self._mask_proxy(proxy_url)
        
        return {
            'total_proxies': len(self.stats),
            'active_proxies': active_count,
            'total_requests': total_requests,
            'successful_requests': total_successes,
            'failed_requests': total_requests - total_successes,
            'success_rate': round(overall_success_rate, 3),
            'strategy': self.strategy.value,
            'allow_direct': self.enable_direct_fallback,
            'best_proxy': best_proxy,
            'best_score': round(best_score, 3)
        }
    
    def get_proxy_details(self) -> List[Dict[str, Any]]:
        """Get detailed statistics for all proxies."""
        details = []
        for proxy_url, stats in self.stats.items():
            details.append({
                'proxy': self._mask_proxy(proxy_url),
                'active': stats.is_active,
                'total_requests': stats.total_requests,
                'success_rate': round(stats.success_rate, 3),
                'avg_response_time': round(stats.avg_response_time, 2),
                'consecutive_failures': stats.consecutive_failures,
                'score': round(stats.score, 3),
                'last_used': stats.last_used.isoformat() if stats.last_used else None
            })
        
        # Sort by score descending
        details.sort(key=lambda x: x['score'], reverse=True)
        return details
    
    def _mask_proxy(self, proxy_url: str) -> str:
        """Mask sensitive proxy credentials in logs."""
        # Extract and mask username:password if present
        if '@' in proxy_url:
            parts = proxy_url.split('@')
            credentials = parts[0].split('//')[-1]
            host = parts[1]
            return f"{proxy_url.split('//')[0]}//*****@{host}"
        return proxy_url


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Proxy Manager Demo")
    print("=" * 70)
    
    # Create sample proxies
    proxies = [
        "http://user1:pass1@proxy1.example.com:8080",
        "http://user2:pass2@proxy2.example.com:8080",
        "socks5://proxy3.example.com:1080"
    ]
    
    # Initialize manager
    manager = ProxyManager(proxies=proxies, strategy=ProxyRotationStrategy.PERFORMANCE)
    
    print("\n📊 Simulating proxy usage...\n")
    
    # Simulate 20 requests
    for i in range(1, 21):
        proxy = manager.get_proxy()
        masked = manager._mask_proxy(proxy) if proxy else "Direct"
        print(f"Request {i}: Using {masked}")
        
        # Simulate success/failure
        if i % 5 == 0:
            # Simulate failure
            manager.mark_failed(proxy)
            print(f"   ❌ Failed")
        else:
            # Simulate success
            response_time = random.uniform(0.5, 3.0)
            manager.mark_success(proxy, response_time)
            print(f"   ✅ Success ({response_time:.2f}s)")
        
        time.sleep(0.1)
    
    # Show statistics
    print("\n" + "=" * 70)
    print("Statistics Summary")
    print("=" * 70)
    
    stats = manager.get_statistics()
    print(f"Total Proxies: {stats['total_proxies']}")
    print(f"Active Proxies: {stats['active_proxies']}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Success Rate: {stats['overall_success_rate']:.1%}")
    print(f"Best Proxy: {stats['best_proxy']} (score: {stats['best_score']})")
    
    print("\n" + "=" * 70)
    print("Proxy Details")
    print("=" * 70)
    
    for details in manager.get_proxy_details():
        print(f"\n{details['proxy']}")
        print(f"  Active: {details['active']}")
        print(f"  Requests: {details['total_requests']}")
        print(f"  Success Rate: {details['success_rate']:.1%}")
        print(f"  Avg Response: {details['avg_response_time']:.2f}s")
        print(f"  Score: {details['score']:.3f}")
