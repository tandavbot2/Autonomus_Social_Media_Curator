import logging
import sys
from ..platforms.platform_factory import PlatformFactory
from ..models.platform import Platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_platform_statuses():
    """Check the status of all enabled platforms"""
    platforms = PlatformFactory.get_all_enabled_platforms()
    
    logger.info(f"Platform enablement status: {platforms}")
    
    # Initialize and check each enabled platform
    results = {}
    for platform, enabled in platforms.items():
        if enabled:
            logger.info(f"Checking {platform.value}...")
            instance = PlatformFactory.create_platform(platform)
            if instance:
                try:
                    status = instance.check_status()
                    results[platform] = status
                    logger.info(f"Platform {platform.value}: {'Connected' if status else 'Failed to connect'}")
                except Exception as e:
                    results[platform] = False
                    logger.error(f"Error checking {platform.value}: {str(e)}")
            else:
                results[platform] = False
                logger.warning(f"Platform {platform.value} is enabled but could not be initialized")
        else:
            results[platform] = False
            logger.info(f"Platform {platform.value}: Disabled")
    
    return results

if __name__ == "__main__":
    logger.info("Starting platform status check...")
    results = check_platform_statuses()
    
    # Print summary
    logger.info("\n=== Platform Status Summary ===")
    for platform, status in results.items():
        logger.info(f"{platform.value}: {'✅ Connected' if status else '❌ Disconnected'}") 