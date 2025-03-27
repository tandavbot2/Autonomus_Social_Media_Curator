from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, desc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, ContentSource, PostHistory, ContentMetrics, SafetyLog, Post
import os
import hashlib
import json
import sqlite3

logger = logging.getLogger(__name__)

class DatabaseManager:
    # Define schema information for each model
    CONTENT_SOURCE_FIELDS = {
        'required': ['source_type', 'category', 'content_hash'],
        'optional': ['url', 'title', 'created_at', 'processed_at'],
        'defaults': {
            'created_at': datetime.utcnow,
            'source_type': 'generated'
        }
    }
    
    POST_HISTORY_FIELDS = {
        'required': ['platform', 'content'],
        'optional': ['source_id', 'content_hash', 'post_id', 'posted_at', 
                    'scheduled_for', 'status', 'created_at', 'updated_at', 
                    'error_message'],
        'defaults': {
            'status': 'pending',
            'created_at': datetime.utcnow
        },
        'valid_platforms': ['twitter', 'linkedin', 'reddit', 'dev.to', 'mastodon', 'threads'],
        'valid_statuses': ['pending', 'generated', 'scheduled', 'posted', 'failed']
    }
    
    CONTENT_METRICS_FIELDS = {
        'required': ['post_id'],
        'optional': ['likes', 'comments', 'shares', 'views', 'clicks',
                    'engagement_rate', 'performance_score', 'platform_metrics',
                    'first_tracked', 'last_updated', 'metrics_history'],
        'defaults': {
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'views': 0,
            'clicks': 0,
            'first_tracked': datetime.utcnow
        }
    }

    # Add index definitions
    INDEXES = {
        'content_metrics': [
            ('post_id', 'post_id_idx'),
            ('first_tracked', 'metrics_time_idx')
        ],
        'safety_logs': [
            ('post_id', 'safety_post_idx'),
            ('checked_at', 'safety_time_idx')
        ]
    }

    def __init__(self, database_url=None):
        """Initialize database manager"""
        self.db_path = database_url or os.getenv('DATABASE_URL')
        self.engine = create_engine(
            self.db_path,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800
        )
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()  # Create default session
        
        # Initialize database
        self._initialize_db()
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Create indexes
        self._create_indexes()
        
        logger.info("Database manager initialized successfully")

    def _initialize_db(self):
        """Initialize database with optimized settings"""
        self.engine = create_engine(
            self.db_path,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
        
        # Set session factory
        self.Session = sessionmaker(bind=self.engine)

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        if isinstance(content, (dict, list)):
            content = json.dumps(content, sort_keys=True)
        return hashlib.md5(str(content).encode()).hexdigest()

    def _validate_and_prepare_data(self, data: Dict, model_fields: Dict) -> Dict:
        """Validate and prepare data according to model schema"""
        # Check required fields
        missing_fields = [field for field in model_fields['required'] 
                         if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Filter valid fields
        valid_fields = model_fields['required'] + model_fields['optional']
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Apply defaults for missing optional fields
        for field, default_value in model_fields['defaults'].items():
            if field not in filtered_data or filtered_data[field] is None:
                filtered_data[field] = default_value() if callable(default_value) else default_value
        
        return filtered_data

    def add_content_source(self, data: Dict) -> Optional[int]:
        """Add a new content source"""
        try:
            # Validate required fields
            for field in self.CONTENT_SOURCE_FIELDS['required']:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Apply defaults
            filtered_data = {}
            for field in self.CONTENT_SOURCE_FIELDS['required'] + self.CONTENT_SOURCE_FIELDS['optional']:
                if field in data:
                    filtered_data[field] = data[field]
                elif field in self.CONTENT_SOURCE_FIELDS['defaults']:
                    default = self.CONTENT_SOURCE_FIELDS['defaults'][field]
                    filtered_data[field] = default() if callable(default) else default
            
            # Add content source
            with self.session as session:
                try:
                    new_source = ContentSource(**filtered_data)
                    session.add(new_source)
                    session.commit()
                    return new_source.id
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error adding content source: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Error adding content source: {str(e)}")
            return None

    def create_post(self, post_data: Dict) -> Optional[PostHistory]:
        """Create new post record"""
        try:
            # Validate platform
            platform = str(post_data.get('platform', '')).lower()
            if platform not in self.POST_HISTORY_FIELDS['valid_platforms']:
                raise ValueError(f"Invalid platform. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_platforms'])}")
            
            # Validate status if provided
            if 'status' in post_data:
                status = str(post_data['status']).lower()
                if status not in self.POST_HISTORY_FIELDS['valid_statuses']:
                    raise ValueError(f"Invalid status. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_statuses'])}")
            
            # Prepare and validate data
            filtered_data = self._validate_and_prepare_data(post_data, self.POST_HISTORY_FIELDS)
            
            # Generate content hash if not provided
            if 'content_hash' not in filtered_data:
                filtered_data['content_hash'] = self._generate_content_hash(filtered_data['content'])
            
            # Create and validate the post
            post = PostHistory(**filtered_data)
            self.session.add(post)
            self.session.flush()  # Get the ID without committing
            
            # Verify the post was created
            if not post.id:
                raise ValueError("Post was not created properly")
            
            # Commit the transaction
            self.session.commit()
            logger.info(f"Created post with ID: {post.id}")
            
            return post
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating post: {str(e)}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            self.session.rollback()
            return None

    def update_post_status(self, post_id: int, status: str, error_message: Optional[str] = None) -> bool:
        """Update post status and error message"""
        try:
            post = self.session.query(PostHistory).get(post_id)
            if not post:
                return False
            
            post.status = status
            if error_message:
                post.error_message = error_message
            if status == 'posted':
                post.posted_at = datetime.utcnow()
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating post status: {str(e)}")
            self.session.rollback()
            return False

    def update_metrics(self, post_id: int, metrics_data: Dict) -> bool:
        """Update post metrics"""
        try:
            # Prepare and validate data
            filtered_data = self._validate_and_prepare_data(
                {'post_id': post_id, **metrics_data},
                self.CONTENT_METRICS_FIELDS
            )
            
            metrics = self.session.query(ContentMetrics).filter(
                ContentMetrics.post_id == post_id
            ).first()
            
            if not metrics:
                metrics = ContentMetrics(**filtered_data)
                self.session.add(metrics)
            else:
                # Update existing metrics
                for key, value in filtered_data.items():
                    if hasattr(metrics, key):
                        setattr(metrics, key, value)
            
            # Calculate engagement rate
            total_engagement = sum([
                metrics.likes or 0,
                metrics.comments or 0,
                metrics.shares or 0
            ])
            if metrics.views:
                metrics.engagement_rate = total_engagement / metrics.views
            
            # Store historical data
            current_metrics = metrics.metrics_history or []
            current_metrics.append({
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': metrics_data
            })
            metrics.metrics_history = current_metrics
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            self.session.rollback()
            return False

    def add_safety_log(self, safety_data: Dict) -> Optional[SafetyLog]:
        """Add safety check log"""
        try:
            log = SafetyLog(**safety_data)
            self.session.add(log)
            self.session.commit()
            return log
        except Exception as e:
            logger.error(f"Error adding safety log: {str(e)}")
            self.session.rollback()
            return None

    def get_post_history(self, platform: Optional[str] = None, 
                        status: Optional[str] = None,
                        days: Optional[int] = 7,
                        include_metrics: bool = True) -> List[Dict]:
        """Get post history with optional filters and metrics"""
        try:
            query = self.session.query(PostHistory)
            
            if platform:
                platform = platform.lower()
                if platform not in self.POST_HISTORY_FIELDS['valid_platforms']:
                    raise ValueError(f"Invalid platform. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_platforms'])}")
                query = query.filter(PostHistory.platform == platform)
            
            if status:
                status = status.lower()
                if status not in self.POST_HISTORY_FIELDS['valid_statuses']:
                    raise ValueError(f"Invalid status. Must be one of: {', '.join(self.POST_HISTORY_FIELDS['valid_statuses'])}")
                query = query.filter(PostHistory.status == status)
            
            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(PostHistory.created_at >= cutoff)
            
            posts = query.order_by(desc(PostHistory.created_at)).all()
            
            result = []
            for post in posts:
                post_data = {
                    'id': post.id,
                    'platform': post.platform,
                    'content': post.content,
                    'status': post.status,
                    'error_message': post.error_message,
                    'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                    'scheduled_for': post.scheduled_for.isoformat() if post.scheduled_for else None,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                }
                
                if include_metrics and post.metrics:
                    metrics = post.metrics[0] if post.metrics else None
                    if metrics:
                        post_data['metrics'] = {
                            'likes': metrics.likes,
                            'comments': metrics.comments,
                            'shares': metrics.shares,
                            'views': metrics.views,
                            'engagement_rate': metrics.engagement_rate,
                            'platform_metrics': metrics.platform_metrics
                        }
                
                result.append(post_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting post history: {str(e)}")
            return []

    def get_post_performance(self, post_id: int) -> Optional[Dict]:
        """Get comprehensive post performance data"""
        try:
            post = self.session.query(PostHistory).get(post_id)
            if not post:
                return None
            
            metrics = self.session.query(ContentMetrics).filter(
                ContentMetrics.post_id == post_id
            ).first()
            
            if not metrics:
                return {
                    'post_id': post_id,
                    'platform': post.platform,
                    'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                    'current_metrics': {
                        'likes': 0,
                        'comments': 0,
                        'shares': 0,
                        'views': 0,
                        'engagement_rate': 0
                    },
                    'platform_metrics': {},
                    'metrics_history': [],
                    'performance_score': 0
                }
                
            return {
                'post_id': post_id,
                'platform': post.platform,
                'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                'current_metrics': {
                    'likes': metrics.likes or 0,
                    'comments': metrics.comments or 0,
                    'shares': metrics.shares or 0,
                    'views': metrics.views or 0,
                    'engagement_rate': metrics.engagement_rate or 0
                },
                'platform_metrics': metrics.platform_metrics or {},
                'metrics_history': metrics.metrics_history or [],
                'performance_score': metrics.performance_score or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting post performance: {str(e)}")
            return None

    def get_platform_analytics(self, platform: str, 
                             start_date: datetime,
                             end_date: datetime) -> Dict:
        """Get platform-specific analytics"""
        try:
            posts = self.session.query(PostHistory).filter(
                PostHistory.platform == platform,
                PostHistory.posted_at.between(start_date, end_date)
            ).all()
            
            total_engagement = {
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'views': 0
            }
            
            post_metrics = []
            for post in posts:
                metrics = self.session.query(ContentMetrics).filter(
                    ContentMetrics.post_id == post.id
                ).first()
                
                if metrics:
                    post_metrics.append({
                        'post_id': post.id,
                        'content': post.content,
                        'posted_at': post.posted_at.isoformat() if post.posted_at else None,
                        'metrics': {
                            'likes': metrics.likes or 0,
                            'comments': metrics.comments or 0,
                            'shares': metrics.shares or 0,
                            'views': metrics.views or 0,
                            'engagement_rate': metrics.engagement_rate or 0
                        }
                    })
                    
                    # Aggregate totals
                    for key in total_engagement:
                        total_engagement[key] += getattr(metrics, key, 0) or 0
            
            return {
                'platform': platform,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_posts': len(posts),
                'total_engagement': total_engagement,
                'average_engagement_rate': sum(p['metrics']['engagement_rate'] for p in post_metrics) / len(post_metrics) if post_metrics else 0,
                'posts': post_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting platform analytics: {str(e)}")
            return {} 

    def _create_indexes(self):
        """Create database indexes"""
        try:
            with self.session as session:
                # Create indexes for content_metrics
                for column, index_name in self.INDEXES['content_metrics']:
                    session.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON content_metrics ({column})"
                    ))
                
                # Create indexes for safety_logs
                for column, index_name in self.INDEXES['safety_logs']:
                    session.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON safety_logs ({column})"
                    ))
                
                session.commit()
                
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database indexes: {str(e)}")
            raise

    def _verify_database(self):
        """Verify database setup and report status"""
        try:
            # Check tables
            tables = {
                'content_sources': ContentSource,
                'post_history': PostHistory,
                'content_metrics': ContentMetrics,
                'safety_logs': SafetyLog
            }
            
            status = {
                'tables': {},
                'indexes': {},
                'counts': {}
            }
            
            # Check each table
            for table_name, model in tables.items():
                try:
                    count = self.session.query(model).count()
                    status['tables'][table_name] = 'exists'
                    status['counts'][table_name] = count
                except Exception as table_error:
                    status['tables'][table_name] = f'error: {str(table_error)}'
            
            # Check indexes
            for table, indexes in self.INDEXES.items():
                status['indexes'][table] = []
                for _, index_name in indexes:
                    try:
                        result = self.session.execute(text(
                            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
                        )).fetchone()
                        status['indexes'][table].append({
                            'name': index_name,
                            'exists': bool(result)
                        })
                    except Exception as idx_error:
                        logger.error(f"Error checking index {index_name}: {str(idx_error)}")
            
            logger.info("Database verification completed:")
            logger.info(f"Tables status: {status['tables']}")
            logger.info(f"Record counts: {status['counts']}")
            logger.info(f"Indexes status: {status['indexes']}")
            
            return status
            
        except Exception as e:
            logger.error(f"Error verifying database: {str(e)}")
            return None 

    def close(self):
        """Close database connections"""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'engine'):
            self.engine.dispose()

    def is_duplicate_content(self, content: str, hours: int = 24) -> bool:
        """
        Check if similar content was posted within specified time period
        
        Args:
            content: The content or URL to check
            hours: Time window in hours to check for duplicates (default: 24)
            
        Returns:
            bool: True if duplicate found, False otherwise
        """
        session = self.Session()
        try:
            # Get posts from specified time period
            recent_posts = session.query(Post).filter(
                Post.created_at >= datetime.utcnow() - timedelta(hours=hours)
            ).all()
            
            # Compare content similarity
            content_hash = hashlib.md5(content.encode()).hexdigest()
            for post in recent_posts:
                post_hash = hashlib.md5(post.content.encode()).hexdigest()
                if post_hash == content_hash:
                    return True
                    
            # Also check URLs in metadata
            recent_platform_posts = session.query(PostHistory).filter(
                PostHistory.posted_at >= datetime.utcnow() - timedelta(hours=hours)
            ).all()
            
            for platform_post in recent_platform_posts:
                try:
                    if platform_post.metadata:
                        metadata = json.loads(platform_post.metadata)
                        post_url = metadata.get('url', '')
                        if post_url and post_url == content:
                            return True
                except:
                    pass
                    
            return False
        finally:
            session.close()

    def is_duplicate_post_on_platform(self, platform: str, content: str = None, 
                                  title: str = None, url: str = None, hours: int = 24) -> bool:
        """
        Check if similar content was posted to a specific platform within specified time period
        
        Args:
            platform: Platform name to check
            content: The post content to check
            title: The post title to check
            url: The URL to check
            hours: Time window in hours to check for duplicates (default: 24)
            
        Returns:
            bool: True if duplicate found, False otherwise
        """
        if not any([content, title, url]):
            return False
            
        session = self.Session()
        try:
            # Get platform posts from specified time period
            query = session.query(PostHistory).filter(
                PostHistory.platform == platform,
                PostHistory.posted_at >= datetime.utcnow() - timedelta(hours=hours)
            )
            
            recent_platform_posts = query.all()
            
            # Check for duplicate titles if title provided
            if title:
                for post in recent_platform_posts:
                    try:
                        if post.metadata:
                            metadata = json.loads(post.metadata)
                            post_title = metadata.get('title', '')
                            # Check for exact match or high similarity
                            if post_title and (post_title == title or self._title_similarity(post_title, title) > 0.8):
                                logger.debug(f"Found duplicate title on {platform}: {title}")
                                return True
                    except Exception as e:
                        logger.error(f"Error checking title similarity: {str(e)}")
            
            # Check for duplicate URLs if url provided
            if url:
                for post in recent_platform_posts:
                    try:
                        if post.metadata:
                            metadata = json.loads(post.metadata)
                            post_url = metadata.get('url', '')
                            if post_url and post_url == url:
                                logger.debug(f"Found duplicate URL on {platform}: {url}")
                                return True
                    except Exception as e:
                        logger.error(f"Error checking URL similarity: {str(e)}")
            
            # Check for duplicate content if content provided
            if content:
                for post in recent_platform_posts:
                    if post.original_content:
                        # Check for exact match or high similarity
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                        post_hash = hashlib.md5(post.original_content.encode()).hexdigest()
                        if post_hash == content_hash:
                            logger.debug(f"Found duplicate content on {platform}")
                            return True
            
            return False
        finally:
            session.close()
            
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (0-1 scale)"""
        # Simple similarity based on character overlap
        title1 = title1.lower()
        title2 = title2.lower()
        
        # Remove common filler words for better comparison
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        for word in stop_words:
            title1 = title1.replace(f" {word} ", " ")
            title2 = title2.replace(f" {word} ", " ")
        
        # If either string is empty after processing, return 0
        if not title1 or not title2:
            return 0
            
        # Calculate Jaccard similarity
        set1 = set(title1.split())
        set2 = set(title2.split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0
            
        return intersection / union

    def store_post(self, content: str, source_url: str = None):
        """Store post in database"""
        session = self.Session()
        try:
            post = Post(content=content, source_url=source_url)
            session.add(post)
            session.commit()
        finally:
            session.close() 