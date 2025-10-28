"""
Mock YouTube Crawler for Testing
=================================

Simulates YouTubeCrawler behavior with fake data to avoid hitting YouTube API limits.
Useful for:
- Testing the BotIndexer pipeline
- Development when YouTube blocks transcript requests
- CI/CD pipelines without API keys

Usage:
    from src.bot.crawlers.mock_youtube_crawler import MockYouTubeCrawler
    
    # Drop-in replacement for YouTubeCrawler
    crawler = MockYouTubeCrawler()
    results = crawler.search_and_extract_batch(queries)
"""

import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

# Handle imports for both direct execution and module import
try:
    from src.bot.crawlers.youtube_crawler import IndexableContent, VideoResult
    from src.bot.question_engine import SearchQuery
    from src.models.unified_metadata_schema import (
        UnifiedMetadata,
        Platform,
        ContentType,
        Difficulty
    )
except ModuleNotFoundError:
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    sys.path.insert(0, project_root)
    from src.bot.crawlers.youtube_crawler import IndexableContent, VideoResult
    from src.bot.question_engine import SearchQuery
    from src.models.unified_metadata_schema import (
        UnifiedMetadata,
        Platform,
        ContentType,
        Difficulty
    )


class MockYouTubeCrawler:
    """
    Mock implementation of YouTubeCrawler that generates realistic fake data.
    
    Features:
    - Same interface as YouTubeCrawler (drop-in replacement)
    - Generates realistic video metadata
    - Creates domain-specific transcripts
    - Simulates quota tracking
    - Configurable success rate for testing error handling
    """
    
    # Sample video titles by category
    SAMPLE_TITLES = {
        'GETTING_STARTED': [
            '{domain} for Complete Beginners - Start Here!',
            'Your First {domain} Lesson - Everything You Need',
            'Getting Started with {domain}: A Beginner\'s Guide',
            '{domain} Basics: What Every Beginner Should Know',
            'How to Start Learning {domain} from Scratch'
        ],
        'SKILL_DEVELOPMENT': [
            'Master {skill} in {domain}: Step-by-Step Tutorial',
            'Developing Advanced {skill} for {domain}',
            '{domain} Technique: Improving Your {skill}',
            'Essential {skill} Every {domain} Student Must Learn',
            'Level Up Your {domain} {skill} Today'
        ],
        'PRACTICE_AND_APPLICATION': [
            'Daily {domain} Practice Routine for Maximum Results',
            'How to Practice {domain} Effectively',
            '{domain} Exercises for Real-World Application',
            'Building a Consistent {domain} Practice Habit',
            'From Theory to Practice: {domain} Skills'
        ],
        'TOOL_AND_EQUIPMENT': [
            'Best {domain} Tools for Beginners in 2025',
            'Essential Equipment Every {domain} Student Needs',
            '{domain} Gear Guide: What to Buy First',
            'Budget-Friendly {domain} Tools That Work',
            'Professional vs Beginner {domain} Equipment'
        ],
        'THEORETICAL_UNDERSTANDING': [
            'Understanding {domain} Theory Simplified',
            'The Science Behind {domain}: Core Concepts',
            '{domain} Fundamentals Explained',
            'Why {domain} Works: Theory and Practice',
            'Deep Dive into {domain} Principles'
        ],
        'COMMON_PROBLEMS_AND_TROUBLESHOOTING': [
            'Top 10 {domain} Mistakes and How to Fix Them',
            'Troubleshooting Common {domain} Problems',
            'Why Your {domain} Isn\'t Improving (And How to Fix It)',
            '{domain} Errors Every Beginner Makes',
            'Solving the Hardest {domain} Challenges'
        ]
    }
    
    # Sample channel names
    SAMPLE_CHANNELS = [
        '{domain} Academy',
        'Learn {domain} Fast',
        '{domain} Mastery',
        'The {domain} Channel',
        '{domain} Pro Tips',
        '{domain} Tutorial Hub',
        'Master {domain} Today',
        '{domain} Expert',
        'Quick {domain} Lessons',
        '{domain} Coach'
    ]
    
    # Sample transcript templates
    TRANSCRIPT_TEMPLATES = [
        """Welcome back to another {domain} tutorial! Today we're going to cover {topic}, which is 
absolutely essential for anyone serious about {domain}. Many beginners struggle with this, but 
I'm going to break it down step by step so it's easy to understand.

First, let's talk about the fundamentals. {theory} is the foundation of everything we do in {domain}. 
Without understanding this core concept, you'll find it very difficult to progress to more advanced 
techniques.

Now, let me show you the practical application. The key here is to {skill} correctly. I see so many 
students making the mistake of rushing through this part, but if you take your time and really focus 
on {practice}, you'll see dramatic improvements in just a few weeks.

Let me demonstrate the technique. As you can see, the proper form involves {demonstration}. This 
might feel awkward at first, but trust the process. Your muscle memory will develop over time.

Common mistakes to avoid: Don't {mistake1}, and never {mistake2}. These are the two biggest pitfalls 
I see in my teaching practice.

For homework, I want you to practice {exercise} for at least 15 minutes daily. Consistency is more 
important than duration. It's better to practice correctly for 15 minutes than incorrectly for an hour.

If you found this helpful, make sure to subscribe and check out my other videos on {domain}. 
Next week, we'll be covering {next_topic}, so stay tuned!""",

        """Hey everyone! In today's video, we're diving deep into {domain} and specifically looking at 
{topic}. This is a topic I get asked about constantly in the comments, so I figured it was time 
to make a dedicated video.

Before we begin, quick disclaimer: {disclaimer}. Always {safety_note} when practicing {domain}.

So, why is {topic} important? Well, {explanation}. This is something that separates beginners from 
intermediate practitioners. Once you master this, you'll notice a huge jump in your overall skill level.

Let's break down the technique. Step one: {step1}. Step two: {step2}. Step three: {step3}. 
It sounds simple, but the devil is in the details. Pay close attention to {detail}.

I've been practicing {domain} for {years} years now, and I can tell you that {insight}. This was 
a game-changer for me when I was at your level.

Now, let's talk about common questions. People always ask: "{question1}" The answer is {answer1}. 
Another frequent question is "{question2}" and the truth is {answer2}.

Equipment-wise, you don't need anything fancy to get started. A basic {tool} will work perfectly fine. 
As you progress, you might want to invest in {advanced_tool}, but that's optional.

Practice tips: Set aside {time} minutes each day. Focus on quality over quantity. Use a metronome 
or timer to track your progress. And most importantly, be patient with yourself.

Remember, everyone progresses at their own pace. Don't compare yourself to others. The only person 
you should be competing with is yourself from yesterday.

Thanks for watching! Drop a comment below with your {domain} questions and I'll answer them in the 
next video. Don't forget to like and subscribe!""",

        """What's up {domain} enthusiasts! Today we're tackling one of the most requested topics: {topic}. 
This is crucial knowledge that will take your {domain} skills to the next level.

I'm going to assume you already know the basics. If you're completely new to {domain}, check out my 
beginner series first - I'll link it in the description below.

Alright, let's get technical. {theory} states that {explanation}. This principle has been proven 
time and time again by professionals in the field. Understanding this will completely change how 
you approach {domain}.

Here's where most people go wrong: they focus on {wrong_focus} instead of {right_focus}. I made 
this mistake for years before a mentor pointed it out to me. Don't be like me - learn from my 
mistakes!

The correct approach is to {correct_approach}. Notice how {observation}? That's the key indicator 
that you're doing it right.

Let me give you a real-world example. Last week, I was working on {project} and I needed to {goal}. 
By applying {technique}, I was able to {result}. This is the power of understanding {topic} properly.

Advanced tip for those ready: Try combining {technique1} with {technique2}. This creates a synergy 
that multiplies your effectiveness. But warning - only try this once you've mastered each technique 
individually.

Resources I recommend: {resource1}, {resource2}, and {resource3}. These are the books and courses 
that helped me the most when I was learning.

Practice routine: Start with {warmup} for 5 minutes. Then do {main_practice} for 20 minutes. 
Finish with {cooldown} for 5 minutes. This 30-minute routine, done daily, will transform your skills.

That's all for today! If you enjoyed this deep dive, smash that like button and let me know what 
topic you want me to cover next. See you in the next one!"""
    ]
    
    def __init__(
        self,
        max_results_per_query: int = 5,
        success_rate: float = 1.0,
        quota_limit: int = 10000
    ):
        """
        Initialize mock crawler.
        
        Args:
            max_results_per_query: Max videos per query (default 5)
            success_rate: Probability of successful extraction (0.0-1.0, default 1.0)
            quota_limit: Simulated daily quota limit
        """
        self.max_results_per_query = max_results_per_query
        self.success_rate = success_rate
        self.max_quota = quota_limit
        self.quota_used = 0
        self.seen_video_ids = set()
        
        print(f"✅ MockYouTubeCrawler initialized:")
        print(f"   📊 Daily quota: {self.max_quota:,} units (simulated)")
        print(f"   🔍 Max results per query: {self.max_results_per_query}")
        print(f"   🎯 Success rate: {self.success_rate * 100:.0f}%")
    
    def _generate_video_id(self) -> str:
        """Generate a fake YouTube video ID."""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        while True:
            video_id = ''.join(random.choices(chars, k=11))
            if video_id not in self.seen_video_ids:
                self.seen_video_ids.add(video_id)
                return video_id
    
    def _format_domain_for_content(self, domain_id: str, subdomain_id: Optional[str] = None) -> str:
        """Format domain/subdomain for use in content."""
        if subdomain_id:
            return subdomain_id.replace('_', ' ').title()
        return domain_id.replace('_', ' ').title()
    
    def _generate_title(self, query: SearchQuery) -> str:
        """Generate realistic video title based on query."""
        domain_text = self._format_domain_for_content(query.domain_id, query.subdomain_id)
        
        # Get category-specific templates or use generic
        category_templates = self.SAMPLE_TITLES.get(
            query.category,
            ['{domain}: ' + query.query]
        )
        
        template = random.choice(category_templates)
        
        # Fill in placeholders
        title = template.format(
            domain=domain_text,
            skill=random.choice(['technique', 'fundamentals', 'skills', 'methods', 'approach']),
            topic=random.choice(['core concepts', 'fundamentals', 'basics', 'essentials', 'principles'])
        )
        
        return title
    
    def _generate_description(self, title: str, domain_text: str) -> str:
        """Generate realistic video description."""
        descriptions = [
            f"Learn {domain_text} with this comprehensive tutorial. Perfect for beginners and intermediate students.",
            f"In this video, we cover everything you need to know about {domain_text}. Links and resources in the description!",
            f"Master {domain_text} step by step. Subscribe for more tutorials! Check out my course for deeper learning.",
            f"The ultimate {domain_text} guide. Join thousands of students learning effectively. Free PDF guide linked below!",
            f"Professional {domain_text} instructor breaks down the essentials. 10+ years experience teaching students worldwide."
        ]
        
        return random.choice(descriptions)
    
    def _generate_transcript(self, query: SearchQuery, title: str) -> str:
        """Generate realistic transcript based on query."""
        domain_text = self._format_domain_for_content(query.domain_id, query.subdomain_id)
        
        # Select random transcript template
        template = random.choice(self.TRANSCRIPT_TEMPLATES)
        
        # Fill in placeholders with context-appropriate content
        transcript = template.format(
            domain=domain_text,
            topic=random.choice(['core fundamentals', 'essential techniques', 'key concepts', 'practical skills']),
            theory=random.choice(['Progressive overload', 'Deliberate practice', 'Spaced repetition', 'Active learning']),
            skill=random.choice(['practice correctly', 'maintain proper form', 'focus on accuracy', 'build muscle memory']),
            practice=random.choice(['consistency', 'quality over quantity', 'mindful practice', 'deliberate repetition']),
            demonstration=random.choice(['proper posture and alignment', 'smooth controlled movements', 'precise execution', 'relaxed but focused form']),
            mistake1=random.choice(['rush through the basics', 'skip warmups', 'practice with poor form', 'ignore fundamentals']),
            mistake2=random.choice(['compare yourself to others', 'practice only when motivated', 'neglect rest days', 'focus on speed over accuracy']),
            exercise=random.choice(['basic drills', 'fundamental exercises', 'core movements', 'foundational techniques']),
            next_topic=random.choice(['advanced applications', 'common mistakes', 'practice strategies', 'performance optimization']),
            disclaimer=random.choice(['results may vary', 'consult a professional first', 'start slowly and build up', 'listen to your body']),
            safety_note=random.choice(['warm up properly', 'use proper equipment', 'maintain good form', 'start at your level']),
            explanation=random.choice(['it builds the foundation for everything else', 'mastering this unlocks advanced techniques', 'this is what separates amateurs from professionals', 'understanding this changes everything']),
            step1=random.choice(['establish proper positioning', 'set up your environment', 'prepare your mindset', 'gather necessary tools']),
            step2=random.choice(['execute the core movement', 'apply the fundamental technique', 'focus on key elements', 'implement the strategy']),
            step3=random.choice(['review and adjust', 'refine your execution', 'build consistency', 'track your progress']),
            detail=random.choice(['body positioning', 'timing and rhythm', 'breathing patterns', 'mental focus']),
            years=random.choice(['5', '10', '15', '8', '12']),
            insight=random.choice(['practice quality matters more than quantity', 'consistency beats intensity', 'fundamentals are never boring', 'slow progress is still progress']),
            question1='How long until I see results?',
            answer1=random.choice(['typically 4-6 weeks with daily practice', 'varies by person but expect 2-3 months', 'you should notice improvements within a month', 'most students see changes in 30-60 days']),
            question2='Do I need expensive equipment?',
            answer2=random.choice(['not at all - basics work fine for beginners', 'start simple and upgrade as you progress', 'expensive gear won\'t make you better', 'focus on technique first, gear second']),
            tool=random.choice(['practice tool', 'beginner-level equipment', 'standard setup', 'basic kit']),
            advanced_tool=random.choice(['professional-grade equipment', 'premium tools', 'advanced gear', 'high-end accessories']),
            time=random.choice(['15', '20', '30', '10', '25']),
            wrong_focus=random.choice(['speed', 'quantity', 'advanced techniques', 'complex methods']),
            right_focus=random.choice(['accuracy', 'fundamentals', 'proper form', 'consistency']),
            correct_approach=random.choice(['master the basics first', 'focus on quality repetitions', 'build solid foundations', 'practice with intention']),
            observation=random.choice(['the movement becomes smooth', 'it feels natural', 'you maintain control', 'there\'s no strain']),
            project=random.choice(['a challenging piece', 'a difficult task', 'an advanced application', 'a complex problem']),
            goal=random.choice(['improve my technique', 'master the skill', 'achieve consistency', 'reach the next level']),
            technique=random.choice(['focused practice', 'deliberate training', 'systematic approach', 'structured method']),
            result=random.choice(['achieve my goal in half the time', 'see dramatic improvement', 'break through my plateau', 'reach a new level']),
            technique1=random.choice(['visualization', 'slow practice', 'focused drills', 'micro-adjustments']),
            technique2=random.choice(['active rest', 'varied practice', 'feedback loops', 'progressive challenge']),
            resource1=random.choice(['The Practice of Practice', 'Peak Performance', 'Mastery', 'Atomic Habits']),
            resource2=random.choice(['online courses from top instructors', 'structured training programs', 'expert-led workshops', 'comprehensive guides']),
            resource3=random.choice(['community forums for feedback', 'practice journals', 'video analysis tools', 'progress tracking apps']),
            warmup=random.choice(['light exercises', 'basic movements', 'gentle preparation', 'mobility work']),
            main_practice=random.choice(['focused technique work', 'skill-specific drills', 'deliberate practice', 'targeted exercises']),
            cooldown=random.choice(['review and reflect', 'light stretching', 'mental review', 'relaxation exercises'])
        )
        
        return transcript
    
    def search_and_extract_batch(
        self,
        queries: List[SearchQuery],
        max_results_per_query: Optional[int] = None,
        delay_seconds: float = 0.5
    ) -> List[IndexableContent]:
        """
        Simulate batch video extraction with realistic fake data.
        
        Args:
            queries: List of SearchQuery objects
            max_results_per_query: Max videos per query
            delay_seconds: Simulated delay (default 0.5s for faster testing)
        
        Returns:
            List of IndexableContent with mock data
        """
        if max_results_per_query is None:
            max_results_per_query = self.max_results_per_query
        
        all_results = []
        
        print(f"\n🚀 Batch crawl: {len(queries)} queries (MOCK MODE)")
        print(f"   Rate limit: {delay_seconds}s delay between queries\n")
        
        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] Processing query...")
            print(f"\n🎬 Searching YouTube: '{query.query}' (MOCK)")
            print(f"   Domain: {query.domain_id}/{query.subdomain_id or 'N/A'}")
            print(f"   Category: {query.category} | Level: {query.skill_level}")
            
            # Simulate quota usage
            self.quota_used += 100  # Search query cost
            
            # Generate mock videos
            num_videos = random.randint(max(1, max_results_per_query - 2), max_results_per_query)
            print(f"🔍 Search: '{query.query}' → {num_videos} videos (quota: {self.quota_used}/{self.max_quota}) [MOCK]")
            
            for j in range(num_videos):
                # Simulate success rate
                if random.random() > self.success_rate:
                    print(f"   ⚠️  Skipping video {j+1}: Simulated failure")
                    continue
                
                # Generate mock video data
                video_id = self._generate_video_id()
                title = self._generate_title(query)
                domain_text = self._format_domain_for_content(query.domain_id, query.subdomain_id)
                description = self._generate_description(title, domain_text)
                transcript = self._generate_transcript(query, title)
                
                # Random channel name
                channel_template = random.choice(self.SAMPLE_CHANNELS)
                channel = channel_template.format(domain=domain_text)
                
                # Random engagement metrics
                views = random.randint(1000, 5000000)
                likes = int(views * random.uniform(0.02, 0.06))
                comments = int(views * random.uniform(0.001, 0.01))
                duration = random.randint(180, 1800)  # 3-30 minutes
                
                # Random publish date (within last 2 years)
                days_ago = random.randint(1, 730)
                published_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
                
                # Build full content
                full_content = f"Title: {title}\n\nDescription: {description}\n\nTranscript:\n{transcript}"
                
                # Create metadata
                difficulty_map = {
                    'beginner': Difficulty.BEGINNER,
                    'intermediate': Difficulty.INTERMEDIATE,
                    'advanced': Difficulty.ADVANCED,
                    'all': Difficulty.INTERMEDIATE
                }
                difficulty = difficulty_map.get(
                    query.skill_level.lower() if query.skill_level else 'intermediate',
                    Difficulty.INTERMEDIATE
                )
                
                metadata = UnifiedMetadata(
                    domain_id=query.domain_id,
                    subdomain_id=query.subdomain_id,
                    source=f"https://youtube.com/watch?v={video_id}",
                    platform=Platform.YOUTUBE,
                    content_type=ContentType.VIDEO,
                    author=channel,
                    created_at=datetime.fromisoformat(published_at.replace('Z', '+00:00')),
                    indexed_at=datetime.now(timezone.utc),
                    difficulty=difficulty,
                    technique=title[:200],
                    tags=[query.category] if query.category else [],
                    helpfulness_score=random.uniform(0.6, 0.95),  # Random quality score
                    engagement_metrics={
                        'views': views,
                        'likes': likes,
                        'comments': comments,
                        'duration_seconds': duration
                    },
                    text_length=len(full_content),
                    language="en"
                )
                
                indexable = IndexableContent(metadata=metadata, content=full_content)
                all_results.append(indexable)
                
                print(f"   ✅ Extracted: {title[:60]}... ({len(transcript)} chars) [MOCK]")
            
            print(f"\n📊 Extracted {num_videos}/{num_videos} videos with transcripts [MOCK]")
            
            # Simulate delay
            if i < len(queries):
                time.sleep(delay_seconds)
        
        print(f"\n✅ Batch complete: {len(all_results)} videos extracted [MOCK]")
        print(f"   Quota used: {self.quota_used}/{self.max_quota} units")
        
        return all_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get crawler statistics."""
        return {
            'quota_used': self.quota_used,
            'max_quota': self.max_quota,
            'quota_remaining': self.max_quota - self.quota_used,
            'videos_seen': len(self.seen_video_ids),
            'max_results_per_query': self.max_results_per_query
        }


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    sys.path.insert(0, project_root)
    
    from src.bot.question_engine import QuestionEngine
    
    print("=" * 70)
    print("Mock YouTube Crawler Demo")
    print("=" * 70)
    
    # Initialize
    engine = QuestionEngine()
    mock_crawler = MockYouTubeCrawler(max_results_per_query=3, success_rate=0.9)
    
    # Generate queries
    queries = engine.generate_queries(
        domain_id="MUSIC",
        subdomain_id="PIANO",
        platform="youtube",
        skill_level="beginner",
        limit=2
    )
    
    print(f"\n📝 Generated {len(queries)} queries")
    
    # Crawl (mock)
    results = mock_crawler.search_and_extract_batch(queries)
    
    # Display
    print("\n" + "=" * 70)
    print("Mock Results")
    print("=" * 70)
    
    for i, indexable in enumerate(results[:3], 1):
        meta = indexable.metadata
        print(f"\n📹 Video {i}:")
        print(f"   Title: {meta.technique}")
        print(f"   Channel: {meta.author}")
        print(f"   Views: {meta.engagement_metrics.get('views'):,}")
        print(f"   Content: {len(indexable.content):,} chars")
        print(f"   Preview: {indexable.content[:100]}...")
