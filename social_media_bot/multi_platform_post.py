#!/usr/bin/env python3
"""
Post tech news to multiple social media platforms
"""
import os
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
from .platforms.manager import PlatformManager
from .models.platform import Platform
from .database.db_manager import DatabaseManager
from .tools.content_strategies import TechNewsStrategy
from .tools.content_quality import ContentEnhancementTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def post_to_platforms(platforms=None, enhance_content=True):
    """Post tech news to specified platforms"""
    if not platforms:
        logger.info("No platforms specified, using all available platforms")
        platforms = [Platform.DEVTO, Platform.MASTODON, Platform.REDDIT]
    
    platform_names = [p.value for p in platforms]
    logger.info(f"Starting tech news posting process for platforms: {', '.join(platform_names)}")
    
    try:
        # Initialize required managers
        platform_manager = PlatformManager()
        db_manager = DatabaseManager()
        
        # Initialize content enhancer if requested
        content_enhancer = ContentEnhancementTool() if enhance_content else None
        
        # Initialize TechNewsStrategy with config
        config = {
            'max_articles': 10,
            'topics': ['ai', 'technology', 'programming', 'cybersecurity'],
            'language': 'en',
            'sort_by': 'publishedAt'
        }
        strategy = TechNewsStrategy(db_manager=db_manager, platform_manager=platform_manager, config=config)
        
        # Check platform availability
        available = {}
        for platform in platforms:
            try:
                status = platform_manager.check_platform_status(platform)
                available[platform] = status
                logger.info(f"Platform {platform.value} available: {status}")
            except Exception as e:
                logger.error(f"Error checking platform {platform.value}: {str(e)}")
                available[platform] = False
        
        available_platforms = [p for p, status in available.items() if status]
        if not available_platforms:
            logger.error("No requested platforms are available")
            return False
        
        # Try up to 5 times to find appropriate news
        for attempt in range(5):
            logger.info(f"Attempt {attempt+1}/5 to find and post tech news")
            
            # Fetch tech news content
            content = strategy.fetch_content()
            if not content:
                logger.error("Failed to fetch valid tech news")
                continue
            
            logger.info(f"Found tech news: {content.get('title', 'No title')}")
            
            # Validate the content is appropriate
            if not strategy.validate_content(content):
                logger.info(f"News not appropriate for posting, trying again")
                continue
            
            # Enhance content if requested
            if enhance_content and content_enhancer:
                try:
                    logger.info("Enhancing content quality...")
                    
                    # Extract content details
                    original_content = content.get('content', '')
                    source = content.get('source', {}).get('name', 'Tech News Source') if isinstance(content.get('source'), dict) else content.get('source', 'Tech News Source')
                    url = content.get('url', '')
                    
                    # Apply content quality enhancement
                    enhanced_result = content_enhancer._run(
                        content=original_content,
                        content_type="tech_news",
                        source=source,
                        source_url=url
                    )
                    
                    # Update the content if enhancement was successful
                    if enhanced_result.get('enhanced_content'):
                        logger.info(f"Content quality improved: {enhanced_result.get('original_score')}% → {enhanced_result.get('enhanced_score')}%")
                        content['content'] = enhanced_result.get('enhanced_content')
                        
                        if enhanced_result.get('enhancements_applied'):
                            logger.info(f"Enhancements applied: {', '.join(enhanced_result.get('enhancements_applied'))}")
                except Exception as e:
                    logger.warning(f"Error enhancing content (continuing anyway): {str(e)}")
            
            # Format content for each platform and post
            platform_results = {}
            for platform in available_platforms:
                try:
                    # Format content for this specific platform
                    formatted_content = strategy.format_for_platform(content, platform)
                    if not formatted_content:
                        logger.warning(f"Could not format content for {platform.value}")
                        continue
                        
                    # Post to this platform
                    logger.info(f"Posting to {platform.value}...")
                    result = platform_manager.post_to_platform(platform, **formatted_content)
                    platform_results[platform] = result
                    
                    if result.get("success"):
                        logger.info(f"Successfully posted to {platform.value}")
                        post_url = result.get('data', {}).get('url', 'Unknown URL')
                        logger.info(f"Post URL: {post_url}")
                    else:
                        error = result.get("error", "Unknown error")
                        logger.error(f"Failed to post to {platform.value}: {error}")
                except Exception as e:
                    logger.error(f"Error processing {platform.value}: {str(e)}")
                    platform_results[platform] = {"success": False, "error": str(e)}
            
            # Check if any platform was successful
            success = any(result.get("success", False) for result in platform_results.values())
            
            if success:
                return True
            
        logger.error("All attempts to post tech news failed")
        return False
        
    except Exception as e:
        logger.error(f"Error in post_to_platforms: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to handle command-line execution"""
    # Parse command line arguments
    args = sys.argv[1:]
    platforms = []
    enhance_content = True
    
    i = 0
    while i < len(args):
        if args[i] == "--platforms" and i+1 < len(args):
            platform_names = args[i+1].split(',')
            for name in platform_names:
                name = name.strip().lower()
                try:
                    platform = Platform(name)
                    platforms.append(platform)
                except ValueError:
                    logger.warning(f"Invalid platform name: {name}")
            i += 2
        elif args[i] == "--no-enhance":
            enhance_content = False
            i += 1
        else:
            i += 1
    
    success = post_to_platforms(platforms, enhance_content)
    
    if success:
        logger.info("Tech news posting completed successfully")
        sys.exit(0)
    else:
        logger.error("Tech news posting failed")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 