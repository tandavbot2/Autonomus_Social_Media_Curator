import os
import logging
from typing import List, Dict
from crewai import Agent, LLM
from .tools.news_tools import (
    NewsGatherer,
    RSSFeedReader,
    TrendAnalyzer,
    ArticleExtractor
)

from .tools.content_tools import (
    ContentGenerator,
    HashtagAnalyzer,
    EngagementPredictor,
    ContentTools
)

from .tools.safety_tools import (
    SafetyChecker,
    DuplicateDetector,
    ComplianceChecker,
    RateLimiter
)

from .tools.database_tools import (
    DatabaseWriter,
    DatabaseReader,
    DatabaseAnalyzer,
    DatabaseTools
)

from .tools.content_quality import (
    ContentCredibilityEvaluatorTool,
    ContentQualityRulesTool,
    ContentEnhancementTool
)

from .database.db_manager import DatabaseManager

from .config.feeds import get_feeds
from .config.llm_config import get_llm

logger = logging.getLogger(__name__)

def get_database_manager():
    """Get database manager agent"""
    return Agent(
        name='Database Manager',
        role='Database Administrator',
        goal='Ensure database operations are working correctly',
        backstory='Expert in managing and maintaining database systems',
        tools=[DatabaseTools()],
        llm=get_llm(),
        verbose=True
    )

def get_content_curator():
    """Get content curator agent"""
    return Agent(
        name='Content Curator',
        role='Content Curator',
        goal='Find and curate relevant content',
        backstory='Expert in content curation and analysis',
        tools=[ContentTools()],
        llm=get_llm(),
        verbose=True
    )

def get_content_creator():
    """Get content creator agent"""
    return Agent(
        name='Content Creator',
        role='Content Creator',
        goal='Create engaging social media content',
        backstory='Expert in creating viral social media content',
        tools=[ContentTools()],
        llm=get_llm(),
        verbose=True
    )

def create_content_curator() -> Agent:
    """Create content curator agent"""
    return Agent(
        role="Content Curator",
        goal="Curate and analyze content for social media posts",
        backstory="""You are an expert content curator with deep knowledge of 
        social media trends and audience engagement. You specialize in AI, 
        technology, and startup news.""",
        tools=[
            NewsGatherer(),
            RSSFeedReader(),
            TrendAnalyzer(),
            ArticleExtractor()
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'rss_feeds': get_feeds(['tech', 'ai']),
            'content_focus': ['AI', 'Technology', 'Innovation'],
            'target_audience': 'Tech professionals and enthusiasts'
        }
    )

def create_safety_agent() -> Agent:
    """Create safety agent"""
    return Agent(
        role="Safety Manager",
        goal="Ensure content safety, compliance, and prevent duplicates",
        backstory="""You are a diligent safety manager with expertise in 
        content moderation and platform compliance.""",
        tools=[
            SafetyChecker(),
            DuplicateDetector(),
            ComplianceChecker(),
            RateLimiter(),
            ContentQualityRulesTool()
        ],
        llm=get_llm(),
        verbose=True
    )

def create_database_agent() -> Agent:
    """Create database management agent"""
    return Agent(
        role="Database Manager",
        goal="Manage and provide access to all stored data for content curation and posting",
        backstory="""You are an expert database manager with deep knowledge of data storage,
        retrieval, and analysis. You maintain the system's historical data and provide insights
        for decision making. Your responsibilities include:
        - Storing content sources and generated content
        - Tracking post history and performance
        - Providing data for duplicate detection
        - Analyzing posting patterns and performance
        - Managing safety logs and compliance records""",
        tools=[
            DatabaseWriter(),
            DatabaseReader(),
            DatabaseAnalyzer()
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'data_types': {
                'content_sources': ['url', 'title', 'source_type', 'category'],
                'posts': ['platform', 'content', 'status', 'metrics'],
                'safety_logs': ['check_type', 'status', 'issues'],
                'metrics': ['likes', 'comments', 'shares', 'engagement_rate']
            },
            'storage_rules': {
                'content': 'Store all content with source attribution',
                'posts': 'Track full posting lifecycle',
                'metrics': 'Update performance data hourly',
                'safety': 'Log all safety checks and issues'
            }
        }
    )

def create_content_quality_agent() -> Agent:
    """Create content quality agent"""
    return Agent(
        role="Content Quality Manager",
        goal="Ensure all content meets high quality standards for credibility and transparency",
        backstory="""You are an expert in content quality with a background in journalism
        and editorial standards. Your job is to evaluate content for credibility,
        transparency, and compliance with quality standards. You ensure all posts
        clearly distinguish between facts and opinions, properly attribute sources,
        and maintain appropriate disclosure of knowledge level.""",
        tools=[
            ContentCredibilityEvaluatorTool(),
            ContentQualityRulesTool(),
            ContentEnhancementTool()
        ],
        llm=get_llm(),
        verbose=True,
        context={
            'quality_standards': {
                'tech_news': 'Must have source attribution, factual accuracy, and balanced perspective',
                'product_review': 'Must disclose experience level and provide balanced pros/cons',
                'opinion': 'Must clearly label opinions and provide reasoning'
            },
            'disclosure_requirements': {
                'experience_level': 'Always disclose level of experience with technologies discussed',
                'source_attribution': 'Always cite original sources for news and factual claims',
                'opinion_labeling': 'Clearly distinguish between factual claims and opinions'
            }
        }
    )

def create_posting_agent() -> Agent:
    """Create posting manager agent"""
    db_manager = DatabaseManager()
    # Change session to Session
    db_session = db_manager.Session()  # Create a session instance
    
    return Agent(
        role="Posting Manager",
        goal="Manage and optimize social media posts",
        backstory="""You are an expert social media manager with deep 
        understanding of platform-specific requirements and optimal posting strategies.""",
        tools=[
            ContentGenerator(),
            HashtagAnalyzer(),
            EngagementPredictor(),
            ContentCredibilityEvaluatorTool(),
            ContentEnhancementTool()
        ],
        llm=get_llm(),
        verbose=True
    )

def create_agents() -> List[Agent]:
    """Create all agents"""
    return [
        get_database_manager(),
        get_content_curator(),
        get_content_creator(),
        create_safety_agent(),
        create_database_agent(),
        create_posting_agent(),
        create_content_quality_agent()
    ] 