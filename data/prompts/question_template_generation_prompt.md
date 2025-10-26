# PROMPT FOR AI AGENT: Generate Learning Question Templates for Self-Teaching

You are helping to create a question generation engine for an autodidact education platform that will search and crawl the internet (YouTube, blogs, Reddit, Quora) for educational content. Your task is to generate **at least 100 template questions** that represent the most common queries asked by self-learners across all domains and skill levels.

## CONTEXT

The platform has a hierarchical learning taxonomy with:
- **217 top-level domains** (e.g., MUSIC, CODING_SOFTWARE, MARTIAL_ARTS)
- **45+ domains with subdomains** (e.g., MUSIC_PIANO, CODING_PYTHON, MARTIAL_ARTS_BJJ)

These question templates will be used to:
1. Generate specific questions by inserting domain/subdomain names into placeholders
2. Search for relevant educational content across multiple platforms
3. Crawl and index learning resources for autodidacts
4. Match learner queries to existing content

## YOUR TASK

Generate **100+ question templates** that cover:
- Different skill levels (absolute beginner → advanced)
- Different learning aspects (theory, practice, troubleshooting, optimization)
- Different question types (how-to, what-is, comparison, recommendation, timeline)
- Different learner needs (tools, resources, motivation, assessment)

## TEMPLATE STRUCTURE

Each question template should use **placeholders** that can be dynamically filled:

### Placeholder Types:
- `${DOMAIN}` - Top-level domain (e.g., "guitar", "Python", "Brazilian Jiu-Jitsu")
- `${SKILL}` - Specific skill or concept (e.g., "chord progressions", "loops", "guard passing")
- `${TOOL}` - Tool, software, or equipment (e.g., "acoustic guitar", "VSCode", "gi")
- `${LEVEL}` - Skill level (e.g., "beginner", "intermediate", "advanced")
- `${RESOURCE}` - Resource type (e.g., "book", "course", "tutorial", "YouTube channel")
- `${TIME}` - Time period (e.g., "30 days", "6 months", "a year")
- `${TOPIC}` - Specific topic within domain (e.g., "music theory", "data structures", "takedowns")

## QUESTION CATEGORIES

Organize templates into these categories:

### 1. GETTING STARTED (Beginner Orientation)
Questions absolute beginners ask when starting from zero.
- "How to learn ${DOMAIN}?"
- "How to start learning ${DOMAIN} as a complete beginner?"
- "What do I need to start ${DOMAIN}?"

### 2. RESOURCE DISCOVERY
Questions about finding learning materials.
- "Best ${RESOURCE} for learning ${DOMAIN}?"
- "Free resources to learn ${DOMAIN}?"
- "Best YouTube channels for ${DOMAIN}?"

### 3. SKILL DEVELOPMENT
Questions about developing specific competencies.
- "How to improve ${SKILL} in ${DOMAIN}?"
- "How to master ${SKILL}?"
- "Techniques for better ${SKILL}?"

### 4. TOOL & EQUIPMENT
Questions about tools, software, gear, and equipment.
- "What ${TOOL} should I buy for ${DOMAIN}?"
- "Best ${TOOL} for ${LEVEL} in ${DOMAIN}?"
- "Do I need ${TOOL} to learn ${DOMAIN}?"

### 5. LEARNING PATH & PROGRESSION
Questions about learning sequence and progression.
- "What should I learn first in ${DOMAIN}?"
- "Learning path for ${DOMAIN}?"
- "How long does it take to learn ${DOMAIN}?"

### 6. COMMON PROBLEMS & TROUBLESHOOTING
Questions about obstacles and challenges.
- "Why am I struggling with ${SKILL}?"
- "Common mistakes in ${DOMAIN}?"
- "How to overcome ${PROBLEM} in ${DOMAIN}?"

### 7. COMPARISON & DECISION MAKING
Questions comparing options or approaches.
- "${OPTION_A} vs ${OPTION_B} for ${DOMAIN}?"
- "Should I learn ${DOMAIN_A} or ${DOMAIN_B} first?"
- "Which is better for ${DOMAIN}: ${APPROACH_A} or ${APPROACH_B}?"

### 8. PRACTICE & APPLICATION
Questions about hands-on practice and real-world application.
- "How to practice ${DOMAIN} effectively?"
- "Daily practice routine for ${DOMAIN}?"
- "Projects to improve ${DOMAIN} skills?"

### 9. ASSESSMENT & VALIDATION
Questions about measuring progress and getting feedback.
- "How to know if I'm good at ${DOMAIN}?"
- "How to test my ${DOMAIN} skills?"
- "Am I ready for ${NEXT_LEVEL} in ${DOMAIN}?"

### 10. MOTIVATION & MINDSET
Questions about staying motivated and overcoming mental barriers.
- "How to stay motivated learning ${DOMAIN}?"
- "Is it too late to learn ${DOMAIN}?"
- "Can I learn ${DOMAIN} without ${PREREQUISITE}?"

### 11. ADVANCED OPTIMIZATION
Questions from learners refining their skills.
- "How to take my ${DOMAIN} to the next level?"
- "Advanced techniques in ${DOMAIN}?"
- "How professionals approach ${SKILL} in ${DOMAIN}?"

### 12. COMMUNITY & NETWORKING
Questions about finding peers and mentors.
- "Where to find ${DOMAIN} community?"
- "Best forums for ${DOMAIN} learners?"
- "How to find a ${DOMAIN} mentor?"

### 13. CAREER & MONETIZATION
Questions about professional applications.
- "How to make money with ${DOMAIN}?"
- "Career opportunities in ${DOMAIN}?"
- "How to become a professional ${DOMAIN} practitioner?"

### 14. TIME & EFFICIENCY
Questions about optimizing learning time.
- "How to learn ${DOMAIN} in ${TIME}?"
- "Can I learn ${DOMAIN} while working full-time?"
- "How much time per day for ${DOMAIN}?"

### 15. THEORETICAL UNDERSTANDING
Questions about concepts and principles.
- "What is ${CONCEPT} in ${DOMAIN}?"
- "How does ${CONCEPT} work in ${DOMAIN}?"
- "Understanding ${TOPIC} in ${DOMAIN}?"

## OUTPUT SCHEMA

```json
{
  "question_templates": [
    {
      "id": 1,
      "category": "GETTING_STARTED",
      "template": "How to learn ${DOMAIN}?",
      "placeholders": ["DOMAIN"],
      "example": "How to learn guitar?",
      "platforms": ["youtube", "reddit", "quora", "blogs"],
      "skill_level": "beginner"
    },
    {
      "id": 2,
      "category": "GETTING_STARTED",
      "template": "How to start learning ${DOMAIN} as a complete beginner?",
      "placeholders": ["DOMAIN"],
      "example": "How to start learning piano as a complete beginner?",
      "platforms": ["youtube", "reddit", "quora", "blogs"],
      "skill_level": "beginner"
    },
    {
      "id": 3,
      "category": "RESOURCE_DISCOVERY",
      "template": "Best ${RESOURCE} for learning ${DOMAIN}?",
      "placeholders": ["RESOURCE", "DOMAIN"],
      "example": "Best books for learning Python?",
      "platforms": ["reddit", "quora", "blogs"],
      "skill_level": "all"
    }
  ]
}
```

## FIELD DEFINITIONS

- **id**: Unique sequential identifier (1-100+)
- **category**: One of the 15 categories listed above
- **template**: The question template with placeholders
- **placeholders**: Array of placeholder types used in the template
- **example**: A concrete example with placeholders filled in
- **platforms**: Which platforms this question type is commonly asked on
  - `youtube` - Video search queries
  - `reddit` - Reddit post titles and comments
  - `quora` - Quora questions
  - `blogs` - Blog post searches and titles
- **skill_level**: Target skill level
  - `beginner` - Complete novices
  - `intermediate` - Some experience
  - `advanced` - Experienced learners
  - `all` - Applicable to all levels

## QUALITY GUIDELINES

### ✅ DO:
- Create templates that are **platform-agnostic** (work across YouTube, Reddit, Quora, blogs)
- Use **natural language** that real people actually search for
- Cover **diverse learning needs** (not just "how to" questions)
- Include **variations** of similar questions (people phrase things differently)
- Make templates **broad enough** to work across multiple domains
- Include **casual/colloquial** phrasings (e.g., "best way to...", "easiest way to...")
- Think about **real search queries** people type into Google/YouTube
- Consider **question words**: How, What, When, Where, Why, Which, Should, Can, Is, Do
- Include templates for **negative/problem-focused** queries (e.g., "Why can't I...", "What am I doing wrong...")
- Add templates for **comparison queries** (vs, or, better, difference)

### ❌ DON'T:
- Create overly specific templates that only work for one domain
- Use academic or overly formal language
- Duplicate the same template with minor word changes
- Create templates that require multiple complex placeholders
- Make templates too long or convoluted
- Ignore the way people *actually* phrase questions online

## DIVERSITY REQUIREMENTS

Ensure coverage across:

1. **Question Length**:
   - Short: 3-5 words (e.g., "Learn ${DOMAIN} fast?")
   - Medium: 6-10 words (e.g., "How to get better at ${SKILL}?")
   - Long: 11+ words (e.g., "What is the best way to practice ${DOMAIN} if I only have ${TIME} per day?")

2. **Question Formality**:
   - Casual: "How do I get good at ${DOMAIN}?"
   - Standard: "How to improve ${DOMAIN} skills?"
   - Formal: "What is the most effective approach to mastering ${DOMAIN}?"

3. **Skill Level Distribution**:
   - 40% Beginner questions
   - 30% Intermediate questions
   - 20% Advanced questions
   - 10% All levels

4. **Platform Distribution** (each template should target 1-4 platforms):
   - YouTube: Video-friendly queries (tutorials, demonstrations, courses)
   - Reddit: Discussion-oriented, opinion-seeking, recommendation requests
   - Quora: Explanatory, comparative, advice-seeking questions
   - Blogs: How-to guides, deep dives, comprehensive tutorials

## EXAMPLE TEMPLATES BY CATEGORY

### GETTING STARTED
1. "How to learn ${DOMAIN}?"
2. "How to start ${DOMAIN}?"
3. "Complete beginner guide to ${DOMAIN}?"
4. "What do I need to start learning ${DOMAIN}?"
5. "Is ${DOMAIN} hard to learn?"
6. "How to teach yourself ${DOMAIN}?"
7. "Learning ${DOMAIN} from scratch?"
8. "Zero to hero in ${DOMAIN}?"

### RESOURCE DISCOVERY
9. "Best ${RESOURCE} for ${DOMAIN}?"
10. "Free resources to learn ${DOMAIN}?"
11. "Best YouTube channels for ${DOMAIN}?"
12. "Recommended ${RESOURCE} for ${LEVEL} ${DOMAIN}?"
13. "Where to learn ${DOMAIN} online?"
14. "Best online course for ${DOMAIN}?"
15. "Free vs paid ${DOMAIN} courses?"

### SKILL DEVELOPMENT
16. "How to improve ${SKILL} in ${DOMAIN}?"
17. "How to get better at ${SKILL}?"
18. "Tips for mastering ${SKILL}?"
19. "Fastest way to improve ${SKILL}?"
20. "How to practice ${SKILL} effectively?"

(Continue for all 15 categories...)

## SPECIAL CONSIDERATIONS

### For YouTube Queries:
- Include templates for tutorial discovery: "tutorial", "how to", "guide", "lesson"
- Course-finding: "full course", "complete guide", "learn in X minutes"
- Demonstration: "demo", "example", "walkthrough"

### For Reddit Queries:
- Include templates for recommendations: "best", "recommend", "suggestions"
- Discussion starters: "thoughts on", "opinions on", "is it worth"
- Success stories: "how I learned", "my experience with"

### For Quora Queries:
- Include templates for explanations: "what is", "how does", "why do"
- Comparisons: "difference between", "vs", "which is better"
- Advice-seeking: "should I", "is it worth", "can I"

### For Blog Searches:
- Include templates for comprehensive guides: "complete guide", "ultimate guide", "everything you need to know"
- Step-by-step: "step by step", "from scratch", "beginner to advanced"

## OUTPUT REQUIREMENTS

1. Generate **minimum 100 question templates** (ideally 120-150 for coverage)
2. Return valid JSON following the schema above
3. Distribute templates across all 15 categories
4. Ensure each category has at least 5 templates
5. Include diverse placeholder usage (don't rely only on ${DOMAIN})
6. Provide realistic, concrete examples for each template
7. Accurately tag platforms and skill levels

## VALIDATION CHECKLIST

Before submitting, verify:
- [ ] At least 100 unique templates
- [ ] All 15 categories represented
- [ ] Mix of beginner/intermediate/advanced
- [ ] All 4 platforms represented
- [ ] Natural, searchable language
- [ ] Valid JSON format
- [ ] Each template has example
- [ ] Diverse placeholder usage
- [ ] No duplicate templates
- [ ] Templates work across multiple domains

## INPUT DATA (Optional Context)

Reference the domains from:
```
./data/domains.json
./data/domains_with_subdomains.json
```

These can help you understand the breadth of topics the templates need to cover, but templates should be general enough to work across domains.

## BEGIN TASK

Generate 100+ question templates following the specifications above. Return only valid JSON matching the schema provided.
