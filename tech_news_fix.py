#!/usr/bin/env python3
"""
Fixed script to post tech news to social media platforms
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def post_tech_news():
    """Post tech news to connected platforms"""
    try:
        # Import here to avoid circular imports
        from social_media_bot.platforms.manager import PlatformManager
        from social_media_bot.models.platform import Platform
        from social_media_bot.database.db_manager import DatabaseManager
        from social_media_bot.tools.content_strategies import TechNewsStrategy
        from social_media_bot.tools.content_quality import ContentEnhancementTool

        # Initialize platform manager
        logger.info("Initializing platform manager...")
        platform_manager = PlatformManager()
        
        # Initialize database manager
        logger.info("Initializing database manager...")
        db_manager = DatabaseManager()
        
        # Initialize content enhancer
        logger.info("Initializing content enhancer...")
        content_enhancer = ContentEnhancementTool()

        # Initialize tech news strategy with required dependencies
        logger.info("Initializing TechNewsStrategy...")
        strategy = TechNewsStrategy(platform_manager=platform_manager, db_manager=db_manager)

        # Check platform statuses
        platform_statuses = platform_manager.check_all_platforms()
        logger.info(f"Platform statuses: {platform_statuses}")
        
        # Filter for available platforms
        available_platforms = [p for p, status in platform_statuses.items() if status]
        if not available_platforms:
            logger.error("No platforms available for posting")
            return False
            
        logger.info(f"Available platforms: {[p.name for p in available_platforms]}")
        
        # Try up to 3 times to find appropriate news
        for attempt in range(3):
            logger.info(f"Attempt {attempt+1}/3 to find and post tech news")
            
            # Fetch tech news content
            content = strategy.fetch_content()
            if not content:
                logger.error("Failed to fetch valid tech news")
                continue
            
            logger.info(f"Found tech news: {content.get('title', 'No title')}")
            
            # Validate the content
            if not strategy.validate_content(content):
                logger.info(f"News not appropriate for posting, trying again")
                continue
                
            # Enhance content quality
            try:
                logger.info("Enhancing content quality...")
                
                # Extract the main content
                original_content = content.get('content', '')
                
                # Apply content quality enhancement
                enhanced_result = content_enhancer._run(
                    content=original_content,
                    content_type="tech_news",
                    source=content.get('source', {}).get('name', 'Tech News Source'),
                    source_url=content.get('url', '')
                )
                
                # Update the content with enhanced version
                if enhanced_result.get('enhanced_content'):
                    logger.info(f"Content quality improved: {enhanced_result.get('original_score')}% -> {enhanced_result.get('enhanced_score')}%")
                    content['content'] = enhanced_result.get('enhanced_content')
                    
                    if enhanced_result.get('enhancements_applied'):
                        logger.info(f"Enhancements applied: {', '.join(enhanced_result.get('enhancements_applied'))}")
            except Exception as e:
                logger.warning(f"Content enhancement error (continuing anyway): {str(e)}")
            
            # Post to available platforms
            results = strategy.post_to_platforms(content, available_platforms)
            
            # Check if posting was successful
            success = False
            for platform, result in results.items():
                if result.get("success"):
                    logger.info(f"Successfully posted to {platform.name}")
                    success = True
                else:
                    error = result.get("error", "Unknown error")
                    logger.error(f"Failed to post to {platform.name}: {error}")
            
            if success:
                return True
        
        logger.error("All attempts to post tech news failed")
        return False
        
    except Exception as e:
        logger.error(f"Error in post_tech_news: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = post_tech_news()
    if success:
        logger.info("Tech news posting completed successfully")
        sys.exit(0)
    else:
        logger.error("Tech news posting failed")
        sys.exit(1) 