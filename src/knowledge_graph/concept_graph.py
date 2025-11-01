"""
Concept Graph - Lightweight Knowledge Graph for Curriculum Planning
====================================================================

This module provides a NetworkX-based knowledge graph that extracts learning
concepts from your existing ChromaDB collection and builds prerequisite
relationships between them.

Key Features:
- Builds from existing data (no manual curation required)
- Uses difficulty levels to infer prerequisite relationships
- Finds optimal learning paths with validated prerequisites
- Caches to disk for fast loading

Usage:
    from src.knowledge_graph.concept_graph import ConceptGraph
    from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection
    
    # Build graph from ChromaDB
    client = get_chroma_client()
    collection = get_or_create_collection(client, "autodidact_ai_core_v2")
    
    graph = ConceptGraph()
    graph.build_from_chroma(collection)
    graph.save_cache()
    
    # Find learning path
    path = graph.find_learning_path(
        target_concept="MUSIC_PIANO_advanced",
        current_knowledge=["MUSIC_PIANO_beginner"]
    )
    print(f"Learning path: {' → '.join(path)}")
"""

import networkx as nx
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
import pickle
from pathlib import Path
from collections import defaultdict


@dataclass
class ConceptNode:
    """
    Represents a learnable concept extracted from content.
    
    Attributes:
        id: Unique identifier (e.g., "MUSIC_PIANO_intermediate")
        domain_id: Top-level domain (e.g., "MUSIC")
        subdomain_id: Specific subdomain (e.g., "PIANO")
        difficulty: Difficulty level as float (0.0=beginner, 1.0=expert)
        avg_quality: Average quality score from QualityScorer
        resource_count: Number of resources teaching this concept
        tags: Set of keywords extracted from content
    """
    id: str
    domain_id: str
    subdomain_id: str
    difficulty: float  # 0.0 (beginner) to 1.0 (expert)
    avg_quality: float = 0.5
    resource_count: int = 0
    tags: Set[str] = field(default_factory=set)
    
    def __repr__(self):
        return f"ConceptNode({self.id}, difficulty={self.difficulty:.2f}, quality={self.avg_quality:.2f})"


@dataclass  
class PrerequisiteEdge:
    """
    Represents a prerequisite relationship between concepts.
    
    Attributes:
        from_concept: Source concept ID (the prerequisite)
        to_concept: Target concept ID (depends on prerequisite)
        strength: Relationship strength (0.0=optional, 1.0=mandatory)
        evidence_count: Number of resources suggesting this relationship
    """
    from_concept: str
    to_concept: str
    strength: float = 0.8  # 0.0 (optional) to 1.0 (mandatory)
    evidence_count: int = 1


class ConceptGraph:
    """
    Lightweight knowledge graph for curriculum planning.
    
    This graph is built from your existing ChromaDB collection by:
    1. Grouping documents by (domain, subdomain, difficulty)
    2. Calculating concept statistics (quality, resource count)
    3. Inferring prerequisite relationships based on difficulty progression
    4. Caching the graph to disk for fast loading
    
    The graph enables:
    - Finding optimal learning paths with validated prerequisites
    - Ensuring smooth difficulty progression
    - Personalizing based on user's current knowledge
    
    Attributes:
        graph: NetworkX DiGraph storing concepts and prerequisites
        cache_path: Path to save/load cached graph
    """
    
    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize concept graph.
        
        Args:
            cache_path: Path to save/load cached graph (default: data/concept_graph.pkl)
        """
        self.graph = nx.DiGraph()
        self.cache_path = cache_path or Path("data/concept_graph.pkl")
        
    def build_from_chroma(self, collection):
        """
        Extract concepts from existing ChromaDB collection.
        
        Groups documents by (domain_id, subdomain_id, difficulty) to create
        concept nodes, then infers prerequisite relationships.
        
        Args:
            collection: ChromaDB collection instance
        """
        print("\n" + "="*70)
        print("Building Concept Graph from ChromaDB")
        print("="*70)
        
        # Get all documents with metadata
        results = collection.get(include=['metadatas'])
        
        if not results or not results.get('metadatas'):
            print("⚠️  No documents found in collection")
            return
        
        # Group by concept (domain + subdomain + difficulty)
        concept_stats = defaultdict(lambda: {
            'domain_id': '',
            'subdomain_id': '',
            'difficulty': 0.5,
            'quality_scores': [],
            'resource_count': 0,
            'tags': set()
        })
        
        print(f"\n📊 Processing {len(results['metadatas'])} documents...")
        
        skipped = 0
        for meta in results['metadatas']:
            domain = meta.get('domain_id', 'UNKNOWN')
            subdomain = meta.get('subdomain_id', 'UNKNOWN')
            difficulty = meta.get('difficulty', 'intermediate')
            
            # Skip documents with UNKNOWN or missing metadata
            if domain == 'UNKNOWN' or subdomain == 'UNKNOWN':
                skipped += 1
                continue
            
            quality = float(meta.get('helpfulness_score', meta.get('quality_score', 0.5)))
            technique = meta.get('technique', '')
            
            # Create concept ID
            concept_id = f"{domain}_{subdomain}_{difficulty}"
            
            # Update stats
            stats = concept_stats[concept_id]
            stats['domain_id'] = domain
            stats['subdomain_id'] = subdomain
            stats['difficulty'] = self._difficulty_to_float(difficulty)
            stats['quality_scores'].append(quality)
            stats['resource_count'] += 1
            
            # Extract tags from technique
            if technique:
                # Simple tag extraction: split on common separators
                words = technique.lower().replace('-', ' ').replace('_', ' ').split()
                stats['tags'].update(w for w in words if len(w) > 3)
        
        # Report skipped documents
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} documents with UNKNOWN domain/subdomain")
        
        # Add nodes to graph
        print(f"\n📦 Creating concept nodes...")
        
        for concept_id, stats in concept_stats.items():
            node = ConceptNode(
                id=concept_id,
                domain_id=stats['domain_id'],
                subdomain_id=stats['subdomain_id'],
                difficulty=stats['difficulty'],
                avg_quality=sum(stats['quality_scores']) / len(stats['quality_scores']),
                resource_count=stats['resource_count'],
                tags=stats['tags']
            )
            
            self.graph.add_node(
                concept_id,
                **node.__dict__
            )
        
        print(f"✅ Created {self.graph.number_of_nodes()} concept nodes")
        
        # Infer prerequisite edges
        self._infer_prerequisites()
        
        # Print summary
        self._print_summary()
        
    def _infer_prerequisites(self):
        """
        Infer prerequisite relationships using heuristics.
        
        Rules:
        1. Same subdomain: beginner → intermediate → advanced
        2. Within domain: foundational subdomains may be prerequisites
        """
        print(f"\n🔗 Inferring prerequisite relationships...")
        
        nodes = list(self.graph.nodes(data=True))
        edges_added = 0
        
        for node_id, node_data in nodes:
            domain = node_data['domain_id']
            subdomain = node_data['subdomain_id']
            difficulty = node_data['difficulty']
            
            # Rule 1: Within same subdomain, difficulty progression
            # If this is not a beginner concept, look for prerequisites
            if difficulty > 0.35:  # Not beginner
                # Find concepts in same subdomain with lower difficulty
                for other_id, other_data in nodes:
                    if (other_data['subdomain_id'] == subdomain and
                        other_data['difficulty'] < difficulty and
                        other_data['difficulty'] >= difficulty - 0.4 and  # Not too far back
                        not self.graph.has_edge(other_id, node_id)):
                        
                        # Add prerequisite edge
                        # Stronger edges for closer difficulty levels
                        difficulty_gap = difficulty - other_data['difficulty']
                        strength = max(0.6, 1.0 - difficulty_gap)
                        
                        self.graph.add_edge(
                            other_id, 
                            node_id,
                            strength=strength,
                            evidence_count=1,
                            type='difficulty_progression'
                        )
                        edges_added += 1
        
        print(f"✅ Inferred {edges_added} prerequisite edges")
    
    def find_learning_path(
        self,
        target_concept: str,
        current_knowledge: Optional[List[str]] = None,
        max_difficulty_jump: float = 0.4
    ) -> List[str]:
        """
        Find optimal learning path to target concept.
        
        Uses shortest path algorithm with difficulty constraints to ensure
        smooth learning progression.
        
        Args:
            target_concept: Concept ID to learn (e.g., "MUSIC_PIANO_advanced")
            current_knowledge: List of concept IDs already mastered (optional)
            max_difficulty_jump: Maximum allowed difficulty increase between steps
        
        Returns:
            List of concept IDs representing the learning path (ordered)
        """
        if target_concept not in self.graph:
            print(f"⚠️  Concept '{target_concept}' not found in graph")
            return [target_concept]  # Return target only
        
        # If no current knowledge specified, find beginner concepts in same domain
        if current_knowledge is None:
            target_data = self.graph.nodes[target_concept]
            domain = target_data['domain_id']
            subdomain = target_data['subdomain_id']
            
            # Find beginner concepts in same subdomain
            current_knowledge = [
                node for node, data in self.graph.nodes(data=True)
                if (data['domain_id'] == domain and
                    data['subdomain_id'] == subdomain and
                    data['difficulty'] < 0.35)  # Beginner level
            ]
        
        if not current_knowledge:
            print(f"ℹ️  No prerequisites found, starting from target")
            return [target_concept]
        
        # Find shortest valid path from any current knowledge to target
        shortest = None
        shortest_len = float('inf')
        
        for start in current_knowledge:
            if start not in self.graph:
                continue
                
            if nx.has_path(self.graph, start, target_concept):
                path = nx.shortest_path(self.graph, start, target_concept)
                
                # Validate difficulty jumps
                valid = True
                for i in range(len(path) - 1):
                    diff_jump = abs(
                        self.graph.nodes[path[i+1]]['difficulty'] - 
                        self.graph.nodes[path[i]]['difficulty']
                    )
                    if diff_jump > max_difficulty_jump:
                        valid = False
                        break
                
                if valid and len(path) < shortest_len:
                    shortest = path
                    shortest_len = len(path)
        
        if shortest:
            return shortest
        else:
            # No path found with constraints, return direct path or just target
            print(f"ℹ️  No valid path found with difficulty constraints")
            return [target_concept]
    
    def get_concept_info(self, concept_id: str) -> Optional[ConceptNode]:
        """
        Get detailed information about a concept.
        
        Args:
            concept_id: Concept ID to look up
            
        Returns:
            ConceptNode with concept details, or None if not found
        """
        if concept_id not in self.graph:
            return None
        
        data = self.graph.nodes[concept_id]
        return ConceptNode(**data)
    
    def _difficulty_to_float(self, difficulty: str) -> float:
        """Convert difficulty string to float value."""
        mapping = {
            'beginner': 0.2,
            'intermediate': 0.5,
            'advanced': 0.8,
            'expert': 0.95
        }
        return mapping.get(difficulty.lower(), 0.5)
    
    def _print_summary(self):
        """Print graph statistics."""
        print("\n" + "="*70)
        print("Concept Graph Summary")
        print("="*70)
        
        # Count by domain
        domain_counts = defaultdict(int)
        for _, data in self.graph.nodes(data=True):
            domain_counts[data['domain_id']] += 1
        
        print(f"\n📊 Statistics:")
        print(f"   Total Concepts: {self.graph.number_of_nodes()}")
        print(f"   Total Prerequisites: {self.graph.number_of_edges()}")
        print(f"   Unique Domains: {len(domain_counts)}")
        
        print(f"\n🏷️  Concepts by Domain:")
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {domain}: {count} concepts")
        
        # Average degree (prerequisites per concept)
        if self.graph.number_of_nodes() > 0:
            avg_degree = self.graph.number_of_edges() / self.graph.number_of_nodes()
            print(f"\n🔗 Average Prerequisites per Concept: {avg_degree:.2f}")
        
        print("="*70 + "\n")
    
    def save_cache(self):
        """Save graph to disk for fast loading."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'wb') as f:
            pickle.dump(self.graph, f)
        print(f"💾 Saved concept graph to {self.cache_path}")
    
    def load_cache(self) -> bool:
        """
        Load graph from disk.
        
        Returns:
            True if cache loaded successfully, False otherwise
        """
        if self.cache_path.exists():
            with open(self.cache_path, 'rb') as f:
                self.graph = pickle.load(f)
            print(f"📂 Loaded concept graph from {self.cache_path}")
            print(f"   Nodes: {self.graph.number_of_nodes()}, Edges: {self.graph.number_of_edges()}")
            return True
        return False


# Example usage
if __name__ == "__main__":
    from src.db_utils.chroma_client import get_chroma_client, get_or_create_collection
    
    print("Concept Graph Demo")
    print("="*70)
    
    # Load ChromaDB collection
    client = get_chroma_client()
    collection = get_or_create_collection(client, "autodidact_ai_core_v2")
    
    # Build graph
    graph = ConceptGraph()
    
    if not graph.load_cache():
        print("\n🔨 Building new graph from ChromaDB...")
        graph.build_from_chroma(collection)
        graph.save_cache()
    
    # Test: Find learning path
    print("\n🧪 Testing Learning Path Discovery")
    print("-"*70)
    
    # Example: Learn advanced piano
    target = "MUSIC_PIANO_advanced"
    
    if target in graph.graph:
        path = graph.find_learning_path(target_concept=target)
        
        print(f"\n📚 Learning Path to '{target}':")
        for i, concept_id in enumerate(path, 1):
            concept = graph.get_concept_info(concept_id)
            if concept:
                print(f"   {i}. {concept.id}")
                print(f"      Difficulty: {concept.difficulty:.2f}, Quality: {concept.avg_quality:.2f}, Resources: {concept.resource_count}")
    else:
        print(f"\n⚠️  Concept '{target}' not found in graph")
        print("\nAvailable concepts:")
        for i, node in enumerate(list(graph.graph.nodes())[:10], 1):
            print(f"   {i}. {node}")
