#!/usr/bin/env python3
"""
Minimal MVP Indexing - Ultra Fast
==================================

Indexes just enough content to test the knowledge graph system.
Perfect for rapid prototyping and testing.

Time: ~5-10 minutes for 15-20 videos
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.bot.bot_indexer import BotIndexer


def minimal_index():
    """
    Minimal indexing for quick testing.
    
    Strategy:
    - 1 domain (MUSIC)
    - 1 subdomain (PIANO)
    - 3 difficulty levels
    - 2 videos per level
    - Total: ~6 videos
    """
    
    print("\n" + "="*70)
    print("Minimal MVP Indexing (Ultra Fast)")
    print("="*70)
    print("\nIndexing 6-10 videos for quick testing...")
    print("Estimated time: 5-10 minutes\n")
    
    indexer = BotIndexer(
        use_apify=True,
        use_quality_scorer=True,
        min_quality_score=0.55
    )
    
    # Index just one subdomain with 3 difficulty levels
    for skill_level in ['beginner', 'intermediate', 'advanced']:
        print(f"\n📝 Indexing MUSIC/PIANO - {skill_level}")
        
        indexer.index_domain(
            domain_id='MUSIC',
            subdomain_id='PIANO',
            skill_level=skill_level,
            num_queries=1,  # Just 1 query per level
            videos_per_query=2  # Just 2 videos per query
        )
    
    print("\n✅ Minimal indexing complete!")
    print("\n🎯 Next Steps:")
    print("   1. Build graph: python scripts/build_knowledge_graph.py")
    print("   2. Test: python -m src.agents.question_agent_v2")
    print("="*70 + "\n")


if __name__ == "__main__":
    minimal_index()
