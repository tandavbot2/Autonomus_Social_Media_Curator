from datetime import datetime, timedelta
from typing import Dict, Any
import logging
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for social media platforms"""
    
    def __init__(self, limits: Dict[str, Any] = None):
        """Initialize rate limiter with optional limits"""
        self.limits = limits or {
            'posts_per_hour': 5,
            'posts_per_day': 20,
            'minimum_interval': 300,  # 5 minutes between posts
            'cooldown_period': 3600  # 1 hour cooldown if limit reached
        }
        self.post_history = deque(maxlen=1000)  # Store last 1000 posts
        self.hourly_posts = 0
        self.daily_posts = 0
        self.last_reset = datetime.utcnow()
    
    def can_post(self) -> bool:
        """Check if posting is allowed based on rate limits"""
        now = datetime.utcnow()
        self._update_counters(now)
        
        # Check minimum interval between posts
        if self.post_history and (now - self.post_history[-1]).total_seconds() < self.limits['minimum_interval']:
            logger.warning("Minimum interval between posts not met")
            return False
            
        # Check hourly limit
        if self.hourly_posts >= self.limits['posts_per_hour']:
            logger.warning("Hourly post limit reached")
            return False
            
        # Check daily limit
        if self.daily_posts >= self.limits['posts_per_day']:
            logger.warning("Daily post limit reached")
            return False
            
        return True
    
    def can_make_request(self) -> bool:
        """Alias for can_post() for API consistency"""
        return self.can_post()
        
    def record_post(self):
        """Record a new post"""
        now = datetime.utcnow()
        self.post_history.append(now)
        self.hourly_posts += 1
        self.daily_posts += 1
        
    def record_request(self):
        """Alias for record_post() for API consistency"""
        self.record_post()
        
    def _update_counters(self, now: datetime):
        """Update hourly and daily post counters"""
        # Reset hourly counter if an hour has passed
        if (now - self.last_reset).total_seconds() > 3600:
            self.hourly_posts = 0
            self.last_reset = now
            
        # Reset daily counter if a day has passed
        if (now - self.last_reset).total_seconds() > 86400:
            self.daily_posts = 0
            
    def get_wait_time(self) -> int:
        """Get wait time in seconds until next post is allowed"""
        if not self.post_history:
            return 0
            
        now = datetime.utcnow()
        last_post_time = self.post_history[-1]
        time_since_last = (now - last_post_time).total_seconds()
        
        return max(0, self.limits['minimum_interval'] - time_since_last) 