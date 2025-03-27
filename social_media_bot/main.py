import logging
from dotenv import load_dotenv
from crewai import Crew, Task
from .agents import get_database_manager, get_content_curator, get_content_creator
from .database.init_db import init_database as init_db
from .database.db_manager import DatabaseManager
from .platforms.manager import PlatformManager
from .tools.content_strategies import TechNewsStrategy
from .tools.news_fetcher import MultiNewsApiFetcher
from .models.platform import Platform
from argparse import ArgumentParser
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    try:
        load_dotenv()
        
        # Parse command line arguments
        parser = ArgumentParser(description="Run the social media bot")
        parser.add_argument(
            "--strategy", 
            choices=["default", "tech_news"], 
            default="default",
            help="Content strategy to use (default: standard CrewAI based content)"
        )
        parser.add_argument(
            "--platforms",
            help="Comma-separated list of platforms to post to (default: all enabled platforms)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force content generation even if APIs are rate-limited"
        )
        
        # Check if any arguments were provided
        if len(sys.argv) > 1:
            args = parser.parse_args()
        else:
            # Use default values if no arguments
            args = parser.parse_args(["--strategy", "default"])
        
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")

        # Initialize platform manager and check statuses
        platform_manager = PlatformManager()
        db_manager = DatabaseManager()
        platform_statuses = platform_manager.check_all_statuses()
        logger.info(f"Platform statuses: {platform_statuses}")

        # If using alternative strategies (like tech_news)
        if args.strategy == "tech_news":
            logger.info("Using tech news strategy")
            # Initialize news fetcher and strategy
            news_fetcher = MultiNewsApiFetcher()
            
            # Check if any API is available before continuing
            if not (news_fetcher.has_news_api or news_fetcher.has_the_news_api) and not args.force:
                logger.error("No news APIs are configured. Add API keys to .env file or use --force to use cached content.")
                return False
                
            # Check if both APIs are rate limited by doing a test fetch
            if news_fetcher.newsapi_calls_today >= news_fetcher.MAX_API_CALLS and news_fetcher.the_news_api_calls_today >= news_fetcher.MAX_API_CALLS and not args.force:
                logger.error("All news APIs are rate-limited. Try again later or use --force to use cached content.")
                return False
                
            strategy = TechNewsStrategy(platform_manager, db_manager, news_fetcher)
            
            # Generate tech news content
            content_list = strategy.generate_content()
            if not content_list:
                logger.error("Failed to generate tech news content")
                return False
                
            logger.info(f"Successfully generated {len(content_list)} content items")
                
            # Parse platforms argument if provided
            platforms = None
            if args.platforms:
                platform_names = args.platforms.split(',')
                platforms = []
                for name in platform_names:
                    try:
                        platform = Platform(name.strip())
                        platforms.append(platform)
                    except ValueError:
                        logger.warning(f"Invalid platform: {name}")
            
            # Track URLs we've posted in this session to avoid duplicates
            posted_urls = set()
            
            # Post all content items to platforms
            success = True
            for content in content_list:
                # Skip if we've already posted this article in this session
                url = content.get('url', '')
                if url in posted_urls:
                    logger.info(f"Skipping already posted article in this session: {content.get('title')}")
                    continue
                
                # Validate the content
                if not strategy.validate_content(content):
                    logger.error(f"Content validation failed: {content.get('title')}")
                    continue
                
                # Detailed logs for content being posted
                logger.info(f"Posting article: {content.get('title')}")
                logger.info(f"Source: {content.get('source')}")
                logger.info(f"URL: {content.get('url')}")
                    
                # Post to platforms
                results = strategy.post_to_platforms(content, platforms)
                
                # Log results
                post_success = False
                for platform, result in results.items():
                    if result.get("success"):
                        logger.info(f"Posted to {platform.value} successfully: {content.get('title')}")
                        post_success = True
                    else:
                        logger.error(f"Failed to post to {platform.value}: {result.get('error')}")
                        success = False
                
                # If we posted successfully to at least one platform, add to our posted URLs
                if post_success:
                    posted_urls.add(url)
            
            if len(posted_urls) > 0:
                logger.info(f"Successfully posted {len(posted_urls)} articles")
            else:
                logger.warning("No articles were successfully posted")
                        
            return success
            
        else:
            # Original CrewAI approach
            # Create content creation and posting task
            content_task = Task(
                description=(
                    "Create and post engaging content by following these exact steps:\n"
                    "1. Generate the following content:\n"
                    "   - A post about the successful database verification\n"
                    "   - Include the operational status and accessibility\n"
                    "   - Make it engaging and informative\n"
                    "2. Use the ContentPostingTool to:\n"
                    "   - Show the content for review\n"
                    "   - Get user approval\n"
                    "   - Handle platform selection\n"
                    "   - Post to selected platforms\n"
                    "3. Report the posting results\n\n"
                    "IMPORTANT: You must use the ContentPostingTool to handle the posting process."
                ),
                expected_output=(
                    "A string containing a JSON object with the following structure:\n"
                    "{\n"
                    '    "content": "The generated content",\n'
                    '    "posting_results": {\n'
                    '        "platform1": {"success": true/false, "url": "post_url"},\n'
                    '        "platform2": {"success": true/false, "url": "post_url"}\n'
                    "    },\n"
                    '    "status": "success/failure"\n'
                    "}"
                ),
                agent=get_content_creator()
            )

            # Create crew with task
            crew = Crew(
                agents=[get_content_creator()],
                tasks=[content_task],
                verbose=True
            )

            result = crew.kickoff()
            return result

    except Exception as e:
        logger.error(f"Error running crew: {str(e)}")
        raise

if __name__ == "__main__":
    main() 