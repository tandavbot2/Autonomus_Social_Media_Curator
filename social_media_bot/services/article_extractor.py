import logging
import requests
import newspaper
from newspaper import Article, ArticleException
from typing import Dict, Any, Optional
import nltk
import os

# Initialize logger
logger = logging.getLogger(__name__)

class ArticleExtractor:
    """
    Service for extracting the full content of news articles from their URLs
    using the newspaper3k library
    """
    
    def __init__(self):
        """Initialize the article extractor service"""
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        # Download required NLTK data if not already available
        self._download_nltk_data()
        
        logger.info("Article extractor service initialized")
    
    def _download_nltk_data(self):
        """Download required NLTK data for article processing"""
        nltk_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'nltk_data')
        os.makedirs(nltk_data_dir, exist_ok=True)
        
        nltk.data.path.append(nltk_data_dir)
        
        # Check if required data is already downloaded
        try:
            nltk.data.find('tokenizers/punkt')
            logger.info("NLTK punkt tokenizer already downloaded")
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer data")
            nltk.download('punkt', download_dir=nltk_data_dir)
            
        try:
            nltk.data.find('tokenizers/punkt_tab/english')
            logger.info("NLTK punkt_tab already downloaded")
        except LookupError:
            try:
                logger.info("Downloading NLTK punkt_tab data")
                nltk.download('punkt_tab', download_dir=nltk_data_dir)
            except:
                logger.warning("Could not download punkt_tab, NLP processing may be limited")
        
        # Download stopwords if needed for better keyword extraction
        try:
            nltk.data.find('corpora/stopwords')
            logger.info("NLTK stopwords already downloaded")
        except LookupError:
            logger.info("Downloading NLTK stopwords data")
            nltk.download('stopwords', download_dir=nltk_data_dir)
    
    def extract_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract the full content of an article from its URL
        
        Args:
            url: The URL of the article to extract
            
        Returns:
            Dictionary containing the extracted article data or None if extraction failed
        """
        if not url:
            logger.warning("No URL provided for extraction")
            return None
            
        try:
            logger.info(f"Extracting article from: {url}")
            
            # Configure article
            article = Article(url)
            article.config.browser_user_agent = self.user_agent
            
            # Download and parse the article
            article.download()
            article.parse()
            
            # Extract the main content and metadata
            result = {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'top_image': article.top_image,
                'summary': None,
                'keywords': []
            }
            
            # Try to extract natural language processing features
            try:
                article.nlp()
                result['summary'] = article.summary
                result['keywords'] = article.keywords
            except Exception as e:
                logger.warning(f"NLP processing failed: {str(e)}")
            
            logger.info(f"Successfully extracted article: {result['title']}")
            logger.debug(f"Article length: {len(result['text'])} characters")
            
            return result
            
        except ArticleException as ae:
            logger.error(f"Newspaper3k extraction error: {str(ae)}")
        except requests.exceptions.RequestException as re:
            logger.error(f"Request error for {url}: {str(re)}")
        except Exception as e:
            logger.exception(f"Unexpected error extracting article: {str(e)}")
            
        return None
    
    def extract_article_from_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract full article content from a NewsAPI item
        
        Args:
            news_item: Dictionary containing article data from NewsAPI
            
        Returns:
            Enhanced news item with full content if extraction succeeded
        """
        url = news_item.get('url')
        if not url:
            logger.warning("News item has no URL")
            return news_item
            
        extracted = self.extract_article(url)
        if not extracted:
            logger.warning(f"Could not extract article from {url}, using original news item")
            return news_item
            
        # Merge the extracted data with the original news item
        # but prioritize original NewsAPI metadata for consistency
        enhanced_item = news_item.copy()
        
        # Only replace content if we successfully extracted it
        if extracted.get('text'):
            enhanced_item['content'] = extracted['text']
            
        # Add new fields that weren't in the original news item
        if not enhanced_item.get('fullContent'):
            enhanced_item['fullContent'] = extracted.get('text')
            
        if not enhanced_item.get('summary') and extracted.get('summary'):
            enhanced_item['summary'] = extracted.get('summary')
            
        if not enhanced_item.get('keywords') and extracted.get('keywords'):
            enhanced_item['keywords'] = extracted.get('keywords')
            
        if not enhanced_item.get('image') and extracted.get('top_image'):
            enhanced_item['image'] = extracted.get('top_image')
            
        logger.info(f"Enhanced news item with extracted content: {enhanced_item.get('title')}")
        return enhanced_item 