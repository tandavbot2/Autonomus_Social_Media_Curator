from typing import Dict, Optional
import os
from dotenv import load_dotenv
from ..models.platform import Platform
from .base import SocialMediaPlatform
from .devto import DevToAPI
from .mastodon import MastodonAPI
from .reddit import RedditAPI

load_dotenv()

class PlatformFactory:
    """Factory for creating social media platform instances"""
    
    @staticmethod
    def create_platform(platform: Platform) -> Optional[SocialMediaPlatform]:
        """Create and return a platform instance based on the platform enum"""
        
        # Use PlatformConfig to check if enabled
        from ..config.platforms import PlatformConfig
        if not PlatformConfig.is_enabled(platform):
            return None
            
        if platform == Platform.DEVTO:
            return DevToAPI()
        elif platform == Platform.MASTODON:
            return MastodonAPI()
        elif platform == Platform.REDDIT:
            return RedditAPI()
        else:
            return None
    
    @staticmethod
    def get_all_enabled_platforms() -> Dict[Platform, bool]:
        """Get all platforms and their enabled status"""
        platforms = {}
        
        for platform in Platform:
            enabled = os.getenv(f"{platform.name}_ENABLED", "false").lower() == "true"
            platforms[platform] = enabled
            
        return platforms 