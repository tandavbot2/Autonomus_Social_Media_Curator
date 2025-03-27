
```markdown
# Autonomous Social Media Curator - Project Overview

## Project Summary
This project is an AI-powered autonomous social media content curation and posting system built with Python. It uses the CrewAI framework to coordinate multiple specialized AI agents that work together to discover, analyze, enhance, and post content to various social media platforms.

## Architecture & Components

### Core System Architecture
- **Agent-Based Architecture**: Uses CrewAI to organize multiple specialized AI agents
- **Modular Design**: Separate modules for platforms, tools, content strategies, and database operations
- **Event-Driven Workflow**: Content flows through multiple processing stages before posting

### Key Components
1. **AI Agents System**
   - 5 specialized agents (News Collector, Content Analyzer, Content Creator, Posting Manager, Safety Monitor)
   - Each agent has specific tools and responsibilities
   - Agents communicate via CrewAI task framework

2. **Platform Management**
   - Abstract `SocialMediaPlatform` base class
   - Concrete implementations for Dev.to, Mastodon, and Reddit
   - `PlatformManager` for centralized platform handling
   - Platform factory pattern for dynamic platform instantiation

3. **Content Tools**
   - News gathering from multiple sources
   - Content analysis and enhancement using LLMs
   - Safety checking and duplicate detection
   - Platform-specific formatting

4. **Database Integration**
   - SQLAlchemy ORM for database operations
   - Models for post history, content sources, and metrics
   - Transaction management with error handling

## Technology Stack

- **Core Framework**: CrewAI for agent orchestration
- **AI/LLM**: DeepSeek for content enhancement, Azure OpenAI for agents
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **External APIs**:
  - News APIs for content sourcing
  - Platform APIs: Dev.to, Mastodon, Reddit
- **Language**: Python 3.9+

## Data Flow & Processes

### Content Collection & Enhancement Flow
1. Gather news from NewsAPI and RSS feeds
2. Filter by relevance to target topics (tech, AI, etc.)
3. Process full articles with DeepSeek LLM
4. Extract key insights and technical concepts
5. Enhance content quality and readability
6. Store processed content in database

### Content Posting Flow
1. Select target platforms based on configuration
2. Format content specifically for each platform
3. Apply safety checks and duplicate detection
4. Manage rate limiting and scheduling
5. Post to each platform using respective APIs
6. Track performance metrics and store results

### Safety & Compliance
- Content moderation using AI-powered tools
- Platform-specific compliance rules
- Rate limiting to prevent API abuse
- Automatic retries with exponential backoff

## Key Files & Structure

```
social_media_bot/
├── agents.py           # AI agent definitions and configuration
├── models/platform.py  # Platform enumeration and base types
├── platforms/          # Platform-specific implementations
│   ├── base.py         # Abstract base class for all platforms
│   ├── devto.py        # Dev.to implementation
│   ├── mastodon.py     # Mastodon implementation
│   ├── reddit.py       # Reddit implementation
│   └── manager.py      # Platform orchestration
├── tools/              # Specialized tools used by agents
│   ├── content_tools.py        # Content creation and formatting
│   ├── news_tools.py           # News gathering
│   ├── safety_tools.py         # Content safety and compliance
│   ├── database_tools.py       # Database operations
│   └── content_quality.py      # Content enhancement
├── database/           # Database integration
├── config/             # Configuration files
│   ├── platforms.py    # Platform settings
│   ├── feeds.py        # News feed configuration
│   └── llm_config.py   # LLM configuration
├── utils/              # Helper utilities
├── main.py             # Main application entry point
└── multi_platform_post.py  # Direct posting utility
```

## Key Features

1. **Autonomous Operation**
   - Fully automatic content discovery, curation, and posting
   - Configurable platforms and content strategies
   - Scheduling and rate limiting

2. **Content Enhancement**
   - Transforms raw news into engaging social media content
   - Platform-specific formatting and optimization
   - Adds value beyond simple reposting

3. **Safety & Reliability**
   - Content moderation and safety checks
   - Error handling with automatic retries
   - Transaction management for database operations

4. **Extensibility**
   - Easily add new platforms via common interface
   - Plug in different content strategies
   - Configurable LLM providers

## Workflow Example

### Tech News Posting Workflow
1. **Content Discovery**: System fetches latest tech news from NewsAPI
2. **Content Processing**:
   - Extracts full article content
   - Enhances with DeepSeek LLM to add insights and improve quality
   - Formats for each target platform
3. **Safety Check**:
   - Verifies content doesn't violate platform policies
   - Checks for duplicates against previously posted content
   - Ensures within rate limits
4. **Platform Posting**:
   - Authenticates with each enabled platform
   - Posts content with appropriate formatting
   - Captures results and metrics
5. **Tracking**:
   - Records post history in database
   - Logs operations and errors

## Environment & Configuration

- **Environment Variables**:
  - API keys for news and LLM services
  - Platform credentials
  - Feature flags for enabling/disabling platforms
  - Database configuration

- **Configuration Files**:
  - Platform configuration in `config/platforms.py`
  - News feed settings in `config/feeds.py`
  - LLM settings in `config/llm_config.py`

## Command Line Interface

The system provides several CLI commands:

```bash
# Main application
python social_media_bot/main.py [--strategy default|tech_news] [--platforms platform1,platform2] [--force]

# Post to multiple platforms
python social_media_bot/multi_platform_post.py [--platforms dev.to,mastodon,reddit] [--no-enhance]

# Post enhanced blog to Dev.to
python post_dev_blog.py

# Database utilities
python test_db.py
python cleanup_db.py
```

## Implementation Notes

- The system uses a factory pattern for platform creation
- Content quality enhancement uses LLM with specific prompts
- Database operations are wrapped in transactions
- All platform interactions include error handling and retries
- The project follows a clean architecture with separation of concerns

## Integration Points

- **News API Integration**: Fetches latest articles based on topics
- **LLM Integration**: Uses DeepSeek for content enhancement
- **Platform APIs**:
  - Dev.to API for developer-focused content
  - Mastodon API for federated social network posts
  - Reddit API for subreddit submissions
- **Database Integration**: SQLAlchemy ORM for data persistence
```

