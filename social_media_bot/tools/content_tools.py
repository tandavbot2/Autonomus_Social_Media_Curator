import os
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import re
import json
from crewai.tools import BaseTool
from litellm import completion
import hashlib
from ..database.db_manager import DatabaseManager
from pydantic import BaseModel, Field, validator, PrivateAttr
from textblob import TextBlob
from collections import Counter
from ..platforms.manager import PlatformManager
from ..models.platform import Platform
import random
from newsapi import NewsApiClient

logger = logging.getLogger(__name__)

class ContentGeneratorSchema(BaseModel):
    digest: Dict[str, Any] = Field(description="Content digest containing the content to generate from")
    platform: str = Field(description="Target platform (must be 'linkedin' or 'twitter')")

    @validator('platform')
    def validate_platform(cls, v):
        v = str(v).strip('"\'').lower()
        if v not in ['linkedin', 'twitter']:
            raise ValueError("Platform must be either 'linkedin' or 'twitter'")
        return v

    @validator('digest')
    def validate_digest(cls, v):
        if not isinstance(v, dict):
            raise ValueError("digest must be a dictionary")
        
        content_data = v.get('content', {})
        if not isinstance(content_data, dict):
            raise ValueError("digest['content'] must be a dictionary")
        
        if 'combined_digest' not in content_data:
            raise ValueError("digest['content'] must contain 'combined_digest' key")
        
        return v

class ContentGenerator(BaseTool):
    name: str = "Generate content"
    description: str = """Generate platform-specific content for LinkedIn or Twitter only.
    Required input format:
    {
        "digest": {
            "content": {
                "combined_digest": "your content summary here"
            }
        },
        "platform": "linkedin" or "twitter" or ["linkedin", "twitter"]  # Can be single platform or list
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._db = DatabaseManager()
        self._prompts = {
            'linkedin': r"""
Role: You are an expert LinkedIn content creator specialized in crafting engaging, educational content with a friendly and conversational tone.
Task: You have to copy the style, tone, format of the examples and then write LinkedIn posts based on the news summaries and context provided, focusing on increasing engagement and educating the audience.
Specifics:
Tone: Friendly, Educative, Conversationalist, FOMO Infused
Content: Based on news summaries provided
Keywords: AI, Business, engagement, educate, LinkedIn
Context:

Posts should be based on the news summaries given
Rewrite by copying the style, tone and format of the examples
Goal is to make posts engaging and enjoyable while being informative

Examples:
" "It's been three days since The Winner's New Year began.



Double work. Double Train. Double Winning.



Do you not FEEL the excitement in the air?



THE POWER??



All the losers are asleep these days, frozen in time, dreaming.



While Winners have been working.



This is why winners win and losers lose.



It has nothing to do with luck,



Nothing to do with IQ or genetics.



It is actually extremely simple.



Winners do what losers won't.



Winners work, while losers rest.



YOU are poor because you've lived most of your life as a loser.



Potentially even now.



Did you train twice today?



Worked twice as long as normal?



Or,



Are you a loser like everyone else?



Destined to the same fate as the average.



When you see the truly powerful of this world buy anything they want and shape the world.



When you see the ever-lasting DYNASTIES built and secured for entire bloodlines.



When you look at your family or friends go through hard times, unable to help them because you can barely help yourself.



I want you to understand it was entirely because of decisions made on days like today.



The days where lines are drawn.



Winners, losers.



The only difference is the decisions they make.



What decision did you make?



Double Train? Double Work?



Or did you CHOOSE to stay a loser.



"BuT TaTE, I DoNT kNoW WHaT tO Do"



I have built an entire program, designed specifically to turn the unremarkable into the remarkable within one year.



It is only open for enrollment until December 31st at 11:59 pm.



If you TRULY gave a fuck about becoming a winner, you would enroll and then never need to wonder what to do ever again.



Finance, Physical, Mental, you would be transformed in all realms.



But you already know this, you've given yourself some bullshit reason to not enroll.



"MaYbE iN 2026" you tell yourself.



Is today the day you will decide to change your life?



I doubt it.



But if it is. We begin DOUBLE WORK DOUBLE TRAINING UNLIMITED POWER AIKIDO&#x20;



Inside."\


"A worm exists in the dirt. &#x20;



Unnoticed and uncared for. &#x20;



Blind - unable to accurately perceive the world around him.&#x20;



Ugly and unloved.&#x20;



If you see a dead dog in the street, it sparks emotion. &#x20;



If you see a dead worm, you don't care. Nobody does.



There isn't a single fable in history which has described the valor of a worm. &#x20;



Or a worm's courage.&#x20;



In fact,



There are no stories about worms at all.&#x20;



They are insignificant to the pages of history and disappear from thought the second they are destroyed.&#x20;



Even children chop them up for fun.&#x20;



The musings of a worm are of no interest to anybody.&#x20;



Nobody cares if a worm is happy or sad.&#x20;



Watch a lion in the jungle and stare into his wizened eyes, you will wonder what he thinks.&#x20;



Nobody cares about the thoughts of a worm.&#x20;



Nobody wonders what a worm is contemplating.&#x20;



Nobody asks for the opinion of a worm.&#x20;



Nobody thinks: "What would a worm do?"



The worm is ultimately pathetic.&#x20;



On every measurable level.&#x20;



And you sir.



Are a worm.



Most perplexing of all, is that you don't even NEED to be one.



It is a choice.



You make the decision every day,



You CHOOSE to do nothing, you CHOOSE not to act.



And here I am giving you a blueprint, a path to change.



A year-long program specifically designed for the worms of the world.



You do not need motivation, you do not need discipline, you do not need any prior knowledge.



You are given a coach who will yell at you every morning to remind you of what you must do.



TO REMIND YOU TO BECOME SOMEONE OF IMPORTANCE.



You will have access to specific fitness training programs along with a fitness coach.



You will have access to over 6 different ways to make money online, each with its own coach to guide you on how to make 10s of thousands of dollars online.



You will be told what to do, exactly how to do it.



EVERYTHING TO TRANSFORM YOU FROM A WORM TO A SOMEBODY.



You have all of this for only \$49.



The program is only open for enrollment from December 26th-December 31st.



You just have to make one single decision, one year-long commitment, ONE ACT.



And you wouldn't stay a worm anymore.



You just go.



You COMMIT TO SOMETHING FOR ONCE IN YOUR LIFE and you finally become a somebody.



It requires only 1 action.



And I feel like you will, like a worm, continue to do nothing.



And you are literally only 1 action away."\

"



Emotion Prompting:
"This task is vital to my career. By creating these LinkedIn posts, I aim to increase engagement and educate my audience, which is crucial for building brand awareness and attracting new clients."
Chain of Thought Prompting:

Try to imitate and engage the reader by copying the style of the examples
Craft a hook to grab the reader's attention
Write in a Conversational and engaging way
Encourage interaction by asking a question or prompting a discussion

Content Requirements:
1. Length: 5000 characters
2. Structure:
   - Hook/Opening (compelling fact or question)
   - Main Content (3-4 detailed paragraphs)
   - Key Takeaways (2-3 bullet points)
   - Call-to-Action (question or invitation for discussion)

Style Guidelines:
1. Professional yet conversational tone
2. Include specific data points and statistics
3. Cite sources and experts
4. Use strategic line breaks for readability
5. Incorporate industry insights
6. Add business implications
7. Include future predictions
8. DO NOT use markdown formatting (no **, *, etc.)
9. Use plain text only
10. Use line breaks and spacing for emphasis

Context:
News Summary:
{summary}

Content Requirements:
1. Length: MINIMUM 2000 characters, aim for 2500-3000 characters
2. Structure:
   - Compelling opening hook (question or surprising fact)
   - Detailed background (2-3 paragraphs)
   - In-depth analysis (2-3 paragraphs)
   - Industry implications (1-2 paragraphs)
   - Future predictions (1 paragraph)
   - Key takeaways (3-4 bullet points)
   - Strong call-to-action (question for discussion)
3. Content Elements:
   - Include specific data points and statistics
   - Reference industry experts or studies
   - Add real-world examples
   - Discuss business implications
   - Include technical insights
4. Formatting:
   - NO markdown formatting
   - Use line breaks for readability
   - Add 3-5 relevant hashtags at the end
   - Break up text into easily digestible sections

Note: The post MUST be comprehensive and detailed. Short posts will not be accepted.""",

            
            
            'twitter': """
Role: You are an expert Twitter content creator.

Task: Create a concise, informative tweet thread based on the news summaries provided.

Content Requirements:
1. Each tweet must be under 250 characters
2. Create 3-5 tweets that flow together
3. First tweet must hook the reader
4. Last tweet should include a call-to-action
5. Add 2-3 relevant hashtags to the last tweet
6. Plain text only, no markdown
7. Separate tweets with [TWEET] marker

Context:
{summary}
"""
        }

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_for_platform(self, digest: Dict, platform: str) -> Dict:
        """Generate content for a specific platform"""
        try:
            # Get prompt and generate content
            prompt = self._prompts[platform].format(summary=digest['content']['combined_digest'])
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Format content based on platform
            if platform == 'twitter':
                tweets = [t.strip() for t in content.split('[TWEET]') if t.strip()]
                tweets = [t for t in tweets if len(t) <= 250]
                formatted_content = {
                    'tweets': tweets,
                    'is_thread': len(tweets) > 1,
                    'platform': 'twitter'
                }
                content_for_db = json.dumps(tweets)  # Store tweets as JSON string
            else:  # linkedin
                formatted_content = {
                    'text': content,
                    'platform': 'linkedin'
                }
                content_for_db = content

            # Store in database
            try:
                # First, create content source
                source_data = {
                    'url': digest.get('url', ''),
                    'title': digest.get('title', ''),
                    'source_type': 'generated',
                    'category': platform,
                    'content_hash': self._generate_content_hash(content_for_db)
                }
                
                source = self._db.add_content_source(source_data)
                if not source:
                    raise ValueError("Failed to create content source")
                
                # Then, create post history with only valid fields
                post_data = {
                    'platform': platform,
                    'content': content_for_db,
                    'source_id': source.id,
                    'status': 'generated'
                }
                
                post = self._db.create_post(post_data)
                if not post:
                    raise ValueError("Failed to create post history")
                
                logger.info(f"Content stored in database with source ID: {source.id} and post ID: {post.id}")
                
                return {
                    'success': True,
                    'content': formatted_content,
                    'source_id': source.id,
                    'post_id': post.id,
                    'platform': platform
                }
            except Exception as db_error:
                logger.error(f"Database error for {platform}: {str(db_error)}")
                # Return success with content but indicate database error
                return {
                    'success': True,
                    'content': formatted_content,
                    'source_id': None,
                    'post_id': None,
                    'platform': platform,
                    'db_error': str(db_error)
                }
                
        except Exception as e:
            logger.error(f"Error generating content for {platform}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform
            }

    def _run(self, digest: Dict, platform: Union[str, List[str]] = 'twitter') -> Dict:
        """Generate content for one or multiple platforms"""
        try:
            # Validate digest
            if not isinstance(digest, dict):
                raise ValueError("digest must be a dictionary")
            
            content_data = digest.get('content', {})
            if not isinstance(content_data, dict):
                raise ValueError("digest['content'] must be a dictionary")
            
            if 'combined_digest' not in content_data:
                raise ValueError("digest['content'] must contain 'combined_digest' key")

            # Handle platform parameter
            platforms = platform if isinstance(platform, list) else [platform]
            platforms = [p.lower() for p in platforms]
            
            # Validate platforms
            valid_platforms = ['linkedin', 'twitter']
            invalid_platforms = [p for p in platforms if p not in valid_platforms]
            if invalid_platforms:
                raise ValueError(f"Invalid platforms: {invalid_platforms}. Must be one of: {valid_platforms}")

            # Generate content for each platform independently
            results = {}
            for p in platforms:
                try:
                    result = self._generate_for_platform(digest, p)
                    results[p] = result
                except Exception as platform_error:
                    logger.error(f"Error generating content for {p}: {str(platform_error)}")
                    results[p] = {
                        'success': False,
                        'error': str(platform_error),
                        'platform': p
                    }
                    # Continue with next platform even if this one failed
                    continue

            return {
                'success': True,
                'results': results
            }
                
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class HashtagAnalyzer(BaseTool):
    name: str = "Analyze hashtags"
    description: str = "Analyze and suggest hashtags"

    def _run(self, content: str, platform: str = 'twitter',
            max_hashtags: int = 5) -> Dict:
        try:
            prompt = f"""
            Analyze this content and suggest relevant hashtags for {platform}:
            {content}
            
            Requirements:
            - Maximum {max_hashtags} hashtags
            - Relevant to content topic
            - Popular on {platform}
            - Mix of broad and specific tags
            """
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
            )
            
            hashtags = re.findall(r'#\w+', response.choices[0].message.content)
            
            return {
                'success': True,
                'hashtags': hashtags[:max_hashtags],
                'metadata': {
                    'platform': platform,
                    'analyzed_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing hashtags: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class EngagementPredictor(BaseTool):
    name: str = "Predict engagement"
    description: str = "Predict potential engagement for content"

    def _run(self, content: str, platform: str = 'twitter',
            historical_data: Optional[Dict] = None) -> Dict:
        """Predict engagement potential for content"""
        try:
            if not content:
                raise ValueError("Content cannot be empty")

            if isinstance(content, dict):
                if 'content' in content:
                    content = str(content['content'])
                elif 'text' in content:
                    content = content['text']
                else:
                    content = str(content)

            prompt = f"""
            Predict engagement potential for this {platform} content:
            {content}
            
            Consider:
            1. Content quality and relevance
            2. Timing and trends
            3. Target audience
            4. Platform-specific factors
            """
            
            if historical_data and isinstance(historical_data, dict):
                prompt += f"\nHistorical performance data:\n{json.dumps(historical_data)}"
            
            response = completion(
                model="deepseek/deepseek-chat",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=500,
                temperature=0.7
            )
            
            # Parse response to extract predicted metrics
            analysis = response.choices[0].message.content
            
            # Generate mock metrics based on analysis
            engagement_score = 0.75  # Default score
            if 'high engagement' in analysis.lower():
                engagement_score = 0.9
            elif 'low engagement' in analysis.lower():
                engagement_score = 0.4
            
            return {
                'success': True,
                'prediction': {
                    'engagement_score': engagement_score,
                    'analysis': analysis,
                    'factors': [factor.strip() for factor in analysis.split('\n') if factor.strip()],
                    'confidence': 0.8
                },
                'metadata': {
                    'platform': platform,
                    'predicted_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error predicting engagement: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class ContentFilter(BaseTool):
    name: str = "Filter content"
    description: str = "Filter content based on relevance and quality"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.quality_thresholds = {
            'min_length': 100,  # Minimum content length
            'max_length': 5000,  # Maximum content length
            'min_sentiment': 0.0,  # Minimum sentiment score (-1 to 1)
            'min_relevance': 0.6,  # Minimum relevance score (0 to 1)
            'max_duplicate_threshold': 0.85  # Maximum similarity for duplicates
        }

    def _calculate_relevance_score(self, content: str, keywords: List[str]) -> float:
        """Calculate content relevance based on keywords"""
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        word_count = len(content_lower.split())
        
        # Count keyword occurrences
        keyword_counts = sum(content_lower.count(k.lower()) for k in keywords)
        
        # Calculate relevance score
        relevance = keyword_counts / max(1, word_count)
        return min(1.0, relevance * 5)  # Normalize to 0-1

    def _analyze_sentiment(self, content: str) -> Dict:
        """Analyze content sentiment"""
        blob = TextBlob(content)
        return {
            'polarity': blob.sentiment.polarity,  # -1 to 1
            'subjectivity': blob.sentiment.subjectivity,  # 0 to 1
            'is_objective': blob.sentiment.subjectivity < 0.5
        }

    def _check_quality(self, content: str) -> Dict:
        """Check content quality metrics"""
        # Basic text cleanup
        clean_content = re.sub(r'\s+', ' ', content).strip()
        words = clean_content.split()
        
        # Calculate metrics
        metrics = {
            'length': len(clean_content),
            'word_count': len(words),
            'avg_word_length': sum(len(w) for w in words) / max(1, len(words)),
            'sentence_count': len(re.split(r'[.!?]+', clean_content)),
            'has_urls': bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)),
            'has_hashtags': bool(re.search(r'#\w+', content)),
            'reading_time': len(words) / 200  # Average reading speed
        }
        
        return metrics

    def _run(self, content: Dict, filters: Dict) -> Dict:
        """
        Filter content based on quality criteria
        
        Args:
            content: Dictionary containing content to filter
            filters: Dictionary containing filter criteria
        """
        try:
            if not content.get('text'):
                return {
                    'success': False,
                    'error': 'No content provided',
                    'passed_filter': False
                }

            text = content['text']
            keywords = filters.get('keywords', [])
            
            # Calculate quality metrics
            quality_metrics = self._check_quality(text)
            sentiment = self._analyze_sentiment(text)
            relevance = self._calculate_relevance_score(text, keywords)
            
            # Apply filtering criteria
            passes_filter = (
                quality_metrics['length'] >= self.quality_thresholds['min_length'] and
                quality_metrics['length'] <= self.quality_thresholds['max_length'] and
                sentiment['polarity'] >= self.quality_thresholds['min_sentiment'] and
                relevance >= self.quality_thresholds['min_relevance']
            )

            return {
                'success': True,
                'passed_filter': passes_filter,
                'metrics': {
                    'quality': quality_metrics,
                    'sentiment': sentiment,
                    'relevance': relevance
                },
                'content_hash': self._generate_content_hash(text),
                'filtered_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error filtering content: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'passed_filter': False
            }

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()

class ContentTools(BaseTool):
    name: str = "Content Tools"
    description: str = "Tools for managing and analyzing content"
    
    _platform_manager: PlatformManager = PrivateAttr()
    _db_manager: DatabaseManager = PrivateAttr()
    _news_api_key: str = PrivateAttr()
    _banned_terms: List[str] = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._platform_manager = PlatformManager()
        self._db_manager = DatabaseManager()
        self._news_api_key = os.getenv('NEWS_API_KEY')
        self._banned_terms = [
            "revolutionary", "groundbreaking", "disruptive", 
            "game-changing", "paradigm shift", "next-level"
        ]

    def _check_duplicate_content(self, content: str) -> bool:
        """Check if content was already posted"""
        return self._db_manager.is_duplicate_content(content)

    def _validate_content(self, news: Dict[str, str]) -> bool:
        """Validate that the content is consistent and complete"""
        if not all([news.get('title'), news.get('content'), news.get('url')]):
            logger.warning("Missing required content fields")
            return False
        
        # Ensure content is related to title
        title_words = set(news['title'].lower().split())
        content_words = set(news['content'].lower().split())
        common_words = title_words.intersection(content_words)
        
        # If there's too little overlap, content might be mismatched
        if len(common_words) < 2:
            logger.warning("Content might not match title - low word overlap")
            return False
            
        return True

    def _get_competitors(self, company: str) -> str:
        """Get relevant competitors for comparison"""
        competitors = {
            "apple": ["Samsung", "Google", "Microsoft"],
            "microsoft": ["Apple", "Google", "Linux"],
            "google": ["Apple", "Microsoft", "Amazon"],
            "amazon": ["Microsoft", "Google", "Alibaba"],
            "meta": ["Snap", "TikTok", "Twitter"],
            "samsung": ["Apple", "Google", "Xiaomi"],
            "sony": ["Microsoft", "Nintendo", "Apple"],
            "amd": ["Intel", "Nvidia", "Qualcomm"],
            "intel": ["AMD", "Qualcomm", "Apple"],
            "nvidia": ["AMD", "Intel", "Qualcomm"]
        }
        
        for key, values in competitors.items():
            if key.lower() in company.lower():
                return random.choice(values)
        
        return "competitors"

    def _get_tech_category(self, title: str, content: str) -> str:
        """Determine the tech category based on content"""
        combined = (title + " " + content).lower()
        
        categories = {
            "ai": ["ai", "artificial intelligence", "machine learning", "neural", "gpt", "llm"],
            "mobile": ["phone", "smartphone", "android", "ios", "iphone", "pixel"],
            "gaming": ["game", "gaming", "playstation", "xbox", "nintendo", "steam"],
            "hardware": ["processor", "chip", "gpu", "cpu", "hardware", "silicon"],
            "software": ["app", "application", "software", "program", "code", "development"],
            "cloud": ["cloud", "aws", "azure", "server", "data center"],
            "security": ["security", "privacy", "encryption", "hack", "breach"],
            "vr": ["vr", "virtual reality", "ar", "augmented reality", "metaverse"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in combined for keyword in keywords):
                return category
        
        return "technology"

    def _fetch_news_content(self) -> Dict[str, Any]:
        """Fetch tech news content from News API"""
        try:
            # Initialize News API client
            news_api_key = os.getenv('NEWS_API_KEY')
            if not news_api_key:
                logger.error("NEWS_API_KEY not found in environment variables")
                raise ValueError("NEWS_API_KEY not found")
            
            newsapi = NewsApiClient(api_key=news_api_key)
            
            # Get current date and yesterday's date
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Try multiple tech-related queries to find valid content
            tech_queries = [
                'technology', 'tech', 'AI', 'artificial intelligence', 
                'software', 'hardware', 'digital', 'innovation'
            ]
            
            all_articles = []
            
            # Try each query
            for query in tech_queries:
                try:
                    logger.info(f"Searching for news with query: {query}")
                    
                    # Get top headlines for technology
                    # Note: top_headlines doesn't accept date parameters
                    top_headlines = newsapi.get_top_headlines(
                        q=query,
                        category='technology',
                        language='en',
                        page_size=10
                    )
                    
                    # If no results, try everything search
                    if not top_headlines.get('articles'):
                        logger.info(f"No top headlines found for {query}, trying everything search")
                        everything = newsapi.get_everything(
                            q=query,
                            language='en',
                            from_param=yesterday,  # This is correct for get_everything
                            to=today,
                            sort_by='relevancy',
                            page_size=10
                        )
                        all_articles.extend(everything.get('articles', []))
                    else:
                        all_articles.extend(top_headlines.get('articles', []))
                    
                except Exception as e:
                    logger.error(f"Error fetching news for query '{query}': {str(e)}")
                    continue
            
            # Filter and validate articles
            valid_articles = []
            for article in all_articles:
                # Skip articles without required fields
                if not all([
                    article.get('title'), 
                    article.get('description'), 
                    article.get('url'),
                    article.get('source', {}).get('name')
                ]):
                    continue
                    
                # Skip articles with "null" content
                if article.get('description') == '[Removed]' or article.get('description') == 'null':
                    continue
                    
                # Validate URL (simple check)
                if not article.get('url').startswith('http'):
                    continue
                    
                # Check if it's tech-related
                title_and_desc = (article.get('title', '') + ' ' + article.get('description', '')).lower()
                tech_keywords = ['tech', 'technology', 'digital', 'software', 'hardware', 'ai', 'app', 
                                'computer', 'internet', 'cyber', 'data', 'innovation']
                
                if any(keyword in title_and_desc for keyword in tech_keywords):
                    valid_articles.append(article)
            
            if not valid_articles:
                logger.warning("No valid tech news articles found")
                return self._get_fallback_tech_news()
            
            # Select a random article from valid ones
            selected_article = random.choice(valid_articles)
            
            return {
                'title': selected_article['title'],
                'content': selected_article['description'],
                'url': selected_article['url'],
                'source': selected_article['source']['name']
            }
            
        except Exception as e:
            logger.error(f"Error fetching tech news: {str(e)}")
            return self._get_fallback_tech_news()

    def _validate_news_content(self, news: Dict[str, str]) -> bool:
        """Validate that news content is appropriate for posting"""
        # Check for minimum content length
        if len(news['content']) < 50:
            logger.warning("News content too short")
            return False
        
        # Check that title and content are related
        title_words = set(re.findall(r'\w+', news['title'].lower()))
        content_words = set(re.findall(r'\w+', news['content'].lower()))
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'and', 'or'}
        title_words = title_words - common_words
        content_words = content_words - common_words
        
        # Check for word overlap
        if not title_words or not content_words:
            return False
        
        overlap = title_words.intersection(content_words)
        overlap_ratio = len(overlap) / min(len(title_words), len(content_words))
        
        # Allow more flexibility in the overlap requirement
        if overlap_ratio < 0.1:  # Only require 10% overlap
            logger.warning(f"Title and content mismatch. Overlap ratio: {overlap_ratio}")
            return False
        
        # Check that it's tech-related
        return self._is_tech_news(news['title'], news['content'])

    def _generate_hook(self, title: str) -> str:
        """Generate an engaging hook from the title"""
        # Clean title by removing source names
        for suffix in [' - TechCrunch', ' | TechRadar', ' | VentureBeat', ' - 9to5Mac', ' - The Verge']:
            title = title.split(suffix)[0]
            
        return title.strip()

    def _extract_company(self, title: str) -> str:
        """Extract company name from title"""
        # Common tech companies to look for
        tech_companies = {
            "apple": "Apple", "google": "Google", "microsoft": "Microsoft",
            "meta": "Meta", "amazon": "Amazon", "nvidia": "NVIDIA",
            "amd": "AMD", "intel": "Intel", "samsung": "Samsung",
            "sony": "Sony", "tesla": "Tesla", "openai": "OpenAI"
        }
        
        title_lower = title.lower()
        # First try to find known companies
        for company_lower, company_proper in tech_companies.items():
            if company_lower in title_lower:
                return company_proper
            
        # If no known company found, try to extract first proper noun
        words = title.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                return word
            
        return "Tech"

    def _create_hook(self, title: str, category: str) -> str:
        """Create an engaging hook based on title and category"""
        hooks = {
            "ai": [
                "AI just got interesting.",
                "Here's why AI folks are buzzing:",
                "The AI space is heating up."
            ],
            "mobile": [
                "New phone, who dis?",
                "Your next phone might be wild.",
                "Mobile tech is evolving."
            ],
            "gaming": [
                "Gamers, you'll want to see this.",
                "Level up your gaming setup:",
                "Gaming just got better."
            ],
            "hardware": [
                "Tech specs that actually matter:",
                "Hardware nerds, assemble!",
                "Power users, check this out:"
            ],
            "software": [
                "App developers are cooking.",
                "Your apps are about to change.",
                "Software update worth noting:"
            ],
            "cloud": [
                "Cloud tech that matters:",
                "Future of cloud is here:",
                "Cloud computing update:"
            ]
        }
        
        category_hooks = hooks.get(category, ["Interesting tech update:"])
        return random.choice(category_hooks)

    def _simplify_tech_terms(self, description: str) -> str:
        """Simplify technical terms for broader audience"""
        # Common technical terms and their simpler alternatives
        tech_terms = {
            "artificial intelligence": "AI",
            "machine learning": "smart tech",
            "neural network": "AI brain",
            "cryptocurrency": "digital money",
            "blockchain": "digital ledger",
            "quantum computing": "next-gen computing",
            "augmented reality": "AR",
            "virtual reality": "VR"
        }
        
        simplified = description
        for term, simple in tech_terms.items():
            simplified = simplified.replace(term, simple)
        
        # Shorten to one clear sentence
        sentences = simplified.split('.')
        if sentences:
            return sentences[0].strip()
        return simplified

    def _generate_insight(self, description: str) -> str:
        """Generate a personal insight about the news"""
        insights = [
            "This could change how we use tech daily",
            "Interesting move for the industry",
            "The competition is getting fierce",
            "Early days, but promising tech",
            "Smart strategy, if it works",
            "This solves a real problem",
            "Game-changer for power users",
            "Developers will love this"
        ]
        return random.choice(insights)

    def _create_engagement_prompt(self, category: str) -> str:
        """Create category-specific engagement prompt"""
        prompts = {
            "ai": "What's your take on AI development? Too fast, too slow, or just right?",
            "mobile": "What feature would make you upgrade your phone right now?",
            "gaming": "Gamers, is this worth the hype?",
            "hardware": "Performance or price - what matters more to you?",
            "software": "Would you try this? Drop a 👍 or 👎",
            "cloud": "Cloud users, what's your biggest pain point?",
            "security": "How do you balance convenience vs security?",
            "vr": "VR/AR - future of tech or just hype?"
        }
        
        return prompts.get(category, "Thoughts on this? Let's discuss 👇")

    def _format_threads_content(self, title: str, description: str, category: str) -> str:
        """Format content specifically for Threads platform"""
        # Get emojis for the category
        category_emojis = {
            "ai": "🤖",
            "mobile": "📱",
            "gaming": "🎮",
            "hardware": "💻",
            "software": "⚡",
            "cloud": "☁️",
            "security": "🔒",
            "vr": "🥽"
        }
        
        emoji = category_emojis.get(category, "💡")
        
        # Create engaging thread content
        thread_content = f"""{emoji} {title}

{self._create_hook(title, category)}

Key points:
• {self._simplify_tech_terms(description)}
• {self._generate_insight(description)}

{self._create_engagement_prompt(category)}

#Tech #{category}"""

        # Ensure content meets Threads length requirements
        if len(thread_content) > 500:
            thread_content = thread_content[:497] + "..."
        
        return thread_content

    def _format_platform_content(self, content: Dict[str, str], platform: Platform) -> str:
        """Format content specifically for each platform with a more human touch"""
        # Clean title and get core info
        title = content['title'].split(' - ')[0].strip()
        description = content['content']
        
        # Get tech category and company info
        category = self._get_tech_category(title, description)
        company = self._extract_company(title)
        competitor = self._get_competitors(company)
        
        if platform == Platform.THREADS:
            return self._format_threads_content(title, description, category)
        elif platform == Platform.DEVTO:
            return f"""---
title: {title}
published: true
tags: {category}, technology, tech
canonical_url: {content['source_url']}
---

{title}

{description}

I've been following this development, and it's interesting to compare {company}'s approach vs {competitor}'s strategy in this space. While {company} seems to focus on innovation, {competitor} has been emphasizing reliability.

As someone who's worked with both companies' products, I see pros and cons to each approach:

Pros:
- {company}'s solution could improve performance in key areas
- The pricing seems competitive compared to alternatives
- Integration with existing systems looks promising

But there are some concerns:
- New technology often comes with stability issues
- The learning curve might be steep for some users
- Long-term support remains a question mark

What's your take - would you choose cutting-edge features or stick with proven technology?

Read the full story: {content['source_url']}

*Originally published on {content['source_name']}*
"""
        
        elif platform == Platform.MASTODON:
            return f"""{title}

{self._create_hook(title, category)}
{self._simplify_tech_terms(description)}

{self._create_engagement_prompt(category)}

#Tech #{category} #{company}"""[:500]
        
        elif platform == Platform.REDDIT:
            return self._format_reddit_content(title, description, category, company)
        
        return content['content']

    def _format_reddit_content(self, title: str, description: str, category: str, company: str) -> str:
        """Format content for Reddit"""
        # Reddit prefers more conversational, community-oriented content
        formatted_content = f"""# {title}

{description}

## Discussion Points

* What do you think about {company}'s approach to this?
* Has anyone here used similar technology in production?
* How does this compare to alternatives in the market?

---

*I'm sharing this tech news to spark discussion. What are your thoughts?*
"""
        return formatted_content

    def _run(self, query: str) -> Dict[str, Any]:
        """Run content tools operations"""
        try:
            # Check if this is a direct content creation request about database verification
            if "database verification" in query.lower():
                # Create custom database verification content
                content = self._create_database_verification_content()
                
                # For database verification, we'll just return the content without posting
                # This simulates a successful content creation but doesn't actually post
                return {
                    "content": content,
                    "posting_results": {},  # Empty results since we're not posting
                    "status": "success",
                    "message": "Database verification content created but not posted. Only tech news is posted to platforms."
                }
            
            # For tech news, proceed with the normal flow
            try:
                # Fetch news content
                news = self._fetch_news_content()
                
                # Create content data
                content_data = {
                    'title': news['title'],
                    'content': news['content'],
                    'source_url': news['url'],
                    'source_name': news['source']
                }
                
                # Check if this is actually tech news
                if not self._is_tech_news(content_data['title'], content_data['content']):
                    return {
                        "success": False,
                        "error": "Content is not tech news. Only tech news is posted to platforms."
                    }
                
                # Check for duplicates
                if self._check_duplicate_content(content_data['content']):
                    return {
                        "success": False,
                        "error": "Similar content was already posted recently"
                    }

                enabled_platforms = self._platform_manager.check_all_statuses()
                posting_results = {}
                
                for platform, is_enabled in enabled_platforms.items():
                    if is_enabled:
                        kwargs = {}
                        if platform == Platform.DEVTO:
                            kwargs['title'] = content_data['title']
                            category = self._get_tech_category(content_data['title'], content_data['content'])
                            kwargs['tags'] = [category, 'technology', 'tech']
                        elif platform == Platform.REDDIT:
                            kwargs['title'] = content_data['title']
                            kwargs['url'] = content_data['source_url']  # Important for r/technews
                            kwargs['subreddit'] = self._select_best_subreddit(content_data['content'])
                        
                        formatted_content = self._format_platform_content(content_data, platform)
                        result = self._platform_manager.post_to_platform(
                            platform=platform,
                            content=formatted_content,
                            **kwargs
                        )
                        posting_results[platform.value] = result

                # Store successful post in database
                if any(result.get('success', False) for result in posting_results.values()):
                    self._db_manager.store_post(
                        content=content_data['content'],
                        source_url=content_data['source_url']
                    )
                
                return {
                    "content": content_data['content'],
                    "posting_results": posting_results,
                    "status": "success"
                }
            except Exception as e:
                logger.error(f"Error fetching news: {str(e)}")
                # Use fallback tech news instead of database verification content
                fallback_news = self._get_fallback_tech_news()
                
                # Post the fallback news to Reddit
                posting_results = {}
                for platform, is_enabled in self._platform_manager.check_all_statuses().items():
                    if is_enabled and platform == Platform.REDDIT:
                        result = self._platform_manager.post_to_platform(
                            platform=platform,
                            content=fallback_news['content'],
                            title=fallback_news['title'],
                            url=fallback_news['url'],
                            subreddit='technews'
                        )
                        posting_results[platform.value] = result
                
                return {
                    "content": fallback_news['content'],
                    "title": fallback_news['title'],
                    "posting_results": posting_results,
                    "status": "success",
                    "message": "News API failed, using fallback tech news content."
                }
        
        except Exception as e:
            logger.error(f"Error in content tools: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("Async not supported")

    def post_to_reddit(self, content, title=None, url=None):
        """Post content to Reddit with appropriate formatting"""
        try:
            # Get the Reddit platform instance
            reddit_platform = self.platform_manager.platforms.get(Platform.REDDIT)
            if not reddit_platform:
                return {"success": False, "error": "Reddit platform not initialized"}
            
            # Determine the best subreddit based on content
            subreddit = self._select_best_subreddit(content)
            
            # Check if this is a news article
            is_news = self._is_news_content(content)
            
            # For technews, we need a URL and original title
            if subreddit.lower() == 'technews':
                if not url:
                    # Try to extract a URL from the content
                    extracted_url = self._extract_url_from_content(content)
                    if extracted_url:
                        url = extracted_url
                    else:
                        # If no URL, we can't post to technews
                        return {
                            "success": False, 
                            "error": "Cannot post to r/technews without a valid news URL"
                        }
                
                # For technews, use the first line as title if not provided
                if not title:
                    title = content.split('\n')[0][:300]
            else:
                # For other subreddits, format as needed
                if not title:
                    title = content.split('\n')[0][:300]
            
            # Determine post type based on content and subreddit
            post_type = 'link' if url else 'text'
            
            # Post to Reddit
            result = reddit_platform.post_content(
                content=content,
                title=title,
                subreddit=subreddit,
                post_type=post_type,
                url=url,
                original_title=(title if is_news else None)
            )
            
            return result
        except Exception as e:
            logger.error(f"Error posting to Reddit: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def _select_best_subreddit(self, content):
        """Select the most appropriate subreddit based on content"""
        # Get available subreddits
        reddit_platform = self.platform_manager.platforms.get(Platform.REDDIT)
        if not reddit_platform:
            return "test"  # Default to test subreddit
        
        available_subreddits = reddit_platform.default_subreddits
        
        # Simple keyword matching for subreddit selection
        content_lower = content.lower()
        
        # Check for tech news content
        tech_keywords = ['technology', 'tech', 'ai', 'software', 'hardware', 'digital', 'cyber', 'computer']
        news_keywords = ['announced', 'released', 'launched', 'unveiled', 'reported', 'news']
        
        # Count tech and news keywords
        tech_count = sum(1 for keyword in tech_keywords if keyword in content_lower)
        news_count = sum(1 for keyword in news_keywords if keyword in content_lower)
        
        # If content seems like tech news and technews is available
        if tech_count > 0 and news_count > 0 and 'technews' in available_subreddits:
            return 'technews'
        
        # Default to the first available subreddit
        return available_subreddits[0] if available_subreddits else 'test'

    def _is_news_content(self, content):
        """Determine if content is news-like"""
        news_indicators = ['announced', 'released', 'launched', 'unveiled', 'reported']
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in news_indicators)

    def _extract_url_from_content(self, content):
        """Extract a URL from content if present"""
        import re
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, content)
        return urls[0] if urls else None

    def _create_database_verification_content(self) -> str:
        """Create custom content about database verification"""
        return """🚀 **Database Verification Successful!** 🚀

We're thrilled to announce that our database verification process has been completed successfully! 🎉

✅ **Operational Status**: All systems are fully operational and running smoothly.
🌐 **Accessibility**: The database is now accessible to all authorized users without any interruptions.

Thank you for your patience and support as we worked to ensure a seamless experience for everyone. Stay tuned for more updates! 💻✨

#DatabaseSuccess #TechUpdate #OperationalExcellence"""

    def _is_tech_news(self, title: str, content: str) -> bool:
        """Determine if content is tech news"""
        tech_keywords = ['technology', 'tech', 'ai', 'software', 'hardware', 'digital', 
                         'cyber', 'computer', 'app', 'device', 'innovation', 'startup',
                         'algorithm', 'data', 'cloud', 'internet', 'mobile', 'robot']
        
        news_keywords = ['announced', 'released', 'launched', 'unveiled', 'reported', 
                         'news', 'update', 'introduces', 'reveals', 'debuts']
        
        text = (title + " " + content).lower()
        
        # Count tech and news keywords
        tech_count = sum(1 for keyword in tech_keywords if keyword in text)
        news_count = sum(1 for keyword in news_keywords if keyword in text)
        
        # Content must have both tech and news elements
        return tech_count > 0 and news_count > 0 

    def _get_fallback_tech_news(self) -> Dict[str, Any]:
        """Provide fallback tech news when API fails"""
        # List of pre-vetted tech news items
        tech_news_items = [
            {
                'title': 'Microsoft Announces New AI Features for Windows 11',
                'content': 'Microsoft has unveiled a suite of new AI-powered features for Windows 11, including enhanced voice recognition, smart content generation, and improved virtual assistant capabilities.',
                'url': 'https://www.theverge.com/2023/5/23/23733181/microsoft-windows-11-ai-features-build',
                'source': 'The Verge'
            },
            {
                'title': 'Google Introduces Next-Generation AI Model for Search',
                'content': 'Google has announced a new AI model that will power its search engine, promising more accurate and contextually relevant results for complex queries.',
                'url': 'https://blog.google/products/search/search-ai-overviews-updates-2023/',
                'source': 'Google Blog'
            },
            {
                'title': 'Apple Unveils New MacBook Pro with M3 Chip',
                'content': 'Apple has released its latest MacBook Pro featuring the new M3 chip, promising significant performance improvements and better battery life compared to previous models.',
                'url': 'https://www.apple.com/newsroom/2023/10/apple-unveils-new-macbook-pro-featuring-m3-chips/',
                'source': 'Apple Newsroom'
            }
        ]
        
        # Return a random news item
        return random.choice(tech_news_items) 