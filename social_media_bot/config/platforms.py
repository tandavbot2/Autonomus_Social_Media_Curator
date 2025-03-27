import os
from ..models.platform import Platform  # Import from models instead of redefining

class PlatformConfig:
    """Platform configuration and availability"""
    
    @staticmethod
    def get_enabled_platforms():
        """Get list of enabled platforms"""
        # Only return platforms that have credentials configured and are enabled
        enabled = []
        
        # Check both credentials and enablement flags
        if os.getenv('DEVTO_API_KEY') and os.getenv('DEVTO_ENABLED', 'false').lower() == 'true':
            enabled.append(Platform.DEVTO)
            
        if os.getenv('MASTODON_ACCESS_TOKEN') and os.getenv('MASTODON_ENABLED', 'false').lower() == 'true':
            enabled.append(Platform.MASTODON)
            
        if os.getenv('REDDIT_CLIENT_ID') and os.getenv('REDDIT_CLIENT_SECRET') and os.getenv('REDDIT_ENABLED', 'false').lower() == 'true':
            enabled.append(Platform.REDDIT)
            
        return enabled

    @staticmethod
    def is_enabled(platform: Platform) -> bool:
        """Check if a platform is enabled"""
        return platform in PlatformConfig.get_enabled_platforms() 