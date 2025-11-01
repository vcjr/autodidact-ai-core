"""
QuestionAgentV2 - Graph-Enhanced Curriculum Generator
======================================================

This is an enhanced version of QuestionAgent that uses a knowledge graph
to create prerequisite-validated learning paths.

Key Improvements over V1:
- Uses ConceptGraph to find optimal learning paths
- Validates prerequisites before generating curriculum
- Retrieves targeted resources for each concept in the path
- Provides structured, pedagogically-sound curricula

Usage:
    from src.agents.question_agent_v2 import QuestionAgentV2
    
    agent = QuestionAgentV2()
    curriculum = agent.generate_curriculum(
        "I want to learn advanced piano, starting from scratch"
    )
    print(curriculum)
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import textwrap
from typing import List, Dict, Optional
from src.agents.question_agent import QuestionAgent
from src.knowledge_graph.concept_graph import ConceptGraph
from src.db_utils.chroma_client import COLLECTION_NAME_V2


class QuestionAgentV2(QuestionAgent):
    """
    Enhanced Question Agent with graph-based curriculum planning.
    
    Workflow:
    1. Scope: Extract domain/subdomain/difficulty (inherited from V1)
    2. Graph Search: Find optimal learning path with validated prerequisites
    3. Retrieve: Get targeted resources for each concept in the path
    4. Generate: Create structured curriculum with prerequisite validation
    
    This ensures:
    - No prerequisite violations (graph enforces order)
    - Smooth difficulty progression
    - Targeted resource retrieval (3 resources per concept vs. 5 random)
    - Better LLM reasoning (clear structure)
    """
    
    def __init__(self, collection_name: str = COLLECTION_NAME_V2):
        """
        Initialize enhanced curriculum generator.
        
        Args:
            collection_name: ChromaDB collection name (default: v2)
        """
        # Initialize base agent (inherits RAG functionality)
        super().__init__(collection_name)
        
        # Load or build concept graph
        print("\n🧠 Loading Concept Graph...")
        self.concept_graph = ConceptGraph()
        
        if not self.concept_graph.load_cache():
            print("   Graph cache not found, building from ChromaDB...")
            self.concept_graph.build_from_chroma(self.collection)
            self.concept_graph.save_cache()
        
        print("✅ QuestionAgentV2 initialized with knowledge graph\n")
    
    def generate_curriculum(self, user_query: str, user_level: Optional[str] = None) -> str:
        """
        Generate curriculum with graph-validated learning path.
        
        Args:
            user_query: User's learning goal
            user_level: Optional current skill level ("beginner", "intermediate", "advanced")
        
        Returns:
            Structured curriculum with validated prerequisites
        """
        print("\n" + "="*70)
        print("QuestionAgentV2: Graph-Enhanced Curriculum Generation")
        print("="*70)
        
        # Step 1: Scope (extract filters) - Inherited from base class
        print("\n📋 Step 1/4: Scoping Query")
        print("-"*70)
        
        chroma_filter = self.scope_agent.build_chroma_where_filter(user_query)
        
        if "error" in chroma_filter:
            return f"Error in curriculum generation: {chroma_filter['error']}"
        
        # Extract values from $and structure for display
        filter_values = self._extract_filter_values(chroma_filter)
        print(f"   Domain: {filter_values.get('domain_id', 'N/A')}")
        print(f"   Subdomain: {filter_values.get('subdomain_id', 'N/A')}")
        print(f"   Difficulty: {filter_values.get('difficulty', 'N/A')}")
        
        # Step 2: Find learning path using graph
        print("\n🗺️  Step 2/4: Finding Learning Path")
        print("-"*70)
        
        target_concept = self._build_concept_id(chroma_filter)
        print(f"   Target Concept: {target_concept}")
        
        # Determine starting point based on user level
        current_knowledge = self._infer_current_knowledge(
            chroma_filter, 
            user_level
        )
        
        learning_path = self.concept_graph.find_learning_path(
            target_concept=target_concept,
            current_knowledge=current_knowledge,
            max_difficulty_jump=0.4  # Allow reasonable jumps
        )
        
        if not learning_path or len(learning_path) == 0:
            # Fallback to original RAG if no path found
            print("   ⚠️  No graph path found, using standard RAG...")
            return super().generate_curriculum(user_query)
        
        print(f"   Learning Path ({len(learning_path)} steps):")
        for i, concept_id in enumerate(learning_path, 1):
            concept = self.concept_graph.get_concept_info(concept_id)
            if concept:
                print(f"      {i}. {concept.subdomain_id} ({concept.difficulty:.2f}) - {concept.resource_count} resources")
        
        # Step 3: Retrieve resources for each concept
        print("\n📚 Step 3/4: Retrieving Resources")
        print("-"*70)
        
        curriculum_modules = []
        
        for concept_id in learning_path:
            # Parse concept ID (format: DOMAIN_SUBDOMAIN_difficulty)
            parts = concept_id.split('_')
            
            if len(parts) >= 3:
                # Extract components
                # Handle cases like CODING_SOFTWARE_PYTHON_beginner
                # Find the difficulty term (should be last)
                difficulty_terms = ['beginner', 'intermediate', 'advanced', 'expert']
                difficulty = 'intermediate'
                subdomain_parts = []
                
                for i, part in enumerate(parts):
                    if part.lower() in difficulty_terms:
                        difficulty = part.lower()
                        subdomain_parts = parts[1:i]
                        break
                
                if not subdomain_parts:
                    # Fallback: assume last part is difficulty
                    difficulty = parts[-1].lower()
                    subdomain_parts = parts[1:-1]
                
                domain = parts[0]
                subdomain = '_'.join(subdomain_parts) if subdomain_parts else parts[1]
                
                # Build filter for this specific concept
                # ChromaDB requires $and operator for multiple conditions
                # Also include quality filter (same as ScopeAgent)
                concept_filter = {
                    "$and": [
                        {"domain_id": domain},
                        {"subdomain_id": subdomain},
                        {"difficulty": difficulty},
                        {"helpfulness_score": {"$gte": 0.55}}  # Quality threshold
                    ]
                }
                
                print(f"   Retrieving for: {domain}/{subdomain} ({difficulty})")
                
                # Retrieve context for this concept (fewer docs than V1)
                context = self._retrieve_context(
                    query=user_query,
                    chroma_filter=concept_filter,
                    k=3  # 3 resources per concept vs. 5 random in V1
                )
                
                # Get concept metadata
                concept = self.concept_graph.get_concept_info(concept_id)
                
                curriculum_modules.append({
                    'concept_id': concept_id,
                    'domain': domain,
                    'subdomain': subdomain,
                    'difficulty': difficulty,
                    'context': context,
                    'avg_quality': concept.avg_quality if concept else 0.5,
                    'resource_count': concept.resource_count if concept else 0
                })
        
        # Step 4: Generate structured curriculum
        print("\n✨ Step 4/4: Generating Structured Curriculum")
        print("-"*70)
        
        curriculum = self._generate_structured_curriculum(
            user_query,
            curriculum_modules,
            learning_path
        )
        
        print("✅ Curriculum generation complete\n")
        
        return curriculum
    
    def _extract_filter_values(self, chroma_filter: dict) -> dict:
        """
        Extract domain_id, subdomain_id, difficulty from ChromaDB filter structure.
        
        Args:
            chroma_filter: Filter dict with $and structure
            
        Returns:
            Dict with extracted values
        """
        values = {}
        
        if '$and' in chroma_filter:
            for condition in chroma_filter['$and']:
                if 'domain_id' in condition:
                    values['domain_id'] = condition['domain_id']
                elif 'subdomain_id' in condition:
                    values['subdomain_id'] = condition['subdomain_id']
                elif 'difficulty' in condition:
                    values['difficulty'] = condition['difficulty']
        
        return values
    
    def _build_concept_id(self, chroma_filter: dict) -> str:
        """
        Build concept ID from ChromaDB filter.
        
        Args:
            chroma_filter: Filter dict with $and structure from ScopeAgent
            
        Returns:
            Concept ID string (e.g., "MUSIC_PIANO_advanced")
        """
        # Extract values from $and structure
        domain = 'UNKNOWN'
        subdomain = 'UNKNOWN'
        difficulty = 'intermediate'
        
        if '$and' in chroma_filter:
            # Parse the $and conditions list
            for condition in chroma_filter['$and']:
                if 'domain_id' in condition:
                    domain = condition['domain_id']
                elif 'subdomain_id' in condition:
                    subdomain = condition['subdomain_id']
                elif 'difficulty' in condition:
                    difficulty = condition['difficulty']
        else:
            # Fallback for simple dict (shouldn't happen with ScopeAgent)
            domain = chroma_filter.get('domain_id', 'UNKNOWN')
            subdomain = chroma_filter.get('subdomain_id', 'UNKNOWN')
            difficulty = chroma_filter.get('difficulty', 'intermediate')
        
        return f"{domain}_{subdomain}_{difficulty}"
    
    def _infer_current_knowledge(
        self, 
        chroma_filter: dict,
        user_level: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        Infer user's current knowledge based on their level.
        
        Args:
            chroma_filter: Filter dict with domain/subdomain info
            user_level: User's stated skill level (optional)
            
        Returns:
            List of concept IDs user likely knows, or None
        """
        if user_level and user_level.lower() in ['beginner', 'complete beginner', 'starting from scratch']:
            # Start from the very beginning
            return None
        
        # Otherwise, let graph find beginner concepts in the domain
        return None
    
    def _generate_structured_curriculum(
        self,
        user_query: str,
        modules: List[Dict],
        learning_path: List[str]
    ) -> str:
        """
        Generate curriculum with validated structure.
        
        Uses LLM to polish the presentation but structure comes from graph.
        
        Args:
            user_query: Original user query
            modules: List of curriculum modules with resources
            learning_path: Ordered list of concept IDs
            
        Returns:
            Formatted curriculum text
        """
        # Build enhanced prompt with clear structure
        system_prompt = f"""
You are the Autodidact AI Curriculum Generator.

USER GOAL: {user_query}

You have been provided with a VALIDATED LEARNING PATH consisting of {len(modules)} modules.
These modules are ordered by prerequisites - each module builds on previous ones.

LEARNING PATH (in prerequisite order):
{' → '.join([f"{i+1}. {mod['subdomain']} ({mod['difficulty']})" for i, mod in enumerate(modules)])}

Your task is to create a comprehensive, structured curriculum that:
1. Respects the prerequisite order (Module 1 must be completed before Module 2, etc.)
2. Uses ONLY the provided resources (include URLs)
3. Provides clear learning objectives for each module
4. Estimates realistic time commitments
5. Explains why each module is important for the next

OUTPUT FORMAT:
# Learning Curriculum: [Title]

## Overview
- Total Modules: {len(modules)}
- Estimated Time: [Calculate from all modules]
- Difficulty Progression: {modules[0]['difficulty']} → {modules[-1]['difficulty']}

---

## Module 1: [Title]
**Difficulty:** [level]
**Estimated Time:** [hours/days]
**Prerequisites:** None (starting point)

### Learning Objectives
- [Objective 1]
- [Objective 2]
- [Objective 3]

### Curated Resources
1. [Resource name] - [URL]
   - Why this resource: [brief explanation]
2. [Resource name] - [URL]
   - Why this resource: [brief explanation]
3. [Resource name] - [URL]
   - Why this resource: [brief explanation]

### What You'll Learn
[2-3 sentences about skills/concepts gained]

### Why This Module Matters
[Explain how it prepares you for next module]

---

[Repeat for each module]

---

## Next Steps
[Guidance on what to do after completing the curriculum]

---

MODULES WITH RESOURCES:
"""
        
        # Add each module's resources
        for i, module in enumerate(modules, 1):
            system_prompt += f"""

{'='*70}
MODULE {i}: {module['subdomain'].replace('_', ' ').title()} ({module['difficulty']})
{'='*70}

Domain: {module['domain']}
Subdomain: {module['subdomain']}
Difficulty: {module['difficulty']}
Average Quality Score: {module['avg_quality']:.2f}
Total Available Resources: {module['resource_count']}

Retrieved Resources (Top 3):
{module['context']}

"""
        
        system_prompt += """

IMPORTANT GUIDELINES:
1. Extract resource URLs from the context (they're in the [Source: ...] lines)
2. Keep module descriptions concise but informative
3. Emphasize the prerequisite flow (why each module prepares for the next)
4. Use markdown formatting for readability
5. Be encouraging and motivational - this is for self-directed learners!
"""
        
        # Generate curriculum
        response = self.llm_client.generate_content(
            contents=[system_prompt]
        )
        
        return response.text


# End-to-end test
if __name__ == "__main__":
    print("\n" + "="*70)
    print("QuestionAgentV2 Demo")
    print("="*70)
    
    # Test queries
    test_queries = [
        "I want to learn advanced piano techniques, starting from scratch",
        "Create a learning path for Python programming",
        "Teach me electric guitar, I'm a complete beginner"
    ]
    
    # Initialize agent
    agent_v2 = QuestionAgentV2()
    
    # Test first query
    curriculum = agent_v2.generate_curriculum(test_queries[0])
    
    print("\n" + "="*70)
    print("GENERATED CURRICULUM")
    print("="*70)
    print(curriculum)
    print("="*70)
