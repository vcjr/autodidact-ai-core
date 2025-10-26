#!/usr/bin/env python3
"""
Generate 100+ question templates using the prompt and Gemini API.

This script:
1. Reads the question template generation prompt
2. Sends it to Gemini with structured JSON output
3. Saves the generated templates to data/question_templates.json
4. Validates the output against requirements

Usage:
    python scripts/generate_question_templates.py
"""

import sys
import os
import json

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.db_utils.llm_client import get_llm_client

def load_prompt():
    """Load the question template generation prompt from file."""
    prompt_path = os.path.join(project_root, 'data/prompts/question_template_generation_prompt.md')
    with open(prompt_path, 'r') as f:
        return f.read()

def load_domains():
    """Load domain data for context."""
    domains_path = os.path.join(project_root, 'data/domains.json')
    with open(domains_path, 'r') as f:
        domains = json.load(f)
    
    # Extract just the IDs for a concise list
    domain_ids = [d['id'] for d in domains]
    return domain_ids

def load_subdomains():
    """Load subdomain data for enhanced template generation."""
    subdomains_path = os.path.join(project_root, 'data/domains_with_subdomains.json')
    
    try:
        with open(subdomains_path, 'r') as f:
            domains_with_subs = json.load(f)
        
        # Extract subdomain examples for context
        subdomain_examples = []
        for domain in domains_with_subs:
            domain_id = domain.get('id', 'UNKNOWN')
            subdomains = domain.get('subdomains', [])
            
            # Get first 3 subdomains as examples
            for subdomain in subdomains[:3]:
                subdomain_examples.append(f"{domain_id}/{subdomain}")
        
        return subdomain_examples, len(domains_with_subs)
    
    except FileNotFoundError:
        print("⚠️  Warning: domains_with_subdomains.json not found, using domains only")
        return [], 0

def generate_templates_batch(batch_number, templates_per_batch, total_batches, domain_ids, subdomain_examples, subdomain_count, prompt):
    """Generate a single batch of templates.
    
    Args:
        batch_number: Current batch (1-indexed)
        templates_per_batch: Number of templates to generate in this batch
        total_batches: Total number of batches
        domain_ids: List of domain IDs
        subdomain_examples: List of subdomain examples
        subdomain_count: Count of domains with subdomains
        prompt: Base prompt text
    
    Returns:
        List of template dictionaries
    """
    print(f"\n� Batch {batch_number}/{total_batches}: Generating {templates_per_batch} templates...")
    
    # Calculate starting ID for this batch
    start_id = (batch_number - 1) * templates_per_batch + 1
    
    # Add batch-specific context
    context_addendum = f"""

## DOMAIN & SUBDOMAIN CONTEXT

The platform covers:
- **{len(domain_ids)} top-level domains** (e.g., MUSIC, CODING_SOFTWARE, LANGUAGES, MARTIAL_ARTS)
- **{subdomain_count} domains with subdomains** (e.g., MUSIC/PIANO, CODING_SOFTWARE/PYTHON, MARTIAL_ARTS/BJJ)

### Sample Domain Hierarchy:
{chr(10).join(subdomain_examples[:30])}
... and many more

### BATCH INFORMATION:
- This is batch {batch_number} of {total_batches}
- Generate EXACTLY {templates_per_batch} templates
- Start template IDs at {start_id}
- Focus on category diversity to complement other batches

### CRITICAL REQUIREMENTS:

1. **Generate EXACTLY {templates_per_batch} templates** (IDs {start_id} to {start_id + templates_per_batch - 1})

2. **Ensure DIVERSITY across batches:**
   - Batch {batch_number} should focus on different categories than other batches
   - Mix domain-level and subdomain-level templates
   - Vary skill levels (beginner, intermediate, advanced)
   - Cover all 4 platforms (youtube, reddit, quora, blogs)

3. **Template requirements:**
   - Domain level: "How to learn ${{DOMAIN}}?" → "How to learn music?"
   - Subdomain level: "How to learn ${{SUBDOMAIN}}?" → "How to learn piano?"
   - Cross-subdomain: "${{SUBDOMAIN_A}} vs ${{SUBDOMAIN_B}}?"
   - Platform-specific variants for each platform

4. **Categories to include** (distribute across batches):
   - how_to_learn, getting_started, resources, tutorials
   - comparison, prerequisites, roadmap, best_practices
   - troubleshooting, common_mistakes, tips_and_tricks
   - career_advice, time_management, motivation
   - tools_and_equipment, community_and_forums, certifications

5. **Placeholder examples:**
   - ${{DOMAIN}}, ${{SUBDOMAIN}}, ${{SUBDOMAIN_A}}, ${{SUBDOMAIN_B}}
   - ${{LEVEL}} (beginner/intermediate/advanced)
   - ${{RESOURCE}} (books/courses/tutorials/videos)
   - ${{TIMEFRAME}} (1 week/1 month/6 months/1 year)

**Generate EXACTLY {templates_per_batch} high-quality, diverse templates for this batch.**
"""
    
    full_prompt = prompt + context_addendum
    
    # Define JSON schema
    json_schema = {
        "type": "object",
        "properties": {
            "question_templates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "category": {"type": "string"},
                        "template": {"type": "string"},
                        "placeholders": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "example": {"type": "string"},
                        "platforms": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "skill_level": {"type": "string"}
                    },
                    "required": ["id", "category", "template", "placeholders", "example", "platforms", "skill_level"]
                }
            }
        },
        "required": ["question_templates"]
    }
    
    # Call Gemini API
    client = get_llm_client()
    
    try:
        response = client.generate_content(
            contents=[full_prompt],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": json_schema,
                "temperature": 0.7,  # Lower temperature to reduce safety filter triggers
                "max_output_tokens": 5120  # Conservative limit for 25 templates
            }
        )
        
        # Parse response
        try:
            batch_data = json.loads(response.text)
            templates = batch_data.get('question_templates', [])
            print(f"   ✅ Batch {batch_number}: {len(templates)} templates generated")
            return templates
            
        except json.JSONDecodeError as json_err:
            print(f"   ⚠️  Batch {batch_number} JSON error: {json_err}")
            # Save debug output
            debug_path = os.path.join(project_root, f'data/debug_batch_{batch_number}.txt')
            with open(debug_path, 'w') as f:
                f.write(response.text)
            print(f"   💾 Debug output saved to: {debug_path}")
            raise ValueError(f"Batch {batch_number} returned invalid JSON")
            
    except Exception as e:
        print(f"   ❌ Batch {batch_number} failed: {e}")
        raise


def generate_templates(target_count=200):
    """Generate question templates using batched Gemini API calls.
    
    Args:
        target_count: Total target number of templates (will be divided into batches)
    """
    print("=" * 60)
    print("Question Template Generation (Batched)")
    print("=" * 60)
    
    # 1. Load prompt and context
    print("\n📥 Loading prompt template...")
    prompt = load_prompt()
    
    print("📥 Loading domain data for context...")
    domain_ids = load_domains()
    
    print("📥 Loading subdomain data for enhanced coverage...")
    subdomain_examples, subdomain_count = load_subdomains()
    
    # 2. Calculate batching strategy
    # Reduced to 25 templates per batch for maximum reliability
    templates_per_batch = 25
    num_batches = (target_count + templates_per_batch - 1) // templates_per_batch  # Ceiling division
    
    print(f"\n📊 Batching strategy:")
    print(f"   🎯 Target: {target_count} templates")
    print(f"   📦 Batches: {num_batches} batches of ~{templates_per_batch} templates")
    print(f"   ⏱️  Estimated time: {num_batches * 20}-{num_batches * 35} seconds")
    print(f"   💡 Minimum acceptable: 100 templates (will continue with partial success)")
    
    # 3. Generate batches with retry logic
    all_templates = []
    max_retries = 2  # Retry failed batches up to 2 times
    failed_batches = []
    
    for batch_num in range(1, num_batches + 1):
        # Calculate templates for this batch (last batch might be smaller)
        if batch_num == num_batches:
            batch_size = target_count - len(all_templates)
        else:
            batch_size = templates_per_batch
        
        # Retry logic for this batch
        batch_success = False
        for retry in range(max_retries + 1):
            try:
                if retry > 0:
                    print(f"   🔄 Retry {retry}/{max_retries} for batch {batch_num}...")
                
                batch_templates = generate_templates_batch(
                    batch_number=batch_num,
                    templates_per_batch=batch_size,
                    total_batches=num_batches,
                    domain_ids=domain_ids,
                    subdomain_examples=subdomain_examples,
                    subdomain_count=subdomain_count,
                    prompt=prompt
                )
                
                all_templates.extend(batch_templates)
                print(f"   📊 Total so far: {len(all_templates)}/{target_count}")
                batch_success = True
                break  # Success - exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ⚠️  Batch {batch_num} attempt {retry + 1} failed: {error_msg[:100]}")
                
                # Check for safety filter (finish_reason=2)
                if "finish_reason" in error_msg and "2" in error_msg:
                    print(f"   🛡️  Safety filter triggered - skipping this batch")
                    failed_batches.append(batch_num)
                    break  # Don't retry safety-filtered batches
                
                if retry < max_retries:
                    print(f"   💤 Waiting 3 seconds before retry...")
                    import time
                    time.sleep(3)
                else:
                    print(f"   ❌ Batch {batch_num} failed after {max_retries + 1} attempts")
                    failed_batches.append(batch_num)
        
        # Continue generating even with some failures
        if not batch_success:
            print(f"   ⏭️  Skipping failed batch {batch_num}, continuing to next batch...")
    
    # 4. Report results
    print(f"\n✅ Batch generation complete!")
    print(f"   📊 Total templates: {len(all_templates)}")
    print(f"   ✅ Successful batches: {num_batches - len(failed_batches)}/{num_batches}")
    if failed_batches:
        print(f"   ⚠️  Failed batches: {failed_batches}")
    
    # Accept partial success if we have enough
    if len(all_templates) < 100:
        raise ValueError(f"Insufficient templates generated ({len(all_templates)} < 100)")
    elif len(all_templates) < target_count:
        print(f"   💡 Generated {len(all_templates)}/{target_count} (sufficient for Phase 2)")
    
    return {"question_templates": all_templates}

def validate_templates(templates_data):
    """Validate generated templates against requirements."""
    print("\n🔍 Validating templates...")
    
    templates = templates_data.get('question_templates', [])
    
    # Check 1: Count (updated target: 100+ minimum, 150-200 ideal)
    template_count = len(templates)
    if template_count < 100:
        print(f"⚠️  Warning: Only {template_count} templates generated (minimum: 100)")
        print(f"   💡 Consider regenerating for better coverage")
    elif template_count >= 100 and template_count < 150:
        print(f"✅ Good template count: {template_count} (minimum met, target: 150-200)")
    elif template_count >= 150:
        print(f"✅ Excellent template count: {template_count} (target: 150-200)")
    
    # Check 2: Category distribution
    categories = {}
    for t in templates:
        cat = t.get('category', 'UNKNOWN')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n📊 Category distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    # Check 3: Skill level distribution
    skill_levels = {}
    for t in templates:
        level = t.get('skill_level', 'unknown')
        skill_levels[level] = skill_levels.get(level, 0) + 1
    
    print(f"\n📊 Skill level distribution:")
    for level, count in sorted(skill_levels.items(), key=lambda x: -x[1]):
        percentage = (count / len(templates)) * 100
        print(f"   {level}: {count} ({percentage:.1f}%)")
    
    # Check 4: Platform coverage
    platform_usage = {}
    for t in templates:
        for platform in t.get('platforms', []):
            platform_usage[platform] = platform_usage.get(platform, 0) + 1
    
    print(f"\n📊 Platform coverage:")
    for platform, count in sorted(platform_usage.items(), key=lambda x: -x[1]):
        print(f"   {platform}: {count} templates")
    
    # Check 5: Subdomain-specific templates (NEW)
    subdomain_count = 0
    for t in templates:
        template_str = t.get('template', '')
        example_str = t.get('example', '')
        
        # Check for subdomain indicators
        if '${SUBDOMAIN}' in template_str or 'subdomain' in template_str.lower():
            subdomain_count += 1
        elif any(keyword in example_str.lower() for keyword in ['piano', 'python', 'guitar', 'bjj', 'javascript', 'jazz', 'acoustic', 'electric']):
            # Examples with specific subdomains
            subdomain_count += 1
    
    subdomain_percentage = (subdomain_count / template_count * 100) if template_count > 0 else 0
    print(f"\n🎯 Subdomain-specific templates: {subdomain_count} ({subdomain_percentage:.1f}%)")
    
    if subdomain_percentage < 20:
        print(f"   ⚠️  Low subdomain coverage ({subdomain_percentage:.1f}% < 20%)")
    else:
        print(f"   ✅ Good subdomain coverage!")
    
    # Check 6: Unique IDs
    ids = [t.get('id') for t in templates]
    if len(ids) != len(set(ids)):
        print("\n⚠️  Warning: Duplicate IDs found")
    else:
        print("\n✅ All template IDs are unique")
    
    # Check 7: Required fields
    missing_fields = []
    for i, t in enumerate(templates):
        required = ['id', 'category', 'template', 'placeholders', 'example', 'platforms', 'skill_level']
        for field in required:
            if field not in t:
                missing_fields.append(f"Template {i+1} missing '{field}'")
    
    if missing_fields:
        print(f"\n⚠️  Missing fields found:")
        for msg in missing_fields[:5]:  # Show first 5
            print(f"   {msg}")
        if len(missing_fields) > 5:
            print(f"   ... and {len(missing_fields) - 5} more")
    else:
        print("✅ All templates have required fields")
    
    # Updated validation criteria: 100+ templates with reasonable subdomain coverage
    passed = template_count >= 100 and len(missing_fields) == 0 and subdomain_percentage >= 15
    
    if passed:
        print("\n🎉 All validation checks passed!")
    elif template_count >= 100:
        print("\n✅ Minimum quality threshold met (100+ templates, usable for Phase 2)")
    
    return passed

def save_templates(templates_data):
    """Save templates to JSON file."""
    output_path = os.path.join(project_root, 'data/question_templates.json')
    
    with open(output_path, 'w') as f:
        json.dump(templates_data, f, indent=2)
    
    print(f"\n💾 Templates saved to: {output_path}")
    return output_path

def main():
    """Main execution with batched generation strategy."""
    try:
        # Generate templates using batched approach (50 templates per batch)
        # Target: 200 templates = 4 batches of 50
        templates_data = generate_templates(target_count=200)
        
        # Validate
        is_valid = validate_templates(templates_data)
        
        # Save
        output_path = save_templates(templates_data)
        
        # Summary
        print("\n" + "=" * 60)
        print("Generation Complete!")
        print("=" * 60)
        
        template_count = len(templates_data.get('question_templates', []))
        
        print(f"📊 Final count: {template_count} question templates")
        
        if is_valid:
            print(f"✅ All validation checks passed")
            print(f"\n📁 Output: {output_path}")
            print("\n🚀 Next steps:")
            print("   1. Review the templates in data/question_templates.json")
            print("   2. Test template substitution with sample domains")
            print("   3. Proceed to building the YouTube crawler")
        else:
            print(f"⚠️  Some validation issues found (still usable)")
            print(f"   Review output for details")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Verify GEMINI_API_KEY is set in .env")
        print("   3. Check data/debug_batch_*.txt for failed batches")
        sys.exit(1)

if __name__ == "__main__":
    main()
