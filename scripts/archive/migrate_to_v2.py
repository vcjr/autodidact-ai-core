#!/usr/bin/env python3
"""
Migration script to re-embed existing test data from legacy collection to v2 collection.

This script:
1. Retrieves all documents from the old collection (autodidact_ai_core with 384d embeddings)
2. Converts legacy metadata to UnifiedMetadata schema
3. Re-embeds content with all-mpnet-base-v2 (768d embeddings)
4. Stores in new v2 collection (autodidact_ai_core_v2)

Usage:
    python scripts/migrate_to_v2.py
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.db_utils.chroma_client import (
    get_chroma_client, 
    get_or_create_collection,
    COLLECTION_NAME_LEGACY,
    COLLECTION_NAME_V2
)
from src.models.unified_metadata_schema import create_manual_metadata, Difficulty
from src.agents.intake_agent import IntakeAgent

def migrate_legacy_metadata(legacy_meta: dict) -> dict:
    """
    Convert legacy metadata format to UnifiedMetadata format.
    
    Legacy format:
        {
            "instrument_id": "electric_guitar",
            "difficulty": "advanced",
            "technique": "sweeping",
            "helpfulness_score": 0.95,
            "source": "url",
            "text_length": 389
        }
    
    New format:
        UnifiedMetadata with domain_id, subdomain_id, etc.
    """
    # Parse instrument_id into domain and subdomain
    instrument_id = legacy_meta.get("instrument_id", "GENERAL")
    
    # Handle different legacy formats
    if "_" in instrument_id:
        parts = instrument_id.split("_")
        # Could be "electric_guitar" or "MUSIC_ELECTRIC_GUITAR"
        if len(parts) == 2 and parts[0].isupper():
            domain_id = parts[0]
            subdomain_id = parts[1]
        else:
            # Legacy lowercase format like "electric_guitar"
            domain_id = "MUSIC"  # Assume MUSIC for old data
            subdomain_id = "_".join(p.upper() for p in parts)
    else:
        domain_id = instrument_id.upper()
        subdomain_id = None
    
    # Map difficulty to enum
    difficulty_map = {
        "beginner": Difficulty.BEGINNER,
        "intermediate": Difficulty.INTERMEDIATE,
        "advanced": Difficulty.ADVANCED
    }
    difficulty = difficulty_map.get(
        legacy_meta.get("difficulty", "beginner").lower(),
        Difficulty.BEGINNER
    )
    
    # Create unified metadata
    unified_meta = create_manual_metadata(
        instrument_id=f"{domain_id}_{subdomain_id}" if subdomain_id else domain_id,
        source=legacy_meta.get("source", "unknown"),
        difficulty=difficulty,
        text_length=legacy_meta.get("text_length", 0),
        helpfulness_score=legacy_meta.get("helpfulness_score", 0.8),
        technique=legacy_meta.get("technique"),
        tags=[]
    )
    
    return unified_meta

def main():
    print("=" * 60)
    print("Migration: Legacy Collection → v2 Collection")
    print("=" * 60)
    
    client = get_chroma_client()
    
    # 1. Check if legacy collection exists
    try:
        legacy_collection = client.get_collection(name=COLLECTION_NAME_LEGACY)
        doc_count = legacy_collection.count()
        print(f"\n✅ Found legacy collection '{COLLECTION_NAME_LEGACY}' with {doc_count} documents")
    except Exception as e:
        print(f"\n⚠️  No legacy collection found: {e}")
        print("Nothing to migrate. Exiting.")
        return
    
    if doc_count == 0:
        print("Legacy collection is empty. Nothing to migrate.")
        return
    
    # 2. Get or create v2 collection
    v2_collection = get_or_create_collection(client, COLLECTION_NAME_V2)
    v2_initial_count = v2_collection.count()
    print(f"✅ v2 collection '{COLLECTION_NAME_V2}' has {v2_initial_count} documents")
    
    # 3. Retrieve all documents from legacy collection
    print(f"\n📥 Retrieving all documents from legacy collection...")
    legacy_data = legacy_collection.get(
        include=["documents", "metadatas"]
    )
    
    print(f"Retrieved {len(legacy_data['ids'])} documents")
    
    # 4. Initialize IntakeAgent for re-embedding
    intake_agent = IntakeAgent(collection_name=COLLECTION_NAME_V2)
    
    # 5. Migrate each document
    print(f"\n🔄 Migrating documents to v2 collection...")
    migrated_count = 0
    failed_count = 0
    
    for i, doc_id in enumerate(legacy_data['ids']):
        try:
            content = legacy_data['documents'][i]
            legacy_meta = legacy_data['metadatas'][i]
            
            print(f"\n  [{i+1}/{len(legacy_data['ids'])}] Migrating: {doc_id}")
            print(f"    Legacy metadata: {legacy_meta}")
            
            # Convert metadata
            unified_meta = migrate_legacy_metadata(legacy_meta)
            
            # Re-embed with new model
            new_doc_id = intake_agent.process_and_add_document(
                content=content,
                source_url=legacy_meta.get("source", "migrated"),
                metadata=unified_meta
            )
            
            print(f"    ✅ Migrated as: {new_doc_id}")
            migrated_count += 1
            
        except Exception as e:
            print(f"    ❌ Failed to migrate {doc_id}: {e}")
            failed_count += 1
            continue
    
    # 6. Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"✅ Successfully migrated: {migrated_count} documents")
    if failed_count > 0:
        print(f"❌ Failed to migrate: {failed_count} documents")
    
    v2_final_count = v2_collection.count()
    print(f"\nv2 collection now has {v2_final_count} documents (was {v2_initial_count})")
    
    print("\n💡 Next steps:")
    print("  1. Test queries against v2 collection")
    print("  2. If everything works, you can delete the legacy collection:")
    print(f"     client.delete_collection('{COLLECTION_NAME_LEGACY}')")
    print("  3. Update QuestionAgent to use v2 collection")

if __name__ == "__main__":
    main()
