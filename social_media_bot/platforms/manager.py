from typing import Dict, List, Any
from .base import SocialMediaPlatform
from .devto import DevToAPI
from .mastodon import MastodonAPI
from .reddit import RedditAPI
from ..models.platform import Platform
from ..config.platforms import PlatformConfig
import logging

# Set up logging
logger = logging.getLogger(__name__)

class PlatformManager:
    """Manages multiple social media platforms"""
    
    def __init__(self):
        self.platforms: Dict[Platform, SocialMediaPlatform] = {}
        self._initialize_platforms()

    def _initialize_platforms(self):
        """Initialize all enabled platforms"""
        platform_map = {
            Platform.DEVTO: DevToAPI,
            Platform.MASTODON: MastodonAPI,
            Platform.REDDIT: RedditAPI,
            # ... other platforms
        }
        
        enabled_platforms = PlatformConfig.get_enabled_platforms()
        logger.info(f"Enabled platforms: {[p.value for p in enabled_platforms]}")
        
        for platform in enabled_platforms:
            if platform in platform_map:
                try:
                    self.platforms[platform] = platform_map[platform]()
                    logger.info(f"Initialized {platform.value} platform")
                except Exception as e:
                    logger.error(f"Failed to initialize {platform.value}: {str(e)}")

    def authenticate_all(self) -> Dict[Platform, bool]:
        """Authenticate all platforms"""
        results = {}
        for platform, instance in self.platforms.items():
            try:
                results[platform] = instance.authenticate()
                logger.info(f"Authentication for {platform.value}: {'Success' if results[platform] else 'Failed'}")
            except Exception as e:
                logger.error(f"Error authenticating {platform.value}: {str(e)}")
                results[platform] = False
        return results

    def post_to_platform(self, platform: Platform, content: str = None, **kwargs) -> Dict[str, Any]:
        """Post content to specific platform"""
        if platform not in self.platforms:
            logger.warning(f"Platform {platform.value} not initialized")
            return {"success": False, "error": f"Platform {platform.value} not initialized"}
            
        logger.info(f"Posting to {platform.value}")
        return self.platforms[platform].post_content(content, **kwargs)

    def post_to_all(self, content: str = None, **kwargs) -> Dict[Platform, Dict[str, Any]]:
        """Post content to all platforms"""
        results = {}
        for platform, instance in self.platforms.items():
            try:
                logger.info(f"Posting to {platform.value}")
                results[platform] = instance.post_content(content, **kwargs)
            except Exception as e:
                logger.error(f"Error posting to {platform.value}: {str(e)}")
                results[platform] = {"success": False, "error": str(e)}
        return results

    def check_platform_status(self, platform: Platform) -> bool:
        """Check status of specific platform"""
        if platform not in self.platforms:
            logger.warning(f"Platform {platform.value} not initialized")
            return False
        return self.platforms[platform].check_status()

    def check_all_statuses(self) -> Dict[Platform, bool]:
        """Check status of all platforms"""
        statuses = {}
        for platform, instance in self.platforms.items():
            try:
                status = instance.check_status()
                statuses[platform] = status
                logger.info(f"Status for {platform.value}: {'Connected' if status else 'Disconnected'}")
            except Exception as e:
                logger.error(f"Error checking status for {platform.value}: {str(e)}")
                statuses[platform] = False
        return statuses 