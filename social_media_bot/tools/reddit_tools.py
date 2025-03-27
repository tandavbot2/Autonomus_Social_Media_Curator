import logging
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from ..platforms.manager import PlatformManager
from ..models.platform import Platform
import json
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class RedditPostSchema(BaseModel):
    title: str = Field(..., description="Title for the Reddit post (required)")
    content: str = Field(..., description="Content/body of the post")
    subreddit: str = Field(
        default=None, 
        description="Subreddit to post to (uses default if not specified)"
    )
    flair_text: str = Field(
        default=None,
        description="Flair text for the post (if available in the subreddit)"
    )
    url: str = Field(
        default=None,
        description="URL for link posts (optional, if provided will create a link post)"
    )
    source_id: str = Field(
        default=None,
        description="Source ID for tracking in the database"
    )

class RedditPoster(BaseTool):
    name: str = "Post to Reddit"
    description: str = "Post content to Reddit in selected subreddits"
    args_schema: type[BaseModel] = RedditPostSchema
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platform_manager = PlatformManager()
        
    def _run(self, title: str, content: str, subreddit: Optional[str] = None, 
             flair_text: Optional[str] = None, url: Optional[str] = None,
             source_id: Optional[str] = None) -> Dict[str, Any]:
        """Post content to Reddit"""
        try:
            # Prepare post data for database
            post_data = {
                'platform': 'reddit',
                'content': json.dumps({
                    'title': title,
                    'content': content,
                    'subreddit': subreddit,
                    'url': url
                }),
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'source_id': source_id
            }
            
            # Generate content hash
            hash_content = f"{title}-{content}-{subreddit}-{datetime.utcnow().isoformat()}"
            post_data['content_hash'] = hashlib.md5(hash_content.encode()).hexdigest()
            
            # Store in database before posting
            # This would be implemented based on your database structure
            # db_manager.store_post(post_data)
            
            # Post to Reddit
            result = self.platform_manager.post_to_platform(
                platform=Platform.REDDIT,
                content=content,
                title=title,
                subreddit=subreddit,
                flair_text=flair_text,
                url=url
            )
            
            # Update database with result
            # db_manager.update_post_status(post_data['content_hash'], 'posted' if result['success'] else 'failed')
            
            return result
            
        except Exception as e:
            error_msg = f"Error posting to Reddit: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _get_subreddit_rules(self, subreddit: str) -> List[Dict[str, Any]]:
        """Get posting rules for a subreddit"""
        try:
            reddit_platform = self.platform_manager.platforms.get(Platform.REDDIT)
            if not reddit_platform:
                return []
            
            return reddit_platform.get_subreddit_rules(subreddit)
        except Exception as e:
            logger.error(f"Error getting rules for r/{subreddit}: {str(e)}")
            return [] 