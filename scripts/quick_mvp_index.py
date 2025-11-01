#!/usr/bin/env python3
"""
Quick MVP Indexing Script
=========================

Rapidly populates ChromaDB with high-quality educational content
across multiple domains for MVP demonstration.

Estimated time: 30-45 minutes for ~50 videos
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.bot.bot_indexer import BotIndexer


def quick_mvp_index():
    """
    Index core domains for MVP demonstration.
    
    Strategy:
    - 3 domains × 2 subdomains each = 6 combinations
    - 3 difficulty levels × 2 queries = 6 queries per combo
    - 3 videos per query
    - Total: ~54 high-quality videos
    """
    
    print("\n" + "="*70)
    print("MVP Quick Indexing Script")
    print("="*70)
    print("\nThis will index ~50-60 videos across multiple domains.")
    print("Estimated time: 30-45 minutes")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    input()
    
    # Initialize indexer with Apify (reliable, no IP blocks)
    indexer = BotIndexer(
        use_apify=True,
        use_quality_scorer=True,
        min_quality_score=0.55,  # Only high-quality content
    )
    
    # Define MVP content strategy
    mvp_domains = [
        # MUSIC domain
        {
            'domain_id': 'MUSIC',
            'subdomain_id': 'PIANO',
            'configs': [
                {'skill_level': 'beginner', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'intermediate', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'advanced', 'num_queries': 1, 'videos_per_query': 2},
            ]
        },
        {
            'domain_id': 'MUSIC',
            'subdomain_id': 'GUITAR',
            'configs': [
                {'skill_level': 'beginner', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'intermediate', 'num_queries': 1, 'videos_per_query': 2},
            ]
        },
        
        # CODING domain
        {
            'domain_id': 'CODING_SOFTWARE',
            'subdomain_id': 'PYTHON',
            'configs': [
                {'skill_level': 'beginner', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'intermediate', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'advanced', 'num_queries': 1, 'videos_per_query': 2},
            ]
        },
        {
            'domain_id': 'CODING_SOFTWARE',
            'subdomain_id': 'JAVASCRIPT',
            'configs': [
                {'skill_level': 'beginner', 'num_queries': 2, 'videos_per_query': 3},
                {'skill_level': 'intermediate', 'num_queries': 1, 'videos_per_query': 2},
            ]
        },
    ]
    
    total_indexed = 0
    total_errors = 0
    
    for i, domain_config in enumerate(mvp_domains, 1):
        domain_id = domain_config['domain_id']
        subdomain_id = domain_config['subdomain_id']
        
        print("\n" + "="*70)
        print(f"Domain {i}/{len(mvp_domains)}: {domain_id} / {subdomain_id}")
        print("="*70)
        
        for config in domain_config['configs']:
            print(f"\n🎯 Indexing {config['skill_level']} level...")
            
            try:
                result = indexer.index_domain(
                    domain_id=domain_id,
                    subdomain_id=subdomain_id,
                    **config
                )
                
                total_indexed += result.get('videos_indexed', 0)
                total_errors += result.get('errors', 0)
                
            except Exception as e:
                print(f"❌ Error indexing {domain_id}/{subdomain_id} ({config['skill_level']}): {e}")
                total_errors += 1
    
    # Print final summary
    print("\n" + "="*70)
    print("MVP Indexing Complete!")
    print("="*70)
    print(f"✅ Total Videos Indexed: {total_indexed}")
    print(f"❌ Total Errors: {total_errors}")
    print(f"📊 Success Rate: {(total_indexed / (total_indexed + total_errors) * 100):.1f}%")
    
    print("\n🎉 Next Steps:")
    print("   1. Build knowledge graph: python scripts/build_knowledge_graph.py")
    print("   2. Test curriculum generation: python -m src.agents.question_agent_v2")
    print("   3. Compare V1 vs V2: python scripts/compare_agents.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    quick_mvp_index()
