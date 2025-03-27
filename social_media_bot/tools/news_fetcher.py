import os
import logging
import random
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from newsapi import NewsApiClient

logger = logging.getLogger(__name__)

class MultiNewsApiFetcher:
    """Fetch news from multiple APIs with fallback logic"""
    
    def __init__(self):
        """Initialize the news API fetcher with multiple providers"""
        # Initialize NewsAPI client (primary)
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.has_news_api = bool(self.news_api_key)
        self.newsapi = NewsApiClient(api_key=self.news_api_key) if self.has_news_api else None
        
        # Initialize TheNewsAPI client (secondary)
        self.the_news_api_key = os.getenv('THE_NEWS_API_KEY')
        self.has_the_news_api = bool(self.the_news_api_key) and self.the_news_api_key != "your_the_news_api_key_here"
        self.the_news_api_base_url = "https://api.thenewsapi.com/v1/news"
        
        # Initialize NewsData.io API client (tertiary)
        self.newsdata_api_key = os.getenv('NEWSDATA_API_KEY')
        self.has_newsdata_api = bool(self.newsdata_api_key) and self.newsdata_api_key != "your_newsdata_api_key_here"
        self.newsdata_api_base_url = "https://newsdata.io/api/1/news"
        
        # Tracking for rate limits
        self.newsapi_calls_today = 0
        self.the_news_api_calls_today = 0
        self.newsdata_api_calls_today = 0
        self.MAX_API_CALLS = 90  # Keep a safe margin below the actual limit of 100
        self.MAX_NEWSDATA_CALLS = 190  # NewsData free tier allows 200 calls/day
        
        # Cache for articles
        self.news_cache = {}
        self.last_fetch_time = None
        
        logger.info(f"NewsAPI available: {self.has_news_api}, TheNewsAPI available: {self.has_the_news_api}, NewsData.io available: {self.has_newsdata_api}")
        
    def fetch_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch news articles matching the query
        
        Args:
            query: The search query 
            max_results: Maximum number of results to return
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"Fetching news for query: {query}")
        articles = []
        
        # Try NewsAPI first if available and not rate limited
        if self.has_news_api and self.newsapi_calls_today < self.MAX_API_CALLS:
            try:
                # First try top headlines
                self.newsapi_calls_today += 1
                top_headlines = self.newsapi.get_top_headlines(
                    q=query,
                    category='technology',
                    language='en',
                    page_size=max_results
                )
                
                if top_headlines.get('articles'):
                    articles.extend(top_headlines.get('articles', [])[:max_results])
                    
                # If we don't have enough articles, try everything search
                if len(articles) < max_results:
                    self.newsapi_calls_today += 1
                    everything = self.newsapi.get_everything(
                        q=query,
                        language='en',
                        sort_by='relevancy',
                        page_size=max_results,
                        # Exclude Medium and similar platforms
                        domains='techcrunch.com,wired.com,theverge.com,arstechnica.com,cnet.com,zdnet.com',
                        exclude_domains='medium.com,substack.com,wordpress.com,blogger.com'
                    )
                    remaining = max_results - len(articles)
                    articles.extend(everything.get('articles', [])[:remaining])
                
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from NewsAPI for '{query}'")
                    self._update_cache(articles)
                    return self._filter_articles(articles)[:max_results]
            except Exception as e:
                error_str = str(e)
                logger.error(f"Error fetching from NewsAPI: {error_str}")
                # If not explicitly rate limited, increment counter anyway
                if 'rateLimited' not in error_str:
                    self.newsapi_calls_today += 1  # Count as a call
        
        # If NewsAPI failed or returned no results, try TheNewsAPI
        if (not articles) and self.has_the_news_api and self.the_news_api_calls_today < self.MAX_API_CALLS:
            try:
                # Define the API parameters - add domain filtering
                params = {
                    'api_token': self.the_news_api_key,
                    'language': 'en',
                    'search': query,
                    'categories': 'tech',
                    'limit': max_results,  # Free tier limit is 3 articles per request
                    'domains': 'techcrunch.com,wired.com,theverge.com,arstechnica.com,cnet.com,zdnet.com',
                    'exclude_domains': 'medium.com'
                }
                
                self.the_news_api_calls_today += 1
                response = requests.get(f"{self.the_news_api_base_url}/all", params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get('data'):
                    # Transform TheNewsAPI format to match NewsAPI format for consistency
                    for article in data.get('data', []):
                        transformed_article = {
                            'title': article.get('title'),
                            'description': article.get('description'),
                            'url': article.get('url'),
                            'source': {'name': article.get('source') or "TheNewsAPI"},
                            'publishedAt': article.get('published_at')
                        }
                        articles.append(transformed_article)
                
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from TheNewsAPI for '{query}'")
                    self._update_cache(articles)
                    return self._filter_articles(articles)[:max_results]
            except Exception as e:
                logger.error(f"Error fetching from TheNewsAPI: {str(e)}")
                # If the error isn't explicit about rate limiting, increment counter anyway
                self.the_news_api_calls_today += 1
        
        # If other APIs failed, try NewsData.io
        if (not articles) and self.has_newsdata_api and self.newsdata_api_calls_today < self.MAX_NEWSDATA_CALLS:
            try:
                # NewsData.io parameters
                params = {
                    'apikey': self.newsdata_api_key,
                    'q': query,
                    'language': 'en',
                    'category': 'technology',
                    'size': max_results,
                    'domain': 'techcrunch.com,wired.com,theverge.com,arstechnica.com,cnet.com'
                }
                
                self.newsdata_api_calls_today += 1
                response = requests.get(self.newsdata_api_base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get('status') == 'success' and data.get('results'):
                    # Transform NewsData.io format to match NewsAPI format for consistency
                    for article in data.get('results', []):
                        # Skip articles without required fields
                        if not all([article.get('title'), article.get('description'), article.get('link')]):
                            continue
                            
                        transformed_article = {
                            'title': article.get('title'),
                            'description': article.get('description'),
                            'url': article.get('link'),
                            'source': {'name': article.get('source_id') or "NewsData.io"},
                            'publishedAt': article.get('pubDate')
                        }
                        articles.append(transformed_article)
                
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from NewsData.io for '{query}'")
                    self._update_cache(articles)
                    return self._filter_articles(articles)[:max_results]
            except Exception as e:
                logger.error(f"Error fetching from NewsData.io: {str(e)}")
                self.newsdata_api_calls_today += 1
        
        # If all APIs failed or had no results, try the cache
        if not articles:
            logger.warning(f"No live results for '{query}', checking cache")
            cached_articles = self._get_cached_articles()
            if cached_articles:
                # Filter cache for relevant articles
                relevant = []
                for article in cached_articles:
                    content = (article.get('title', '') + ' ' + article.get('description', '')).lower()
                    if query.lower() in content:
                        relevant.append(article)
                
                if relevant:
                    logger.info(f"Found {len(relevant)} cached articles for '{query}'")
                    return self._filter_articles(relevant)[:max_results]
        
        logger.warning(f"No articles found for '{query}'")
        return []
    
    def get_tech_news(self, use_fallback=True) -> Dict[str, Any]:
        """
        Fetch tech news using available APIs with fallback logic
        
        Args:
            use_fallback: Whether to use fallback options (cache, hardcoded) if APIs fail
            
        Returns:
            Dict containing article info or None if all methods fail
        """
        articles = []
        
        # First try: NewsAPI if available and not rate limited
        if self.has_news_api and self.newsapi_calls_today < self.MAX_API_CALLS:
            try:
                articles = self._fetch_from_newsapi()
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from NewsAPI")
                    self._update_cache(articles)
                    return self._select_random_article(articles)
            except Exception as e:
                error_str = str(e)
                logger.error(f"Error fetching from NewsAPI: {error_str}")
                # If not rate limited, it's another error - increment counter anyway
                if 'rateLimited' not in error_str:
                    self.newsapi_calls_today += 2  # Assume 2 calls were made
        
        # Second try: TheNewsAPI if available and not rate limited
        if not articles and self.has_the_news_api and self.the_news_api_calls_today < self.MAX_API_CALLS:
            try:
                articles = self._fetch_from_the_news_api()
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from TheNewsAPI")
                    self._update_cache(articles)
                    return self._select_random_article(articles)
            except Exception as e:
                logger.error(f"Error fetching from TheNewsAPI: {str(e)}")
                # If the error isn't explicit about rate limiting, increment counter anyway
                self.the_news_api_calls_today += 1
        
        # If both APIs failed or are rate limited, try the cache
        if not articles and use_fallback:
            logger.warning("Both APIs failed or are rate limited")
            cached_article = self._get_cached_article()
            if cached_article:
                logger.info("Using cached article")
                return cached_article
            
            # Last resort: use fallback content
            logger.warning("No cached articles available, using fallback content")
            return self._get_fallback_content()
            
        # If we have articles but didn't return yet, something went wrong
        if articles:
            return self._select_random_article(articles)
            
        # If we get here, everything failed and no fallback was used
        return None
    
    def _fetch_from_newsapi(self) -> List[Dict[str, Any]]:
        """Fetch articles from NewsAPI"""
        all_articles = []
        rate_limited = False
        
        # Get current date and yesterday's date
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Reduced set of queries to minimize API calls
        tech_queries = [
            'technology OR AI OR software OR hardware',  # Combined query 1
        ]
        
        # Only try one query to minimize API usage
        for query in tech_queries:
            if rate_limited:
                break
                
            try:
                logger.info(f"Searching NewsAPI with query: {query}")
                
                # Get top headlines for technology
                try:
                    self.newsapi_calls_today += 1
                    top_headlines = self.newsapi.get_top_headlines(
                        q=query,
                        category='technology',
                        language='en',
                        page_size=10
                    )
                    
                    if top_headlines.get('articles'):
                        all_articles.extend(top_headlines.get('articles', []))
                        # If we have enough articles, don't make more API calls
                        if len(all_articles) >= 5:
                            break
                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error fetching top headlines from NewsAPI: {error_str}")
                    if 'rateLimited' in error_str:
                        rate_limited = True
                        break
                
                # Only do everything search if we don't have enough articles
                if len(all_articles) < 3 and not rate_limited:
                    try:
                        self.newsapi_calls_today += 1
                        everything = self.newsapi.get_everything(
                            q=query,
                            language='en',
                            from_param=yesterday,
                            to=today,
                            sort_by='relevancy',
                            page_size=10
                        )
                        all_articles.extend(everything.get('articles', []))
                    except Exception as e:
                        error_str = str(e)
                        logger.error(f"Error fetching everything search from NewsAPI: {error_str}")
                        if 'rateLimited' in error_str:
                            rate_limited = True
                    
            except Exception as e:
                logger.error(f"Error in NewsAPI query '{query}': {str(e)}")
                continue
        
        # Filter articles for tech relevance and reputable sources
        valid_articles = self._filter_articles(all_articles)
        return valid_articles
    
    def _fetch_from_the_news_api(self) -> List[Dict[str, Any]]:
        """Fetch articles from TheNewsAPI"""
        all_articles = []
        
        # Define the API parameters with domain filtering
        params = {
            'api_token': self.the_news_api_key,
            'language': 'en',
            'categories': 'tech',
            'limit': 3,  # Free tier limit is 3 articles per request
            'domains': 'techcrunch.com,wired.com,theverge.com,arstechnica.com,cnet.com,zdnet.com',
            'exclude_domains': 'medium.com'
        }
        
        try:
            logger.info("Fetching top stories from TheNewsAPI")
            self.the_news_api_calls_today += 1
            
            # Fetch top stories
            response = requests.get(f"{self.the_news_api_base_url}/top", params=params)
            response.raise_for_status()  # Raise exception for non-200 responses
            
            data = response.json()
            if data.get('data'):
                # Transform TheNewsAPI format to match NewsAPI format for consistency
                for article in data.get('data', []):
                    transformed_article = {
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'url': article.get('url'),
                        'source': {'name': article.get('source') or "TheNewsAPI"},
                        'publishedAt': article.get('published_at')
                    }
                    all_articles.append(transformed_article)
                    
            # If we don't have enough articles, try all news endpoint
            if len(all_articles) < 3:
                logger.info("Fetching all news from TheNewsAPI")
                self.the_news_api_calls_today += 1
                
                # Add tech search term - more specific
                params['search'] = 'technology news AI quantum computing security'
                
                response = requests.get(f"{self.the_news_api_base_url}/all", params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get('data'):
                    # Transform and add articles
                    for article in data.get('data', []):
                        transformed_article = {
                            'title': article.get('title'),
                            'description': article.get('description'),
                            'url': article.get('url'),
                            'source': {'name': article.get('source') or "TheNewsAPI"},
                            'publishedAt': article.get('published_at')
                        }
                        all_articles.append(transformed_article)
            
            # Filter articles for tech relevance
            valid_articles = self._filter_articles(all_articles)
            return valid_articles
            
        except Exception as e:
            logger.error(f"Error fetching from TheNewsAPI: {str(e)}")
            if '429' in str(e):  # HTTP 429 Too Many Requests
                logger.warning("TheNewsAPI rate limited")
            return []
    
    def _filter_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter articles for tech relevance and validity"""
        valid_articles = []
        
        # Define reputable tech news sources - only verified professional outlets
        reputable_sources = [
            # Major tech news sites
            'techcrunch.com', 'wired.com', 'theverge.com', 'arstechnica.com', 
            'engadget.com', 'cnet.com', 'zdnet.com', 'venturebeat.com',
            'thenextweb.com', 'gizmodo.com', 'mashable.com', 'techradar.com',
            
            # General news with good tech coverage
            'reuters.com', 'apnews.com', 'bloomberg.com', 'wsj.com', 
            'nytimes.com', 'bbc.com', 'bbc.co.uk', 'cnbc.com', 'forbes.com',
            
            # Additional tech publications
            'techrepublic.com', 'protocol.com', 'fastcompany.com', 'slashdot.org',
            'technologyreview.mit.edu', 'tomshardware.com', 'pcmag.com',
            'ieee.org', 'developer.mozilla.org', 'infoworld.com'
        ]
        
        # Explicitly blocked sources (blogs and low quality content)
        blocked_sources = [
            'medium.com', 'substack.com', 'wordpress.com', 'blogger.com',
            'tumblr.com', 'facebook.com', 'linkedin.com'
        ]
        
        # Count how many articles we're filtering out for logging purposes
        rejected_count = 0
        
        for article in articles:
            # Skip articles without required fields
            if not all([
                article.get('title'), 
                article.get('description'), 
                article.get('url'),
                article.get('source', {}).get('name')
            ]):
                rejected_count += 1
                continue
                
            # Skip articles with "null" content
            if article.get('description') == '[Removed]' or article.get('description') == 'null':
                rejected_count += 1
                continue
                
            # Validate URL (simple check)
            url = article.get('url', '')
            if not url.startswith('http'):
                rejected_count += 1
                continue
                
            # Check if URL is from a blocked source
            if any(blocked in url for blocked in blocked_sources):
                logger.info(f"Skipping blocked source: {url}")
                rejected_count += 1
                continue
            
            # Check if we're using TheNewsAPI, which already provides filtered content
            using_the_news_api = not (self.has_news_api and self.newsapi_calls_today < self.MAX_API_CALLS)
            
            # Always check for reputable sources
            is_reputable = False
            
            # First check if it's in our explicitly reputable list
            for source in reputable_sources:
                if source in url:
                    is_reputable = True
                    break
                    
            # If using TheNewsAPI but not reputable, do additional checks
            if not is_reputable:
                if using_the_news_api:
                    # For TheNewsAPI, check if the article is substantive and not just a blog post
                    
                    # Check for minimum content length
                    if len(article.get('description', '')) < 100:
                        logger.info(f"Skipping article with short description: {url}")
                        rejected_count += 1
                        continue
                    
                    # Check source name for known publishers
                    source_name = article.get('source', {}).get('name', '').lower()
                    major_publishers = ['bbc', 'cnn', 'nbc', 'cbs', 'abc', 'nyt', 'reuters', 'ap', 
                                      'washington post', 'guardian', 'time', 'scientific', 'ieee']
                    
                    if any(pub in source_name for pub in major_publishers):
                        is_reputable = True
                    else:
                        # If not from a recognized publisher, reject
                        logger.info(f"Skipping non-reputable source: {url}")
                        rejected_count += 1
                        continue
                else:
                    # For NewsAPI, maintain strict source validation
                    logger.info(f"Skipping non-reputable source: {url}")
                    rejected_count += 1
                    continue
                
            # Check if it's tech-related
            title_and_desc = (article.get('title', '') + ' ' + article.get('description', '')).lower()
            tech_keywords = ['tech', 'technology', 'digital', 'software', 'hardware', 'ai', 'app', 
                            'computer', 'internet', 'cyber', 'data', 'innovation', 'robot',
                            'quantum', 'virtual', 'augmented', 'blockchain', 'cloud', 'security']
            
            if any(keyword in title_and_desc for keyword in tech_keywords):
                valid_articles.append(article)
            else:
                rejected_count += 1
        
        # Log the filtering results
        if rejected_count > 0:
            logger.info(f"Filtered out {rejected_count} articles, kept {len(valid_articles)}")
            
        return valid_articles
    
    def _update_cache(self, articles: List[Dict[str, Any]]) -> None:
        """Update the cache with new articles"""
        if articles:
            self.news_cache = {'articles': articles}
            self.last_fetch_time = datetime.now()
    
    def _get_cached_articles(self) -> List[Dict[str, Any]]:
        """Get all cached articles if available and not too old"""
        if not self.news_cache or not self.news_cache.get('articles'):
            return []
            
        # Cache valid for 6 hours
        if self.last_fetch_time and (datetime.now() - self.last_fetch_time).total_seconds() < 21600:
            logger.info("Using cached news articles")
            return self.news_cache.get('articles', [])
                
        return []
    
    def _get_cached_article(self) -> Optional[Dict[str, Any]]:
        """Get an article from cache if available and not too old"""
        if not self.news_cache or not self.news_cache.get('articles'):
            return None
            
        # Cache valid for 6 hours
        if self.last_fetch_time and (datetime.now() - self.last_fetch_time).total_seconds() < 21600:
            logger.info("Using cached news articles")
            # Select a random article from the cache
            return self._select_random_article(self.news_cache.get('articles', []))
                
        return None
    
    def _select_random_article(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select a random article from the list and format it"""
        if not articles:
            return None
            
        selected_article = random.choice(articles)
        
        # Log the source for verification
        logger.info(f"Selected article from source: {selected_article['source']['name']} ({selected_article['url']})")
        
        # Format to standard content format
        return {
            'title': selected_article['title'],
            'content': selected_article['description'],
            'url': selected_article['url'],
            'source': selected_article['source']['name'],
            'published_at': selected_article.get('publishedAt')
        }
    
    def _get_fallback_content(self) -> Dict[str, Any]:
        """Return fallback content when APIs fail and cache is empty"""
        # Instead of hardcoded content, log an error and return None
        logger.error("No news available from APIs or cache")
        return None 