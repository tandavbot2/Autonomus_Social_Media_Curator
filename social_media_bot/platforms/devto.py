import os
import requests
import json
import logging
from typing import Dict, Any
from .base import SocialMediaPlatform
from ..models.platform import Platform

# Initialize logger
logger = logging.getLogger(__name__)

class DevToAPI(SocialMediaPlatform):
    """Dev.to platform implementation"""
    
    def __init__(self):
        super().__init__(Platform.DEVTO)
        self.api_key = os.getenv('DEVTO_API_KEY')
        self.base_url = "https://dev.to/api"
        
    def authenticate(self) -> bool:
        """Verify Dev.to API key"""
        try:
            if not self.api_key:
                print("Dev.to API key is missing")
                return False
            
            headers = {'api-key': self.api_key}
            response = requests.get(f"{self.base_url}/articles/me", headers=headers)
            
            if response.status_code == 200:
                print("Dev.to authentication successful")
                self.is_authenticated = True
                return True
            
            print(f"Dev.to authentication failed: {response.status_code} - {response.text}")
            self.is_authenticated = False
            return False
        except Exception as e:
            print(f"Dev.to authentication error: {str(e)}")
            self.is_authenticated = False
            return False

    def post_content(self, content=None, **kwargs):
        """Post content to Dev.to"""
        try:
            # If content is a dictionary, use it directly
            # Otherwise, use the keyword arguments
            content_data = content if isinstance(content, dict) else kwargs
            
            # Authenticate
            if not self.authenticate():
                return {"success": False, "error": "Authentication failed"}
            
            # Add debug logging for the content data
            logger.info(f"Dev.to post data: {json.dumps(content_data, indent=2)}")
            
            # Ensure required fields are present
            title = content_data.get('title')
            body_markdown = content_data.get('body_markdown')
            
            if not title or not body_markdown:
                logger.error(f"Missing required Dev.to post fields. Title: {bool(title)}, Body Markdown: {bool(body_markdown)}")
                return {"success": False, "error": "Missing required fields (title or body_markdown)"}
            
            # Prepare the article data
            tags = content_data.get('tags', ['technology'])
            article_data = {
                'article': {
                    'title': title,
                    'body_markdown': body_markdown,
                    'published': content_data.get('published', True),
                    'tags': tags
                }
            }
            
            # Add canonical URL if present
            if content_data.get('canonical_url'):
                article_data['article']['canonical_url'] = content_data.get('canonical_url')
            
            # Add series if present
            if content_data.get('series'):
                article_data['article']['series'] = content_data.get('series')
            
            # Prepare request
            url = 'https://dev.to/api/articles'
            headers = {
                'api-key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Posting to Dev.to with title: {title}")
            
            # Send request
            response = requests.post(url, headers=headers, json=article_data)
            
            # Handle response
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Successfully posted to Dev.to: Article ID {data.get('id')}")
                return {
                    "success": True,
                    "data": {
                        "id": data.get('id'),
                        "url": data.get('url'),
                        "title": data.get('title')
                    }
                }
            else:
                error_msg = f"Dev.to API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.exception(f"Error posting to Dev.to: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_status(self) -> bool:
        """Check Dev.to API status"""
        try:
            response = requests.get(f"{self.base_url}/articles")
            return response.status_code == 200
        except:
            return False 