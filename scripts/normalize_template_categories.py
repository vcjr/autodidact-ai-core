#!/usr/bin/env python3
"""
Normalize category names in question_templates.json
Fixes inconsistent formatting (spaces, ampersands, underscores)
"""

import json
import os
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.parent

def normalize_category_name(category):
    """Normalize category name to consistent format.
    
    Rules:
    1. Convert to uppercase
    2. Replace spaces with underscores
    3. Replace '&' with 'AND'
    4. Remove duplicate underscores
    5. Strip leading/trailing underscores
    6. Map common variations to canonical names
    """
    if not category:
        return "UNCATEGORIZED"
    
    # Convert to uppercase
    normalized = category.upper()
    
    # Replace '&' with 'AND'
    normalized = normalized.replace('&', 'AND')
    
    # Replace spaces with underscores
    normalized = normalized.replace(' ', '_')
    
    # Remove duplicate underscores
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    # Strip leading/trailing underscores
    normalized = normalized.strip('_')
    
    # Map variations to canonical names
    canonical_mapping = {
        # Remove redundant suffixes that mean the same thing
        'COMMON_PROBLEMS_TROUBLESHOOTING': 'COMMON_PROBLEMS_AND_TROUBLESHOOTING',
        'PRACTICE_APPLICATION': 'PRACTICE_AND_APPLICATION',
        'COMPARISON_DECISION_MAKING': 'COMPARISON_AND_DECISION_MAKING',
        'ASSESSMENT_VALIDATION': 'ASSESSMENT_AND_VALIDATION',
        'CAREER_MONETIZATION': 'CAREER_AND_MONETIZATION',
        'COMMUNITY_NETWORKING': 'COMMUNITY_AND_NETWORKING',
        'MOTIVATION_MINDSET': 'MOTIVATION_AND_MINDSET',
        'LEARNING_PATH_PROGRESSION': 'LEARNING_PATH_AND_PROGRESSION',
        'TOOL_EQUIPMENT': 'TOOL_AND_EQUIPMENT',
        'TIME_EFFICIENCY': 'TIME_AND_EFFICIENCY',
    }
    
    # Apply canonical mapping
    if normalized in canonical_mapping:
        normalized = canonical_mapping[normalized]
    
    return normalized


def main():
    print("=" * 60)
    print("Normalizing Question Template Categories")
    print("=" * 60)
    
    # 1. Load templates
    templates_path = project_root / 'data' / 'question_templates.json'
    
    print(f"\n📥 Loading templates from: {templates_path}")
    
    with open(templates_path, 'r') as f:
        data = json.load(f)
    
    templates = data.get('question_templates', [])
    print(f"   Found {len(templates)} templates")
    
    # 2. Analyze current categories
    print("\n📊 Current category distribution:")
    categories_before = {}
    for template in templates:
        cat = template.get('category', 'UNCATEGORIZED')
        categories_before[cat] = categories_before.get(cat, 0) + 1
    
    for cat, count in sorted(categories_before.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    print(f"\n   Total unique categories: {len(categories_before)}")
    
    # 3. Normalize categories
    print("\n🔧 Normalizing categories...")
    
    category_mapping = {}  # Track what changed
    
    for template in templates:
        original = template.get('category', '')
        normalized = normalize_category_name(original)
        
        if original != normalized:
            if original not in category_mapping:
                category_mapping[original] = normalized
        
        template['category'] = normalized
    
    # 4. Show what changed
    if category_mapping:
        print(f"\n✏️  Category changes:")
        for original, normalized in sorted(category_mapping.items()):
            print(f"   '{original}' → '{normalized}'")
    else:
        print("\n✅ All categories already normalized!")
    
    # 5. Analyze normalized categories
    print("\n📊 Normalized category distribution:")
    categories_after = {}
    for template in templates:
        cat = template.get('category', 'UNCATEGORIZED')
        categories_after[cat] = categories_after.get(cat, 0) + 1
    
    for cat, count in sorted(categories_after.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    print(f"\n   Total unique categories: {len(categories_after)} (was {len(categories_before)})")
    
    # 6. Save normalized templates
    print(f"\n💾 Saving normalized templates...")
    
    with open(templates_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"   ✅ Saved to: {templates_path}")
    
    # 7. Summary
    print("\n" + "=" * 60)
    print("Normalization Complete!")
    print("=" * 60)
    print(f"✅ Processed {len(templates)} templates")
    print(f"✅ Consolidated {len(categories_before)} → {len(categories_after)} categories")
    print(f"✅ Changed {len(category_mapping)} category names")
    
    if len(categories_after) <= 15:
        print("\n📋 Final category list:")
        for cat in sorted(categories_after.keys()):
            print(f"   - {cat}")


if __name__ == "__main__":
    main()
