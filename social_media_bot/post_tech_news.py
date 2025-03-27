#!/usr/bin/env python3
"""
Script to fetch and post tech news to configured social media platforms
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from .platforms.manager import PlatformManager
from .database.db_manager import DatabaseManager
from .tools.content_strategies import TechNewsStrategy
from .models.platform import Platform

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if environment variables are set"""
    required_vars = ['NEWS_API_KEY']
    optional_vars = ['DEEPSEEK_API_KEY', 'DEEPSEEK_API_URL']
    
    # Check for required environment variables
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
        
    # Check for optional environment variables and provide warnings
    for var in optional_vars:
        if not os.environ.get(var):
            logger.warning(f"Optional environment variable not set: {var}")
            
            if var == 'DEEPSEEK_API_KEY':
                logger.warning("DeepSeek integration for enhanced blog posts will be disabled")
    
    return True

def main():
    """Main function to post tech news"""
    load_dotenv()
    
    if not check_environment():
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Post tech news to social media platforms')
    parser.add_argument('--platforms', type=str, help='Comma-separated list of platforms to post to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    try:
        # Initialize platform manager
        platform_manager = PlatformManager()
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Parse specified platforms or use all available
        if args.platforms:
            platform_names = [p.strip().lower() for p in args.platforms.split(',')]
            platforms = []
            for name in platform_names:
                try:
                    platform = Platform(name)
                    platforms.append(platform)
                except ValueError:
                    logger.warning(f"Invalid platform name: {name}")
        else:
            # Use all enabled platforms
            platforms = platform_manager.check_all_statuses()
            platforms = [p for p, status in platforms.items() if status]
        
        if not platforms:
            logger.error("No valid platforms specified or available")
            sys.exit(1)
            
        logger.info(f"Posting tech news to platforms: {', '.join([p.value for p in platforms])}")
        
        # Configure tech news strategy
        config = {
            'max_articles': 10,
            'topics': ['ai', 'technology', 'programming', 'cybersecurity'],
            'language': 'en',
            'sort_by': 'publishedAt',
            'reddit_subreddit': 'technology'  # Default subreddit for Reddit posts
        }
        
        strategy = TechNewsStrategy(
            db_manager=db_manager,
            platform_manager=platform_manager,
            config=config
        )
        
        # Fetch tech news content
        content = strategy.fetch_content()
        if not content:
            logger.error("Failed to fetch valid tech news content")
            sys.exit(1)
            
        logger.info(f"Found tech news: {content.get('title')}")
        
        # Validate content is appropriate for posting
        if not strategy.validate_content(content):
            logger.error("Content validation failed, not suitable for posting")
            sys.exit(1)
            
        # Post to each platform
        success = False
        for platform in platforms:
            try:
                # Format content for this platform
                formatted_content = strategy.format_for_platform(content, platform)
                if not formatted_content:
                    logger.warning(f"Could not format content for {platform.value}")
                    continue
                    
                # Post to platform
                logger.info(f"Posting to {platform.value}...")
                result = platform_manager.post_to_platform(platform, **formatted_content)
                
                if result.get("success"):
                    logger.info(f"Successfully posted to {platform.value}")
                    post_url = result.get('data', {}).get('url', 'Unknown URL')
                    logger.info(f"Post URL: {post_url}")
                    success = True
                else:
                    error = result.get("error", "Unknown error")
                    logger.error(f"Failed to post to {platform.value}: {error}")
            except Exception as e:
                logger.exception(f"Error posting to {platform.value}: {str(e)}")
        
        if success:
            logger.info("Tech news successfully posted to at least one platform")
            sys.exit(0)
        else:
            logger.error("Failed to post tech news to any platform")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 