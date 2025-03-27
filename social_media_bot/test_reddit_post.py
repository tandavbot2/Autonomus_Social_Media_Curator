import os
import logging
from dotenv import load_dotenv
from .platforms.manager import PlatformManager
from .models.platform import Platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_reddit_post():
    """Test posting to Reddit directly"""
    logger.info("Initializing platform manager...")
    platform_manager = PlatformManager()
    
    # Check if Reddit is enabled and connected
    statuses = platform_manager.check_all_statuses()
    logger.info(f"Platform statuses: {statuses}")
    
    # Debug: Check if Reddit is in the platforms dictionary
    logger.info(f"Available platforms: {list(platform_manager.platforms.keys())}")
    
    # Try to get Reddit platform directly
    reddit_platform = platform_manager.platforms.get(Platform.REDDIT)
    if reddit_platform:
        logger.info("Reddit platform is available in the manager")
        is_authenticated = reddit_platform.authenticate()
        logger.info(f"Reddit authentication: {is_authenticated}")
        
        # Create a test tech news post
        title = "Microsoft Announces New AI Features for Windows 11"
        content = """Microsoft has unveiled a suite of new AI-powered features for Windows 11, 
        including enhanced voice recognition, smart content generation, and improved virtual assistant capabilities.
        These features are expected to roll out in the next major update."""
        url = "https://www.theverge.com/2023/5/23/23733181/microsoft-windows-11-ai-features-build"
        
        # Get the default subreddit from environment
        subreddits = os.getenv('REDDIT_DEFAULT_SUBREDDITS', '').split(',')
        subreddit = subreddits[0] if subreddits else 'test'
        
        logger.info(f"Posting to r/{subreddit} with title: {title}")
        
        # Post to Reddit directly using the platform instance
        result = reddit_platform.post_content(
            content=content,
            title=title,
            url=url,
            subreddit=subreddit,
            post_type='link'  # Force link post for technews
        )
        
        # Log the result
        if result.get('success'):
            logger.info(f"Post successful! URL: {result.get('data', {}).get('url')}")
        else:
            logger.error(f"Post failed: {result.get('error')}")
        
        return result
    else:
        logger.error("Reddit platform is not available in the manager")
        return {"success": False, "error": "Reddit platform not available"}

if __name__ == "__main__":
    test_reddit_post() 