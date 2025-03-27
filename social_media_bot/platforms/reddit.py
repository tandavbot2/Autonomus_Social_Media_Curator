import os
import praw
import logging
from typing import Dict, Any, List, Optional
from .base import SocialMediaPlatform
from ..models.platform import Platform
from dotenv import load_dotenv
from ..utils.rate_limiter import RateLimiter

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class RedditPostError(Exception):
    """Exception raised for Reddit posting errors"""
    pass

class RedditAuthError(Exception):
    """Exception raised for Reddit authentication errors"""
    pass

class RedditAPI(SocialMediaPlatform):
    """Implementation of Reddit platform using PRAW"""
    
    def __init__(self):
        super().__init__(Platform.REDDIT)
        # Get credentials from environment
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.user_agent = os.getenv('REDDIT_USER_AGENT')
        self.default_subreddits = os.getenv('REDDIT_DEFAULT_SUBREDDITS', '').split(',')
        
        # Initialize rate limiter
        rate_limits = {
            'posts_per_hour': 5,
            'posts_per_day': 20,
            'minimum_interval': 300,
            'cooldown_period': 3600
        }
        self.rate_limiter = RateLimiter(rate_limits)
        self.reddit = None
        self.is_authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with Reddit API"""
        try:
            if not all([self.client_id, self.client_secret, self.username, self.password, self.user_agent]):
                logger.error("Missing Reddit credentials")
                return False
                
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                username=self.username,
                password=self.password,
                user_agent=self.user_agent
            )
            
            # Verify authentication
            username = self.reddit.user.me().name
            logger.info(f"Authenticated as Reddit user: {username}")
            self.is_authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"Reddit authentication error: {str(e)}")
            self.is_authenticated = False
            return False
    
    def post_content(self, content: str = None, **kwargs) -> Dict[str, Any]:
        """Post content to Reddit"""
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return {"success": False, "error": "Authentication failed"}
            
            # Check rate limits
            if not self.rate_limiter.can_post():
                wait_time = self.rate_limiter.get_wait_time()
                return {
                    "success": False, 
                    "error": f"Rate limit exceeded. Try again in {wait_time} seconds."
                }
            
            # Get parameters
            title = kwargs.get('title')
            subreddit_name = kwargs.get('subreddit')
            post_type = kwargs.get('post_type', 'text')  # Default to text post
            url = kwargs.get('url')
            flair_id = kwargs.get('flair_id')
            flair_text = kwargs.get('flair_text')
            
            # Validate required parameters
            if not title:
                return {"success": False, "error": "Title is required for Reddit posts"}
            
            if not subreddit_name:
                if not self.default_subreddits:
                    return {"success": False, "error": "No subreddit specified and no defaults configured"}
                subreddit_name = self.default_subreddits[0]
            
            # Get the subreddit
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Create the post
            logger.info(f"Posting to r/{subreddit_name} with title: {title}")
            
            try:
                if post_type == 'link' and url:
                    # Create a link post
                    logger.info(f"Link post created: {url}")
                    submission = subreddit.submit(
                        title=title,
                        url=url,
                        flair_id=flair_id,
                        flair_text=flair_text
                    )
                else:
                    # For text posts, content is required
                    if content is None:
                        return {"success": False, "error": "Content is required for text posts"}
                        
                    # Create a text post
                    logger.info("Text post created")
                    submission = subreddit.submit(
                        title=title,
                        selftext=content,
                        flair_id=flair_id,
                        flair_text=flair_text
                    )
                
                # Record successful post for rate limiting
                self.rate_limiter.record_post()
                
                return {
                    "success": True,
                    "data": {
                        "id": submission.id,
                        "url": submission.url,
                        "permalink": submission.permalink
                    }
                }
                
            except Exception as e:
                error_msg = f"Error posting to Reddit: {str(e)}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Reddit posting error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _format_content(self, content: str) -> tuple:
        """Format content for Reddit (split into title and body)"""
        lines = content.strip().split('\n')
        title = lines[0][:300]  # Reddit title limit
        
        # If content has multiple lines, use the rest as body
        body = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        return title, body
    
    def get_profile(self) -> Dict[str, Any]:
        """Get the authenticated user's profile information"""
        if not self.is_authenticated and not self.authenticate():
            return {"success": False, "error": "Authentication failed"}
            
        try:
            user = self.reddit.user.me()
            return {
                "success": True,
                "username": user.name,
                "karma": user.link_karma + user.comment_karma,
                "created_utc": user.created_utc,
                "is_gold": user.is_gold,
                "platform": "reddit"
            }
            
        except Exception as e:
            logger.error(f"Error getting Reddit profile: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_status(self) -> bool:
        """Check if the Reddit API is available"""
        try:
            if not self.reddit and not self.authenticate():
                return False
                
            # Simple API call to check status
            self.reddit.user.me()
            return True
            
        except Exception as e:
            logger.error(f"Error checking Reddit API status: {str(e)}")
            return False
    
    def get_subreddit_rules(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """Get posting rules for a subreddit"""
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return []
            
            subreddit = self.reddit.subreddit(subreddit_name)
            rules = subreddit.rules()
            
            return [
                {
                    "short_name": rule.short_name,
                    "description": rule.description,
                    "violation_reason": rule.violation_reason,
                    "kind": rule.kind
                }
                for rule in rules
            ]
        except Exception as e:
            logger.error(f"Failed to get rules for r/{subreddit_name}: {str(e)}")
            return []
    
    def get_subreddit_flairs(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """Get available flairs for a subreddit"""
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return []
            
            subreddit = self.reddit.subreddit(subreddit_name)
            flairs = list(subreddit.flair.link_templates)
            
            return [
                {
                    "id": flair["id"],
                    "text": flair["text"],
                    "background_color": flair.get("background_color"),
                    "text_color": flair.get("text_color")
                }
                for flair in flairs
            ]
        except Exception as e:
            logger.error(f"Failed to get flairs for r/{subreddit_name}: {str(e)}")
            return []

# For backward compatibility
Reddit = RedditAPI 