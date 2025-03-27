from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.platform import Platform

class SocialMediaPlatform(ABC):
    """Base class for social media platforms"""
    
    def __init__(self, platform_type: Platform):
        self.platform_type = platform_type
        self.is_authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass

    @abstractmethod
    def post_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Post content to the platform"""
        pass

    @abstractmethod
    def check_status(self) -> bool:
        """Check platform connection status"""
        pass 