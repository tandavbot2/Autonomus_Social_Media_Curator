import os
from typing import Dict, Any
from mastodon import Mastodon as MastodonClient
from .base import SocialMediaPlatform
from ..models.platform import Platform
import logging

# Set up logging
logger = logging.getLogger(__name__)

class MastodonAPI(SocialMediaPlatform):
    """Mastodon platform implementation"""
    
    def __init__(self):
        super().__init__(Platform.MASTODON)
        self.server = os.getenv('MASTODON_SERVER', 'https://mastodon.social')
        self.access_token = os.getenv('MASTODON_ACCESS_TOKEN')
        self.api = None
        self.is_authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with Mastodon"""
        try:
            if not self.access_token:
                logger.error("Missing Mastodon access token")
                return False

            self.api = MastodonClient(
                access_token=self.access_token,
                api_base_url=self.server
            )
            # Verify credentials
            self.api.account_verify_credentials()
            self.is_authenticated = True
            logger.info("Mastodon authentication successful")
            return True
        except Exception as e:
            logger.error(f"Mastodon authentication error: {str(e)}")
            self.is_authenticated = False
            return False

    def post_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Post content to Mastodon"""
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return {"success": False, "error": "Authentication failed"}

            try:
                visibility = kwargs.get('visibility', 'public')
                media_ids = kwargs.get('media_ids', None)
                
                status = self.api.status_post(
                    status=content,
                    media_ids=media_ids,
                    visibility=visibility
                )

                logger.info(f"Mastodon post URL: {status.get('url', 'URL not available')}")
                return {
                    "success": True,
                    "data": status,
                    "url": status.get('url', '')
                }
            except Exception as e:
                logger.error(f"Mastodon API Error: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
        except Exception as e:
            logger.error(f"Mastodon posting error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def check_status(self) -> bool:
        """Check Mastodon connection status"""
        try:
            if not self.api:
                return self.authenticate()
            self.api.instance()
            return True
        except Exception as e:
            logger.error(f"Mastodon status check failed: {str(e)}")
            return False 