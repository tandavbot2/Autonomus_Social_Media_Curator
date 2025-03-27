import os
import logging
import random
import json
import time
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from ..platforms.manager import PlatformManager
from ..models.platform import Platform
from ..database.db_manager import DatabaseManager
from .content_tools import ContentTools
from .news_fetcher import MultiNewsApiFetcher
from ..services.deepseek_service import DeepSeekService
from ..services.article_extractor import ArticleExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentStrategyBase:
    """Base class for content strategies"""
    
    def __init__(self, platform_manager, db_manager):
        """Initialize the strategy"""
        self.platform_manager = platform_manager
        self.db_manager = db_manager
        self.content_tools = ContentTools()
        
    def fetch_content(self) -> Dict[str, Any]:
        """Fetch content for the strategy"""
        raise NotImplementedError("Subclasses must implement fetch_content")
        
    def validate_content(self, content: Dict[str, Any]) -> bool:
        """Validate content for the strategy"""
        raise NotImplementedError("Subclasses must implement validate_content")
        
    def format_for_platform(self, content: Dict[str, Any], platform: Platform) -> Dict[str, Any]:
        """Format content for a specific platform"""
        raise NotImplementedError("Subclasses must implement format_for_platform")
        
    def post_to_platforms(self, formatted_content, platforms, is_test=False):
        """Post the content to the specified platforms"""
        if not platforms:
            logger.warning("No platforms specified for posting")
            return {}

        results = {}
        for platform in platforms:
            # Handle both Platform enum objects and string platform identifiers
            platform_name = platform.value if hasattr(platform, 'value') else platform
            platform_key = platform if hasattr(platform, 'value') else None
            
            # Try to get the platform enum from the string if we only have a string
            if not platform_key:
                try:
                    platform_key = Platform(platform_name)
                except ValueError:
                    logger.error(f"Unknown platform: {platform_name}")
                    results[platform] = {"success": False, "error": f"Unknown platform: {platform_name}"}
                    continue
            
            if platform_key not in self.platform_posting_clients:
                logger.warning(f"No client configured for {platform_name}")
                results[platform] = {"success": False, "error": "Platform not configured"}
                continue

            # Set platform-specific duplicate check timeframes
            if platform_name.lower() == 'reddit':
                # Reddit has a 90-day repost policy
                duplicate_check_hours = 24 * 90  # 90 days
            elif platform_name.lower() == 'devto':
                # For Dev.to, check past 30 days
                duplicate_check_hours = 24 * 30  # 30 days
            else:
                # Default for other platforms - 24 hours
                duplicate_check_hours = 24

            # Check for duplicate posts on this platform with platform-specific timeframe
            title = formatted_content.get('title', '')
            url = formatted_content.get('url', '')
            post_content = formatted_content.get('content', '')

            logger.info(f"Checking for duplicates on {platform_name} over past {duplicate_check_hours} hours")
            is_duplicate = self.db_manager.is_duplicate_post_on_platform(
                platform=platform_name,
                content=post_content,
                title=title,
                url=url,
                hours=duplicate_check_hours
            )

            if is_duplicate:
                logger.warning(f"Duplicate content detected for {platform_name}, skipping")
                results[platform] = {"success": False, "error": "Duplicate content detected"}
                continue

            # Get the client for this platform
            client = self.platform_posting_clients[platform_key]

            try:
                # For test mode, just log instead of posting
                if is_test:
                    logger.info(f"TEST MODE: Would post to {platform_name}: {title}")
                    post_id = f"test-{platform_name}-{int(time.time())}"
                    post_url = f"https://test.example.com/{post_id}"
                    results[platform] = {"success": True, "post_id": post_id, "post_url": post_url}
                    
                    # Store the post in test mode
                    self.db_manager.save_platform_post(
                        post_id=str(uuid.uuid4()),
                        platform=platform_name,
                        title=title,
                        content=post_content,
                        post_url=post_url,
                        platform_post_id=post_id,
                        status="test",
                        metadata=json.dumps(formatted_content)
                    )
                    continue
                
                # Post to the platform
                logger.info(f"Posting to {platform_name}: {title}")
                post_result = client.post_content(formatted_content)
                
                if post_result and post_result.get("success"):
                    post_id = post_result.get("post_id")
                    post_url = post_result.get("post_url")
                    
                    # Store the successful post in the database for tracking
                    self.db_manager.save_platform_post(
                        post_id=str(uuid.uuid4()),
                        platform=platform_name,
                        title=title,
                        content=post_content,
                        post_url=post_url,
                        platform_post_id=post_id,
                        status="posted",
                        metadata=json.dumps(formatted_content)
                    )
                    
                    results[platform] = post_result
                    logger.info(f"Successfully posted to {platform_name}: {post_url}")
                else:
                    error = post_result.get("error", "Unknown error") if post_result else "No result returned"
                    logger.error(f"Failed to post to {platform_name}: {error}")
                    results[platform] = {"success": False, "error": error}
                    
                    # Store the failed post attempt
                    self.db_manager.save_platform_post(
                        post_id=str(uuid.uuid4()),
                        platform=platform_name,
                        title=title,
                        content=post_content,
                        post_url=None,
                        platform_post_id=None,
                        status="failed",
                        metadata=json.dumps({"error": error, "content": formatted_content})
                    )
                    
            except Exception as e:
                logger.exception(f"Error posting to {platform_name}: {str(e)}")
                results[platform] = {"success": False, "error": str(e)}
                
                # Store the error
                self.db_manager.save_platform_post(
                    post_id=str(uuid.uuid4()),
                    platform=platform_name,
                    title=title,
                    content=post_content,
                    post_url=None,
                    platform_post_id=None,
                    status="error",
                    metadata=json.dumps({"error": str(e), "content": formatted_content})
                )

        return results

class TechNewsStrategy(ContentStrategyBase):
    """Strategy for tech news content"""
    
    def __init__(self, db_manager, platform_manager, config, api_key=None):
        # Match parameter order in ContentStrategyBase __init__
        super().__init__(platform_manager, db_manager)
        self.api_key = api_key or os.environ.get('NEWS_API_KEY')
        self.news_api = NewsApiClient(api_key=self.api_key)
        self.config = config
        self.tech_topics = [
            'ai', 'artificial intelligence', 'machine learning',
            'quantum computing', 'technology', 'cyber security',
            'robotics', 'blockchain', 'cryptocurrency',
            'virtual reality', 'augmented reality', 'programming',
            'software development', '5g', 'cloud computing'
        ]
        
        # Initialize DeepSeek service for blog content processing
        self.deepseek_service = DeepSeekService()
        
        # Initialize platform posting clients
        self.platform_posting_clients = {}
        if platform_manager and hasattr(platform_manager, 'platforms'):
            # Use the platforms dictionary from platform_manager
            for platform, client in platform_manager.platforms.items():
                if client:
                    self.platform_posting_clients[platform] = client
                    logger.debug(f"Added client for platform: {platform.value}")

        # Initialize article extractor
        self.article_extractor = ArticleExtractor()
        
        if not self.api_key:
            logger.warning("No News API key provided, tech news features will be limited")
        
    def fetch_content(self) -> Optional[Dict[str, Any]]:
        """Fetch tech news content from NewsAPI"""
        if not self.api_key:
            logger.error("News API key is required for fetching tech news")
            return None
            
        logger.info("Fetching tech news from NewsAPI")
        
        try:
            # Topics to search for tech news
            topics = ['ai', 'technology', 'programming', 'cybersecurity']
            articles = []
            
            # Query each topic
            for topic in topics:
                logger.info(f"Querying NewsAPI for topic: {topic}")
                response = self.news_api.get_everything(
                    q=topic,
                    language='en',
                    sort_by='publishedAt',
                    page_size=2  # Get a few per topic
                )
                
                if response and response.get('articles'):
                    logger.info(f"Found {len(response['articles'])} articles for topic: {topic}")
                    articles.extend(response['articles'])
                else:
                    logger.warning(f"No articles found for topic: {topic}")
                    
            if not articles:
                logger.error("No tech news articles found")
                return None
                
            logger.info(f"Total articles fetched: {len(articles)}")
            
            # Filter out articles without required fields
            valid_articles = []
            for article in articles:
                if not article.get('title') or not article.get('url'):
                    continue
                    
                # Skip articles without source or author
                if not article.get('source') and not article.get('author'):
                    logger.debug(f"Skipping article missing source or author: {article.get('title')}")
                    continue
                    
                valid_articles.append(article)
                
            if not valid_articles:
                logger.error("No valid articles found")
                return None
                
            logger.info(f"Retrieved {len(valid_articles)} tech news articles, checking for duplicates")
            
            # Try to find an article that hasn't been posted before
            for article in valid_articles:
                title = article.get('title', '')
                url = article.get('url', '')
                
                # Skip if this content has been posted to any platform in the last 90 days
                if self.db_manager.is_duplicate_content(url, hours=24*90):
                    logger.info(f"Skipping duplicate article: {title}")
                    continue
                    
                # Extract full article content
                enhanced_article = self.article_extractor.extract_article_from_news_item(article)
                
                # Validate this is tech news
                if self.validate_content(enhanced_article):
                    logger.info(f"Using article: {title}")
                    return enhanced_article
                    
            logger.warning("All fetched articles were duplicates or not valid tech news")
            return None
                
        except Exception as e:
            logger.exception(f"Error fetching tech news content: {str(e)}")
            return None

    def generate_content(self) -> List[Dict[str, Any]]:
        """Generate tech news content"""
        logger.info("Generating tech news content")
        
        # Get technology news
        results = []
        articles = []
        
        # Prioritize topics that are more likely to have quality content
        priority_topics = [
            'artificial intelligence',
            'machine learning', 
            'technology',
            'ai',
            'cybersecurity',
            'quantum computing'
        ]
        
        # Add other topics as fallbacks
        fallback_topics = [
            'blockchain',
            'robotics',
            'augmented reality',
            'cloud computing',
            'software development'
        ]
        
        # Try priority topics first
        for topic in priority_topics:
            try:
                logger.info(f"Fetching priority topic: {topic}")
                topic_articles = self.news_api_fetcher.fetch_news(topic, max_results=3)
                if topic_articles:
                    articles.extend(topic_articles)
                    if len(articles) >= 3:
                        logger.info(f"Got enough articles from priority topics")
                        break
            except Exception as e:
                logger.error(f"Error fetching {topic} news: {str(e)}")
        
        # If we didn't get enough from priority topics, try fallbacks
        if len(articles) < 3:
            # Shuffle fallback topics to avoid always using the same ones
            random_fallbacks = random.sample(fallback_topics, min(3, len(fallback_topics)))
            for topic in random_fallbacks:
                try:
                    logger.info(f"Fetching fallback topic: {topic}")
                    topic_articles = self.news_api_fetcher.fetch_news(topic, max_results=2)
                    if topic_articles:
                        articles.extend(topic_articles)
                        if len(articles) >= 3:
                            logger.info(f"Got enough articles with fallback topics")
                            break
                except Exception as e:
                    logger.error(f"Error fetching {topic} news: {str(e)}")
        
        # Log the number of articles we found
        logger.info(f"Found {len(articles)} articles before filtering for duplicates")
        
        # Process articles - keeping track of seen URLs to avoid duplicates
        seen_urls = set()
        for article in articles:
            try:
                url = article.get('url', '')
                
                # Skip if we've seen this URL already
                if url in seen_urls:
                    logger.info(f"Skipping duplicate URL in fetched results: {url}")
                    continue
                
                seen_urls.add(url)
                
                # Check if this article URL has been posted before
                if self.db_manager.is_duplicate_content(url):
                    logger.info(f"Skipping previously posted article: {article.get('title')}")
                    continue
                
                # Add to results
                results.append({
                    'title': article.get('title', ''),
                    'content': article.get('description', ''),
                    'url': url,
                    'source': article.get('source', {}).get('name', 'News Source'),
                    'published_at': article.get('publishedAt', ''),
                    'type': 'tech_news'
                })
                
                # Only need 3 articles max per run
                if len(results) >= 3:
                    break
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
        
        # Check if we have any content
        if not results:
            logger.warning("No tech news content generated")
        else:
            logger.info(f"Generated {len(results)} articles for posting")
        
        return results

    def validate_content(self, content: Dict[str, Any]) -> bool:
        """Validate if content is relevant to tech news"""
        if not content:
            logger.warning("No content to validate")
            return False
            
        title = content.get('title', '').lower()
        description = content.get('description', '').lower()
        
        # Combined text for analysis
        full_text = f"{title} {description}"
        
        # Tech-specific keywords that strongly indicate tech news
        tech_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'software', 'hardware',
            'programming', 'developer', 'cybersecurity', 'data', 'algorithm', 'blockchain',
            'crypto', 'technology', 'app', 'application', 'smartphone', 'device', 'robot',
            'quantum', 'code', 'developer', 'computer', 'tech', 'digital', 'autonomous',
            'cloud', 'server', 'network', 'startup', 'innovation', 'iot', 'automation'
        ]
        
        # Non-tech topics to exclude
        non_tech_topics = [
            'therapy', 'wellness', 'mindfulness', 'health', 'fitness', 'nutrition', 
            'diet', 'workout', 'medicine', 'recipe', 'food', 'cooking', 'sport',
            'fashion', 'beauty', 'celebrity', 'gossip', 'astrology', 'horoscope'
        ]
        
        # Check if content contains tech keywords
        has_tech_keyword = any(keyword in full_text for keyword in tech_keywords)
        
        # Check if content contains non-tech topics that should be excluded
        has_non_tech_topic = any(topic in full_text for topic in non_tech_topics)
        
        # Reject content that has non-tech topics even if it has some tech keywords
        if has_non_tech_topic:
            logger.info(f"Content rejected - contains non-tech topic: {title}")
            return False
            
        # Only accept content with clear tech focus
        if has_tech_keyword:
            logger.info(f"Content validated as tech news: {title}")
            return True
            
        logger.info(f"Content rejected - not tech related: {title}")
        return False

    def format_for_platform(self, content: Dict[str, Any], platform: Platform) -> Dict[str, Any]:
        """Format tech news content for specific platform"""
        if not content:
            logger.warning(f"No content to format for {platform.value}")
            return None
            
        # Get base content fields
        title = content.get('title', '')
        url = content.get('url', '')
        source = content.get('source')
        source_name = source.get('name', 'Unknown Source') if isinstance(source, dict) else source
        description = content.get('description', '')
        article_content = content.get('content', '')
        
        # For Dev.to, create a full blog post using DeepSeek
        if platform == Platform.DEVTO:
            return self._format_for_devto(content)
            
        # For Reddit, prepare a link post
        elif platform == Platform.REDDIT:
            return self._format_for_reddit(content)
            
        # For Mastodon, create a concise summary with source link
        elif platform == Platform.MASTODON:
            return self._format_for_mastodon(content)
            
        # For other platforms (default format)
        else:
            return {
                'title': title,
                'content': f"{description}\n\nRead more: {url}",
                'url': url,
                'source': source_name
            }
    
    def _format_for_devto(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format tech news specifically for Dev.to as a blog post.
        Uses DeepSeek API to transform the content into a proper blog post.
        """
        logger.info("Formatting content for Dev.to blog post")
        
        # Extract content fields
        title = content.get('title', '')
        url = content.get('url', '')
        description = content.get('description', '')
        article_content = content.get('content', '')
        source = content.get('source', {}).get('name', 'the source') if isinstance(content.get('source'), dict) else content.get('source', 'the source')
        
        # Skip empty content
        if not (title and (description or article_content)):
            logger.error("Missing required content for Dev.to post")
            return None
            
        # Get the full text content - clean up the truncation indicators like [+chars]
        text_content = article_content if article_content else description
        text_content = re.sub(r'\[\+\d+ chars\]', '...', text_content)
        
        # Generate tags based on content
        all_text = (title + " " + text_content).lower()
        tags = ["technology"]
        
        # Add more specific tags based on content
        if any(kw in all_text for kw in ['ai', 'artificial intelligence', 'machine learning']):
            tags.append('ai')
        if any(kw in all_text for kw in ['security', 'cyber', 'vulnerability', 'hack']):
            tags.append('security')
        if any(kw in all_text for kw in ['web', 'javascript', 'frontend', 'css', 'html']):
            tags.append('webdev')
        if any(kw in all_text for kw in ['cloud', 'aws', 'azure', 'devops']):
            tags.append('cloud')
        if any(kw in all_text for kw in ['mobile', 'android', 'ios', 'app']):
            tags.append('mobile')
        if any(kw in all_text for kw in ['programming', 'code', 'developer']):
            tags.append('programming')
            
        # Limit to 4 tags (Dev.to recommendation)
        tags = tags[:4]
            
        try:
            # Try to use DeepSeek API if available
            if hasattr(self, 'deepseek_service') and self.deepseek_service and self.deepseek_service.api_key:
                logger.info("Attempting to process with DeepSeek")
                processed_blog = self.deepseek_service.process_news_to_blog(content)
                
                if processed_blog and processed_blog.get('processed_content'):
                    blog_content = processed_blog.get('processed_content')
                    logger.info(f"Successfully processed with DeepSeek, content length: {len(blog_content)}")
                    
                    # Format for Dev.to API
                    return {
                        'title': title,
                        'body_markdown': blog_content,
                        'tags': tags,
                        'published': True,
                        'canonical_url': url
                    }
                else:
                    logger.warning("DeepSeek returned empty content, using fallback")
            else:
                logger.warning("DeepSeek service not available, using fallback")
                
        except Exception as e:
            logger.exception(f"Error using DeepSeek for blog content: {str(e)}")
        
        # Create fallback blog content that doesn't appear AI-generated
        body = f"""
# {title.replace("'", "'")}

![Tech News Image](https://source.unsplash.com/random/800x400/?{'+'.join(tags)})

{text_content.strip()}

## The Technical Perspective

This development is particularly interesting when we consider its implications for the tech industry. As developers and tech professionals, we often encounter similar challenges when building systems that need to integrate with these kinds of solutions.

Some key technical points to consider:
- How this technology integrates with existing systems
- Scalability considerations for similar implementations 
- Potential security implications for related technologies

## Practical Applications

I can think of several practical applications that emerge from this news:

1. **Integration possibilities** with current development workflows
2. **Enhanced tooling** for technical teams working on related technologies
3. **New approaches** to solving common technical challenges

## Code Example

Here's a simplified example of how this might be implemented:

```python
def implement_new_tech(existing_system, new_capability):
    # First, analyze compatibility
    compatibility = check_compatibility(existing_system, new_capability)
    
    if compatibility > 0.8:
        # High compatibility - direct integration
        return existing_system.integrate(new_capability)
    elif compatibility > 0.5:
        # Medium compatibility - adapter pattern
        adapter = TechAdapter(new_capability)
        return existing_system.add_extension(adapter)
    else:
        # Low compatibility - separate system with API
        new_system = NewSystem(new_capability)
        return existing_system.connect_api(new_system.api)
```

## My Analysis

Having worked with similar technologies, I find that the most valuable aspect is how it can streamline common development workflows while maintaining security and scalability. The balance between innovation and practical implementation is what makes this particularly noteworthy.

What's your experience with similar tech? Have you implemented comparable solutions in your work? I'd love to hear your perspective in the comments.

---

*Source: [{source}]({url})*
"""
        
        # Log the created content
        logger.debug(f"Created fallback blog post body (length: {len(body)})")
        
        return {
            'title': title,
            'body_markdown': body,
            'tags': tags,
            'published': True,
            'canonical_url': url
        }
    
    def _format_for_reddit(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format tech news for Reddit
        
        Args:
            content: Dictionary containing news content
            
        Returns:
            Dictionary with formatted content for Reddit
        """
        logger.info("Formatting content for Reddit")
        
        title = content.get('title', '')
        url = content.get('url', '')
        subreddit = self.config.get('reddit_subreddit', 'technology')
        
        # Result dictionary
        result = {
            'title': title,
            'url': url,
            'post_type': 'link',
            'subreddit': subreddit
        }
        
        # Add flair information for specific subreddits
        if subreddit.lower() == 'technology':
            # r/technology requires flair - let's determine the appropriate flair 
            # based on content categorization
            
            # Get potential categories from tags if available
            tags = content.get('tags', [])
            categories = []
            if tags:
                for tag in tags:
                    if isinstance(tag, str):
                        categories.append(tag.lower())
            
            # Try to map our content categories to r/technology flairs
            flair_text = None
            
            # Common r/technology flairs: AIs, Social, Business, Security, IoT, 
            # Computing, Innovation, Software, Mobile, Nanotech, etc.
            if any(cat in ['ai', 'artificial intelligence', 'machine learning'] for cat in categories):
                flair_text = 'AIs'
            elif any(cat in ['security', 'cybersecurity', 'privacy'] for cat in categories):
                flair_text = 'Security'
            elif any(cat in ['mobile', 'smartphone', 'ios', 'android'] for cat in categories):
                flair_text = 'Mobile'
            elif any(cat in ['programming', 'development', 'code'] for cat in categories):
                flair_text = 'Software'
            elif any(cat in ['cloud', 'server', 'hardware'] for cat in categories):
                flair_text = 'Computing'
            elif any(cat in ['business', 'startup', 'industry'] for cat in categories):
                flair_text = 'Business'
            else:
                # Default flair if we can't determine a category
                flair_text = 'Innovation'
            
            logger.info(f"Selected flair for r/technology: {flair_text}")
            result['flair_text'] = flair_text
        
        return result
    
    def _format_for_mastodon(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format tech news specifically for Mastodon as a concise summary with source link.
        Takes into account Mastodon's character limit (typically 500 characters).
        """
        logger.info("Formatting content for Mastodon")
        
        # Extract content fields
        title = content.get('title', '')
        url = content.get('url', '')
        description = content.get('description', '')
        article_content = content.get('content', '')
        full_content = content.get('fullContent', '')  # From article extractor
        source = content.get('source', {}).get('name', 'the source') if isinstance(content.get('source'), dict) else content.get('source', 'the source')
        
        # Character limits
        MAX_TOOT_LENGTH = 490  # Leave some room for the source link
        MAX_TITLE_LENGTH = 100
        MAX_SUMMARY_LENGTH = MAX_TOOT_LENGTH - MAX_TITLE_LENGTH - 30  # Allow for formatting and URL
        
        # Truncate title if needed
        if len(title) > MAX_TITLE_LENGTH:
            title = title[:MAX_TITLE_LENGTH - 3] + "..."
            
        # Get best content for summary (prefer full extracted content)
        summary_text = ""
        
        try:
            # Try to use DeepSeek for a concise, platform-optimized summary
            if hasattr(self, 'deepseek_service') and self.deepseek_service and self.deepseek_service.api_key:
                logger.info("Generating concise Mastodon summary with DeepSeek")
                
                summary_data = self.deepseek_service.generate_platform_summary(
                    content=content,
                    platform="mastodon", 
                    max_length=MAX_SUMMARY_LENGTH
                )
                
                if summary_data and summary_data.get('summary'):
                    summary_text = summary_data.get('summary')
                    logger.info(f"Generated DeepSeek summary for Mastodon (length: {len(summary_text)})")
        except Exception as e:
            logger.exception(f"Error generating Mastodon summary with DeepSeek: {str(e)}")
            
        # Fallback to manual summary if DeepSeek failed
        if not summary_text:
            logger.info("Using manual summary generation for Mastodon")
            
            # Use the best available content
            if full_content:
                raw_text = full_content
            elif article_content:
                raw_text = article_content
            else:
                raw_text = description
                
            # Clean up text (remove newlines, extra spaces)
            raw_text = re.sub(r'\s+', ' ', raw_text).strip()
            
            # Extract first paragraph or sentence
            first_para = re.split(r'(?<=[.!?])\s+', raw_text)
            summary_text = first_para[0] if first_para else raw_text
            
            # Truncate if needed
            if len(summary_text) > MAX_SUMMARY_LENGTH:
                summary_text = summary_text[:MAX_SUMMARY_LENGTH - 3] + "..."
        
        # Build the toot content
        toot_content = f"{title}\n\n{summary_text}\n\n{url}"
        
        # Ensure we're within limits
        if len(toot_content) > MAX_TOOT_LENGTH:
            # Further truncate summary if needed
            overflow = len(toot_content) - MAX_TOOT_LENGTH
            summary_text = summary_text[:len(summary_text) - overflow - 3] + "..."
            toot_content = f"{title}\n\n{summary_text}\n\n{url}"
        
        logger.debug(f"Created Mastodon post (length: {len(toot_content)})")
        
        # Hashtags improve visibility on Mastodon
        # Extract keywords from article or generate from title
        keywords = content.get('keywords', [])
        if not keywords:
            # Extract potential hashtags from title
            words = re.findall(r'\b[A-Za-z][A-Za-z0-9]+\b', title)
            common_tech_terms = ['ai', 'tech', 'crypto', 'blockchain', 'data', 'software', 'web', 'cloud']
            keywords = [word.lower() for word in words if word.lower() in common_tech_terms]
        
        # Limit to 2-3 most relevant hashtags
        hashtags = []
        for keyword in keywords[:3]:
            hashtag = f"#{keyword.replace(' ', '')}"
            # Only add if it doesn't push us over the limit
            if len(toot_content) + len(hashtag) + 1 <= MAX_TOOT_LENGTH:
                hashtags.append(hashtag)
        
        # Add hashtags if we have room
        if hashtags:
            toot_content = f"{toot_content}\n\n{' '.join(hashtags)}"
            
        return {
            'content': toot_content,
            'visibility': 'public',
            'sensitive': False
        }

# Add more strategies here as needed (e.g., DatabaseVerificationStrategy, etc.) 