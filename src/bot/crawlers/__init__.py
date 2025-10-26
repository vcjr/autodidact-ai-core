"""
Bot Crawlers Package
===================

Multi-platform content crawlers for automated knowledge base expansion.

Supported Platforms:
- YouTube: Video transcripts via YouTube Data API v3
- Reddit: Discussions via PRAW
- Quora: Q&A via Selenium
- Blogs: Articles via Google Custom Search + newspaper3k
"""

from .youtube_crawler import YouTubeCrawler

__all__ = ['YouTubeCrawler']
