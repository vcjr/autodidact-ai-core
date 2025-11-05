#!/usr/bin/env python3
"""
Build Knowledge Graph from ChromaDB

This script builds a concept graph from your existing ChromaDB collection
and caches it to disk for fast loading.

Usage:
    python scripts/build_knowledge_graph.py
    
The graph will be saved to: data/concept_graph.pkl
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.knowledge_graph.concept_graph import ConceptGraph
from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection

def main():
    print("\n" + "="*70)
    print("Knowledge Graph Builder")
    print("="*70)
    
    # Load ChromaDB collection
    print("\n📂 Loading ChromaDB collection...")
    client = get_chroma_client()
    collection = get_or_create_collection(client, "autodidact_ai_core_v2")
    
    # Get collection stats
    count = collection.count()
    print(f"   Collection: autodidact_ai_core_v2")
    print(f"   Documents: {count}")
    
    if count == 0:
        print("\n⚠️  Warning: Collection is empty!")
        print("   Run BotIndexer first to populate the collection.")
        return
    
    # Build graph
    print("\n🔨 Building concept graph...")
    graph = ConceptGraph()
    graph.build_from_chroma(collection)
    
    # Save to cache
    graph.save_cache()
    
    # Test: Find a few example paths
    print("\n🧪 Testing Learning Path Discovery")
    print("-"*70)
    
    # Get some example concepts
    nodes = list(graph.graph.nodes())[:5]
    
    print(f"\nExample concepts in graph:")
    for i, node in enumerate(nodes, 1):
        concept = graph.get_concept_info(node)
        if concept:
            print(f"   {i}. {node}")
            print(f"      Quality: {concept.avg_quality:.2f}, Resources: {concept.resource_count}")
    
    # Try to find a path
    if len(nodes) >= 2:
        print(f"\n🗺️  Finding path from {nodes[0]} to {nodes[-1]}...")
        path = graph.find_learning_path(
            target_concept=nodes[-1],
            current_knowledge=[nodes[0]]
        )
        
        if path:
            print(f"\n📚 Learning Path ({len(path)} steps):")
            for i, concept_id in enumerate(path, 1):
                print(f"   {i}. {concept_id}")
        else:
            print("   No path found")
    
    print("\n✅ Graph building complete!")
    print(f"   Saved to: {graph.cache_path}")
    print("\n💡 Next steps:")
    print("   1. Use QuestionAgentV2 for graph-enhanced curriculum generation")
    print("   2. Run: python -m src.agents.question_agent_v2")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
