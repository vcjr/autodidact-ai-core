#!/usr/bin/env python3
"""
Compare QuestionAgent V1 (RAG only) vs V2 (Graph + RAG)

This script runs the same query through both agents and compares outputs.

Usage:
    python scripts/compare_agents.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.agents.question_agent import QuestionAgent
from src.agents.question_agent_v2 import QuestionAgentV2


def main():
    print("\n" + "="*70)
    print("QuestionAgent V1 vs V2 Comparison")
    print("="*70)
    
    # Test queries
    test_queries = [
        "I want to learn advanced piano techniques, starting from scratch",
        "Create a learning path for Python programming for beginners",
        "Teach me electric guitar, I'm a complete beginner"
    ]
    
    # Initialize both agents
    print("\n🔧 Initializing agents...")
    print("   Loading V1 (RAG only)...")
    agent_v1 = QuestionAgent()
    
    print("   Loading V2 (Graph + RAG)...")
    agent_v2 = QuestionAgentV2()
    
    # Run comparison
    for i, query in enumerate(test_queries, 1):
        print("\n" + "="*70)
        print(f"Test Query {i}/{len(test_queries)}")
        print("="*70)
        print(f"Query: {query}\n")
        
        # V1 - RAG only
        print("🔹 V1 (RAG Only) - Generating...")
        print("-"*70)
        try:
            result_v1 = agent_v1.generate_curriculum(query)
            print("\n📄 V1 Output (first 500 chars):")
            print(result_v1[:500])
            print("..." if len(result_v1) > 500 else "")
        except Exception as e:
            print(f"❌ V1 Error: {e}")
            result_v1 = None
        
        print("\n")
        
        # V2 - Graph + RAG
        print("🔹 V2 (Graph + RAG) - Generating...")
        print("-"*70)
        try:
            result_v2 = agent_v2.generate_curriculum(query)
            print("\n📄 V2 Output (first 500 chars):")
            print(result_v2[:500])
            print("..." if len(result_v2) > 500 else "")
        except Exception as e:
            print(f"❌ V2 Error: {e}")
            result_v2 = None
        
        # Save full outputs
        output_dir = os.path.join(project_root, "reports")
        os.makedirs(output_dir, exist_ok=True)
        
        if result_v1:
            v1_file = os.path.join(output_dir, f"curriculum_v1_query{i}.md")
            with open(v1_file, 'w') as f:
                f.write(f"# Query: {query}\n\n")
                f.write(result_v1)
            print(f"\n💾 V1 full output saved to: {v1_file}")
        
        if result_v2:
            v2_file = os.path.join(output_dir, f"curriculum_v2_query{i}.md")
            with open(v2_file, 'w') as f:
                f.write(f"# Query: {query}\n\n")
                f.write(result_v2)
            print(f"💾 V2 full output saved to: {v2_file}")
        
        print("\n" + "-"*70)
        
        # Wait for user input before next query
        if i < len(test_queries):
            input("\nPress Enter to continue to next query...")
    
    print("\n" + "="*70)
    print("Comparison Complete")
    print("="*70)
    print("\n📊 Key Differences to Look For:")
    print("   V1 (RAG only):")
    print("   - May have random/unordered content")
    print("   - No explicit prerequisite validation")
    print("   - Might skip foundational topics")
    print("\n   V2 (Graph + RAG):")
    print("   - Structured learning path (beginner → intermediate → advanced)")
    print("   - Explicit prerequisites for each module")
    print("   - Validated difficulty progression")
    print("   - Targeted resource retrieval per concept")
    print("\n💡 Review the saved files in reports/ to compare full outputs")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
