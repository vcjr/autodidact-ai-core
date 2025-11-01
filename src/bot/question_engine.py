"""
Question Engine - Template Substitution System

Loads question templates and substitutes placeholders with actual domains/subdomains
to generate search queries for the crawler.

Usage:
    engine = QuestionEngine()
    queries = engine.generate_queries(domain_id="MUSIC", subdomain_id="PIANO", limit=10)
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass


@dataclass
class SearchQuery:
    """Represents a generated search query."""
    query: str
    domain_id: str
    subdomain_id: Optional[str]
    category: str
    skill_level: str
    platforms: List[str]
    template_id: int
    
    def __str__(self):
        return f"[{self.category}] {self.query}"


class QuestionEngine:
    """
    Generates search queries by substituting template placeholders with actual values.
    """
    
    def __init__(self, templates_path: Optional[Path] = None):
        """
        Initialize the question engine.
        
        Args:
            templates_path: Path to question_templates.json (auto-detected if None)
        """
        if templates_path is None:
            # Auto-detect path
            project_root = Path(__file__).parent.parent.parent
            templates_path = project_root / 'data' / 'question_templates.json'
        
        self.templates_path = templates_path
        self.templates = self._load_templates()
        
        # Cache for domain/subdomain data
        self.domains = self._load_domains()
        self.subdomains = self._load_subdomains()
        
        print(f"✅ QuestionEngine initialized:")
        print(f"   📦 {len(self.templates)} templates loaded")
        print(f"   🏷️  {len(set(t['category'] for t in self.templates))} categories")
        print(f"   🌍 {len(self.domains)} domains available")
        print(f"   🎯 {len(self.subdomains)} domain-subdomain pairs")
    
    def _load_templates(self) -> List[Dict]:
        """Load question templates from JSON."""
        with open(self.templates_path, 'r') as f:
            data = json.load(f)
        return data.get('question_templates', [])
    
    def _load_domains(self) -> List[str]:
        """Load domain IDs from domains.json."""
        project_root = Path(__file__).parent.parent.parent
        domains_path = project_root / 'data' / 'domains.json'
        
        with open(domains_path, 'r') as f:
            domains_data = json.load(f)
        
        return [d['id'] for d in domains_data]
    
    def _load_subdomains(self) -> Dict[str, List[str]]:
        """Load subdomain data from domains_with_subdomains.json."""
        project_root = Path(__file__).parent.parent.parent
        subdomains_path = project_root / 'data' / 'domains_with_subdomains.json'
        
        subdomains = {}
        
        try:
            with open(subdomains_path, 'r') as f:
                domains_data = json.load(f)
            
            for domain in domains_data:
                domain_id = domain.get('id')
                subs = domain.get('subdomains', [])
                
                if domain_id and subs:
                    # Extract subdomain names
                    subdomain_names = []
                    for sub in subs:
                        if isinstance(sub, dict):
                            # Subdomain is a dict with 'id' and 'description'
                            subdomain_full_id = sub.get('id', '')
                            # Extract subdomain part: "MUSIC_PIANO" -> "PIANO"
                            if subdomain_full_id.startswith(domain_id + '_'):
                                subdomain_name = subdomain_full_id[len(domain_id) + 1:]
                                subdomain_names.append(subdomain_name)
                        elif isinstance(sub, str):
                            # If subdomain is already a string
                            subdomain_names.append(sub)
                    
                    # Filter out empty strings
                    subdomain_names = [s for s in subdomain_names if s]
                    if subdomain_names:
                        subdomains[domain_id] = subdomain_names
                        
        except FileNotFoundError:
            print("⚠️  domains_with_subdomains.json not found, subdomain queries disabled")
        
        return subdomains
    
    def substitute_template(
        self,
        template: Dict,
        domain_id: str,
        subdomain_id: Optional[str] = None,
        skill_level: Optional[str] = None
    ) -> str:
        """
        Substitute placeholders in a template with actual values.
        
        Args:
            template: Template dictionary with 'template' and 'placeholders' keys
            domain_id: Domain ID (e.g., "MUSIC")
            subdomain_id: Optional subdomain (e.g., "PIANO")
            skill_level: Optional skill level override
        
        Returns:
            Substituted query string
        """
        query = template['template']
        placeholders = template.get('placeholders', [])
        
        # Build substitution map
        substitutions = {
            '${DOMAIN}': self._format_domain(domain_id, subdomain_id),
            '${SUBDOMAIN}': subdomain_id.replace('_', ' ').title() if subdomain_id else domain_id.replace('_', ' ').title(),
            '${LEVEL}': skill_level or self._get_random_skill_level(),
            '${RESOURCE}': self._get_random_resource(),
            '${TIMEFRAME}': self._get_random_timeframe(),
            '${TIME}': self._get_random_timeframe(),  # Alias for TIMEFRAME
            '${SKILL}': self._get_random_skill(),
            '${CONCEPT}': self._get_random_concept(),
            '${THEORY}': self._get_random_theory(),
            '${THEORETICAL_KNOWLEDGE}': self._get_random_theory(),
            '${PROBLEM}': self._get_random_problem(),
            '${TOOL}': self._get_random_tool(),
            '${TOPIC}': self._get_random_topic(),
        }
        
        # Add concept comparison placeholders
        if '${CONCEPT_A}' in query or '${CONCEPT_B}' in query:
            concepts = ['core principles', 'advanced techniques', 'fundamental methods', 
                       'best practices', 'modern approaches', 'traditional methods']
            random.shuffle(concepts)
            substitutions['${CONCEPT_A}'] = concepts[0] if len(concepts) > 0 else 'first approach'
            substitutions['${CONCEPT_B}'] = concepts[1] if len(concepts) > 1 else 'second approach'
        
        # Add tool comparison placeholders for ${TOOL_A} and ${TOOL_B}
        if '${TOOL_A}' in query or '${TOOL_B}' in query:
            tools = ['essential tools', 'recommended software', 'key equipment',
                    'useful utilities', 'productivity tools', 'popular frameworks',
                    'industry-standard tools', 'modern solutions']
            random.shuffle(tools)
            substitutions['${TOOL_A}'] = tools[0] if len(tools) > 0 else 'first tool'
            substitutions['${TOOL_B}'] = tools[1] if len(tools) > 1 else 'second tool'
        
        # Add method comparison placeholders for ${METHOD_A} and ${METHOD_B}
        if '${METHOD_A}' in query or '${METHOD_B}' in query:
            methods = ['structured learning', 'self-directed study', 'hands-on practice',
                      'guided instruction', 'peer collaboration', 'online courses',
                      'traditional classroom', 'project-based learning']
            random.shuffle(methods)
            substitutions['${METHOD_A}'] = methods[0] if len(methods) > 0 else 'first method'
            substitutions['${METHOD_B}'] = methods[1] if len(methods) > 1 else 'second method'
        
        # Add domain comparison placeholders for ${DOMAIN_A} and ${DOMAIN_B}
        if '${DOMAIN_A}' in query or '${DOMAIN_B}' in query:
            # Get two different domains for comparison
            available_domains = [d for d in self.domains if d != domain_id]
            if len(available_domains) >= 2:
                random.shuffle(available_domains)
                substitutions['${DOMAIN_A}'] = available_domains[0].replace('_', ' ').title()
                substitutions['${DOMAIN_B}'] = available_domains[1].replace('_', ' ').title()
            else:
                substitutions['${DOMAIN_A}'] = 'related field'
                substitutions['${DOMAIN_B}'] = 'alternative field'
        
        # Add field placeholder for career-related questions
        if '${FIELD}' in query:
            fields = ['software development', 'creative arts', 'professional practice',
                     'technical field', 'industry work', 'freelance work',
                     'academic research', 'teaching']
            substitutions['${FIELD}'] = random.choice(fields)
        
        # Add subdomain comparison placeholders if applicable
        if subdomain_id and '${SUBDOMAIN_A}' in query:
            # Get another random subdomain from same domain for comparison
            domain_subs = self.subdomains.get(domain_id, [])
            if len(domain_subs) >= 2:
                other_subs = [s for s in domain_subs if s != subdomain_id]
                if other_subs:
                    substitutions['${SUBDOMAIN_A}'] = subdomain_id.replace('_', ' ').title()
                    substitutions['${SUBDOMAIN_B}'] = random.choice(other_subs).replace('_', ' ').title()
        
        # Perform substitutions
        for placeholder, value in substitutions.items():
            query = query.replace(placeholder, value)
        
        return query
    
    def _format_domain(self, domain_id: str, subdomain_id: Optional[str] = None) -> str:
        """Format domain/subdomain for natural language."""
        if subdomain_id:
            # Use subdomain if available
            return subdomain_id.replace('_', ' ').title()
        else:
            # Use domain, handle multi-part IDs (e.g., CODING_SOFTWARE → Coding Software)
            return domain_id.replace('_', ' ').title()
    
    def _get_random_skill_level(self) -> str:
        """Get random skill level."""
        return random.choice(['beginner', 'intermediate', 'advanced', 'all'])

    
    def _get_random_resource(self) -> str:
        """Get random resource type."""
        return random.choice(['books', 'courses', 'tutorials', 'videos', 'podcasts', 'articles', 'tools'])
    
    def _get_random_timeframe(self) -> str:
        """Get random timeframe."""
        return random.choice(['1 week', '1 month', '3 months', '6 months', '1 year', '2 years'])
    
    def _get_random_skill(self) -> str:
        """Get random skill placeholder."""
        return random.choice([
            'technique', 'fundamentals', 'advanced methods', 'core concepts',
            'practical application', 'problem-solving', 'execution', 'implementation'
        ])
    
    def _get_random_concept(self) -> str:
        """Get random concept placeholder."""
        return random.choice([
            'core principles', 'fundamental concepts', 'advanced theory',
            'key techniques', 'underlying mechanics', 'essential patterns'
        ])
    
    def _get_random_theory(self) -> str:
        """Get random theory placeholder."""
        return random.choice([
            'theoretical foundations', 'core theory', 'fundamental principles',
            'conceptual framework', 'underlying theory', 'academic knowledge'
        ])
    
    def _get_random_problem(self) -> str:
        """Get random problem placeholder."""
        return random.choice([
            'common errors', 'typical mistakes', 'performance issues',
            'implementation challenges', 'technical difficulties', 'common pitfalls'
        ])
    
    def _get_random_tool(self) -> str:
        """Get random tool placeholder."""
        return random.choice([
            'essential tools', 'recommended software', 'key equipment',
            'useful utilities', 'productivity tools', 'development environment'
        ])
    
    def _get_random_topic(self) -> str:
        """Get random topic placeholder."""
        return random.choice([
            'fundamental topics', 'advanced subjects', 'core areas',
            'key domains', 'essential subjects', 'specialized topics'
        ])
    
    def generate_queries(
        self,
        domain_id: str,
        subdomain_id: Optional[str] = None,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        skill_level: Optional[str] = None,
        limit: int = 10,
        shuffle: bool = True
    ) -> List[SearchQuery]:
        """
        Generate search queries for a specific domain/subdomain.
        
        Args:
            domain_id: Domain ID (e.g., "MUSIC")
            subdomain_id: Optional subdomain (e.g., "PIANO")
            platform: Filter by platform (youtube/reddit/quora/blogs)
            category: Filter by category
            skill_level: Filter by skill level
            limit: Maximum number of queries to generate
            shuffle: Randomize template selection
        
        Returns:
            List of SearchQuery objects
        """
        # Filter templates
        filtered = self.templates.copy()
        
        if platform:
            filtered = [t for t in filtered if platform.lower() in [p.lower() for p in t.get('platforms', [])]]
        
        if category:
            filtered = [t for t in filtered if t.get('category', '').upper() == category.upper()]
        
        if skill_level:
            filtered = [t for t in filtered if t.get('skill_level', '').lower() == skill_level.lower() or t.get('skill_level', '').lower() == 'all']
        
        # Shuffle for variety
        if shuffle:
            random.shuffle(filtered)
        
        # Generate queries
        queries = []
        for template in filtered[:limit]:
            query_text = self.substitute_template(
                template=template,
                domain_id=domain_id,
                subdomain_id=subdomain_id,
                skill_level=skill_level
            )
            
            queries.append(SearchQuery(
                query=query_text,
                domain_id=domain_id,
                subdomain_id=subdomain_id or domain_id,
                category=template['category'],
                skill_level=template.get('skill_level', 'all'),
                platforms=template.get('platforms', []),
                template_id=template['id']
            ))
        
        return queries
    
    def generate_queries_batch(
        self,
        domains: List[str],
        platform: Optional[str] = None,
        queries_per_domain: int = 5
    ) -> Dict[str, List[SearchQuery]]:
        """
        Generate queries for multiple domains.
        
        Args:
            domains: List of domain IDs
            platform: Filter by platform
            queries_per_domain: Number of queries per domain
        
        Returns:
            Dictionary mapping domain_id to list of queries
        """
        results = {}
        
        for domain_id in domains:
            # Check if domain has subdomains
            subdomains = self.subdomains.get(domain_id, [])
            
            if subdomains:
                # Generate queries for each subdomain
                all_queries = []
                queries_per_sub = max(1, queries_per_domain // len(subdomains))
                
                for subdomain in subdomains[:5]:  # Limit to first 5 subdomains
                    queries = self.generate_queries(
                        domain_id=domain_id,
                        subdomain_id=subdomain,
                        platform=platform,
                        limit=queries_per_sub
                    )
                    all_queries.extend(queries)
                
                results[domain_id] = all_queries[:queries_per_domain]
            else:
                # Generate domain-level queries
                queries = self.generate_queries(
                    domain_id=domain_id,
                    platform=platform,
                    limit=queries_per_domain
                )
                results[domain_id] = queries
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get statistics about templates and coverage."""
        categories = {}
        platforms = {}
        skill_levels = {}
        
        for template in self.templates:
            # Count categories
            cat = template.get('category', 'UNKNOWN')
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count platforms
            for platform in template.get('platforms', []):
                platforms[platform] = platforms.get(platform, 0) + 1
            
            # Count skill levels
            level = template.get('skill_level', 'unknown')
            skill_levels[level] = skill_levels.get(level, 0) + 1
        
        return {
            'total_templates': len(self.templates),
            'categories': categories,
            'platforms': platforms,
            'skill_levels': skill_levels,
            'total_domains': len(self.domains),
            'domains_with_subdomains': len(self.subdomains),
            'total_subdomains': sum(len(subs) for subs in self.subdomains.values())
        }


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = QuestionEngine()
    
    # Get statistics
    print("\n📊 Template Statistics:")
    stats = engine.get_statistics()
    print(f"   Total templates: {stats['total_templates']}")
    print(f"   Categories: {len(stats['categories'])}")
    print(f"   Domains: {stats['total_domains']}")
    print(f"   Subdomains: {stats['total_subdomains']}")
    
    # Example 1: Generate queries for MUSIC/PIANO
    print("\n🎹 Example: MUSIC/PIANO queries (YouTube)")
    queries = engine.generate_queries(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        limit=5
    )
    
    for i, query in enumerate(queries, 1):
        print(f"   {i}. {query.query}")
        print(f"      Category: {query.category} | Level: {query.skill_level}")
    
    # Example 2: Generate queries for CODING_SOFTWARE/PYTHON
    print("\n🐍 Example: CODING_SOFTWARE/PYTHON queries (Reddit)")
    queries = engine.generate_queries(
        domain_id="CODING_SOFTWARE",
        subdomain_id="PYTHON",
        platform="reddit",
        limit=5
    )
    
    for i, query in enumerate(queries, 1):
        print(f"   {i}. {query.query}")
        print(f"      Category: {query.category} | Level: {query.skill_level}")
    
    # Example 3: Batch generation
    print("\n📦 Example: Batch generation (3 domains, 3 queries each)")
    batch = engine.generate_queries_batch(
        domains=["MUSIC", "CODING_SOFTWARE", "MARTIAL_ARTS"],
        platform="youtube",
        queries_per_domain=3
    )
    
    for domain, queries in batch.items():
        print(f"\n   {domain}:")
        for query in queries:
            print(f"      - {query.query}")
