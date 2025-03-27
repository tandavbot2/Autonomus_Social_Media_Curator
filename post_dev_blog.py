#!/usr/bin/env python3
"""
Helper script to post enhanced tech news blog posts to Dev.to using DeepSeek API
"""
import sys
import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the tech news blog posting"""
    # Load environment variables
    load_dotenv()
    
    # Check for required API keys
    if not os.environ.get('NEWS_API_KEY'):
        logger.error("NEWS_API_KEY environment variable is required")
        sys.exit(1)
        
    if not os.environ.get('DEEPSEEK_API_KEY'):
        logger.warning("DEEPSEEK_API_KEY environment variable not set.")
        logger.warning("Will use fallback blog formatting without DeepSeek enhancement.")
    
    if not os.environ.get('DEVTO_API_KEY'):
        logger.error("DEVTO_API_KEY environment variable is required for posting to Dev.to")
        sys.exit(1)
    
    # Import here to avoid circular imports
    from social_media_bot.post_tech_news import main as post_tech_news_main
    
    # Run the tech news posting script with Dev.to platform
    sys.argv.extend(['--platforms', 'dev.to', '--debug'])
    post_tech_news_main()

if __name__ == "__main__":
    main() 