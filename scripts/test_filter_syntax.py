#!/usr/bin/env python3
"""
Quick test to verify ChromaDB filter syntax is working correctly
"""

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection

def test_filter_syntax():
    print("\n" + "="*70)
    print("Testing ChromaDB Filter Syntax")
    print("="*70)
    
    # Load collection
    client = get_chroma_client()
    collection = get_or_create_collection(client, "autodidact_ai_core_v2")
    
    print(f"\n✅ Collection loaded: {collection.count()} documents")
    
    # Test 1: Simple filter (should work)
    print("\n🧪 Test 1: Simple single-condition filter")
    try:
        results = collection.query(
            query_texts=["piano"],
            n_results=1,
            where={"domain_id": "MUSIC"}
        )
        print(f"   ✅ Single condition works: {len(results['ids'][0])} results")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 2: Multiple conditions with $and (correct syntax)
    print("\n🧪 Test 2: Multiple conditions with $and")
    try:
        results = collection.query(
            query_texts=["piano"],
            n_results=1,
            where={
                "$and": [
                    {"domain_id": "MUSIC"},
                    {"difficulty": "beginner"}
                ]
            }
        )
        print(f"   ✅ $and filter works: {len(results['ids'][0])} results")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Test 3: Multiple conditions WITHOUT $and (should fail)
    print("\n🧪 Test 3: Multiple conditions WITHOUT $and (should fail)")
    try:
        results = collection.query(
            query_texts=["piano"],
            n_results=1,
            where={
                "domain_id": "MUSIC",
                "difficulty": "beginner"
            }
        )
        print(f"   ⚠️  Unexpectedly worked: {len(results['ids'][0])} results")
    except ValueError as e:
        print(f"   ✅ Expected error caught: {str(e)[:80]}...")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    # Test 4: Complex filter (like ScopeAgent builds)
    print("\n🧪 Test 4: Complex filter with quality score")
    try:
        results = collection.query(
            query_texts=["piano advanced techniques"],
            n_results=2,
            where={
                "$and": [
                    {"domain_id": "MUSIC"},
                    {"subdomain_id": "PIANO"},
                    {"difficulty": "advanced"},
                    {"helpfulness_score": {"$gte": 0.55}}
                ]
            }
        )
        print(f"   ✅ Complex filter works: {len(results['ids'][0])} results")
        if results['metadatas'][0]:
            meta = results['metadatas'][0][0]
            print(f"      Sample: {meta.get('domain_id')}/{meta.get('subdomain_id')} - {meta.get('difficulty')}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "="*70)
    print("Filter Syntax Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_filter_syntax()
