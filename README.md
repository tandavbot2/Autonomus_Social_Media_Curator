# Autonomous Social Media Content Curator

An AI-powered system for autonomous social media content curation and posting using CrewAI. All made for hobby and practice, any improvements will be appriciated!

## Current Implementation Status

### Implemented Components
- Core system architecture with CrewAI integration
- Azure OpenAI integration for AI processing
- Database integration with SQLAlchemy
- Agent system with five specialized agents:
  - News Collector
  - Content Analyzer
  - Content Creator
  - Posting Manager
  - Safety Monitor
- Task definitions for each agent
- Basic logging and error handling
- Environment configuration setup
- Social media posting tools for:
  * Dev.to integration
  * Mastodon integration
  * Reddit integration
- Content validation and safety checks
- Database schema and models
- Error handling system

### Development Status

1. **Tool Development** (Current Progress):
   - News gathering tools (NewsAPI + RSS integration) - Implemented
   - Content analysis tools - Implemented
   - Social media posting tools - Implemented for:
     * Dev.to posting with API
     * Mastodon API integration
     * Reddit API integration
   - Safety check tools - Implemented:
     * Content validation
     * Rate limiting
     * Session validation

2. **API Integrations**:
   - Dev.to API implementation - Fully functional
   - Mastodon API implementation - Fully functional
   - Reddit API implementation - Fully functional
   - News API service setup - Implemented

3. **Data Storage** (Implemented):
   - Posting history tracking with SQLAlchemy
   - Performance metrics storage
   - Content source management
   - Safety logs and analytics
   - Database schema with models:
     * PostHistory
     * ContentMetrics
     * ContentSource
     * SafetyLog

4. **Safety Features**:
   - Content moderation implementation - Implemented
   - Duplicate detection system - Implemented
   - Rate limiting logic - Implemented
   - Session validation - Implemented
   - Error tracking - Implemented

5. **Dashboard & Monitoring**:
   - Real-time status dashboard - Planned
   - Performance metrics visualization - Planned
   - Error tracking interface - Basic Implementation
   - Logging system - Implemented

## Architecture

The system uses a microservices-based architecture with specialized AI agents:

1. **News Collector Agent**: Gathers and filters relevant news
2. **Content Analyzer Agent**: Evaluates content relevance and viral potential
3. **Content Creator Agent**: Generates platform-specific content
4. **Posting Manager Agent**: Handles scheduling and posting
5. **Safety Monitor Agent**: Ensures content safety and compliance

## Features

- Automated news collection from multiple sources
- Content analysis and virality prediction
- Platform-specific content generation (Dev.to, Mastodon, Reddit)
- Automated posting with optimal timing
- Content safety and compliance checking
- Performance tracking and analytics

## Tech Stack

- **Core Framework**: CrewAI
- **Language**: Python 3.9+
- **APIs**: 
  - NewsAPI for content collection
  - Dev.to API
  - Mastodon API
  - Reddit API
  - OpenAI API for content generation
- **Database**: SQLAlchemy with SQLite (can be configured for PostgreSQL)
- **Monitoring**: Built-in logging and dashboard

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .   
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Fill in your API keys and credentials

4. Run the system:
   ```bash
   python social_media_bot/main.py
   ```

## Configuration

Key configuration files:
- `.env`: API keys and credentials
- `config/`: Platform-specific settings
- `templates/`: Content templates

## Usage Commands

### Check Connected Platforms
To see which platforms are enabled and properly connected:

```bash
python -c "from social_media_bot.platforms.manager import PlatformManager; pm = PlatformManager(); print(pm.check_all_statuses())"
```

### Post to All Enabled Platforms
To post tech news to all enabled platforms:

```bash
python social_media_bot/multi_platform_post.py
```

### Post to Specific Platforms
To post to specific platforms only:

```bash
python social_media_bot/multi_platform_post.py --platforms dev.to,mastodon
```

Available platform options: `dev.to`, `mastodon`, `reddit`

### Post Without Content Enhancement
To post without AI enhancement of content:

```bash
python social_media_bot/multi_platform_post.py --no-enhance
```

### Post a Dev.to Blog
To create and post an enhanced blog to Dev.to:

```bash
python post_dev_blog.py
```

### Check Database Status
To verify database connectivity and structure:

```bash
python test_db.py
```

### Clean Database
To remove old records from database:

```bash
python cleanup_db.py
```

## Safety Features

- Content moderation filters
- Duplicate content detection
- Rate limiting
- Manual review option
- Emergency stop capability

## Monitoring

The system includes:
- Real-time logging
- Performance metrics
- Content engagement tracking
- Error monitoring
- API usage tracking

## License

MIT License 

## Workflow

The system operates through a coordinated sequence of specialized agents working together to curate, analyze, and post content. Here's the detailed workflow:

1. **Content Curation (Content Curator Agent)**
   - Gathers trending news using NewsAPI and RSS feeds
   - Focuses on AI, technology, and startup news
   - Uses tools:
     - `NewsGatherer`: Fetches articles from configured sources
     - `RSSFeedReader`: Monitors RSS feeds for fresh content
     - `TrendAnalyzer`: Evaluates content popularity and relevance
     - `ArticleExtractor`: Processes full article pages through Deepseek LLM to:
       * Extract main article content
       * Remove ads and irrelevant elements
       * Identify key points and insights
       * Summarize core message
       * Extract relevant quotes
       * Identify technical terms and concepts

2. **Safety Check (Safety Manager Agent)**
   - Reviews content for safety and compliance
   - Uses tools:
     - `SafetyChecker`: Scans for inappropriate content, hate speech, etc.
     - `DuplicateDetector`: Ensures content uniqueness
     - `ComplianceChecker`: Verifies platform policy compliance
     - `RateLimiter`: Manages posting frequency

3. **Content Generation & Optimization (Posting Manager Agent)**
   - Creates platform-specific content
   - Uses tools:
     - `ContentGenerator`: Creates tailored posts for each platform
     - `HashtagAnalyzer`: Suggests relevant hashtags
     - `EngagementPredictor`: Predicts potential engagement

### Detailed Process Flow

1. **Initial Content Discovery**
   - Content Curator monitors news sources and RSS feeds
   - Filters content based on relevance to AI and technology
   - For each relevant article:
     1. Fetches complete webpage content
     2. Sends to Deepseek LLM for intelligent extraction
     3. LLM processes and returns:
        * Clean article text
        * Key insights
        * Technical concepts
        * Important quotes
        * Summary
     4. Analyzes trends across processed articles
     5. Generates initial content ideas based on processed data

2. **Safety and Compliance Review**
   - Safety Manager checks content against:
     - Platform guidelines
     - Content policies
     - Duplicate detection
     - Rate limiting rules
   - Flags any issues for review

3. **Content Creation and Optimization**
   - For each platform (Dev.to, Mastodon, Reddit):
     - Generates platform-specific content
     - Optimizes for character limits
     - Adds relevant hashtags
     - Predicts engagement potential
     - Adjusts content based on predictions

4. **Posting Process**
   - Verifies authentication with platforms
   - Checks rate limits
   - Posts content with appropriate timing
   - Handles media uploads if included
   - Monitors post status

5. **Performance Tracking**
   - Monitors engagement metrics
   - Tracks:
     - Impressions
     - Likes/Reactions
     - Comments/Replies
     - Shares/Reposts
   - Stores performance data for future optimization

### Data Flow

1. **Input Sources**
   - NewsAPI articles
   - RSS feed content
   - Platform-specific trending topics
   - Historical performance data

2. **Processing Pipeline**
   - Content filtering and relevance scoring
   - Safety and compliance checks
   - Content generation and optimization
   - Platform-specific formatting

3. **Output Channels**
   - Dev.to posts
   - Mastodon posts
   - Reddit posts
   - Performance metrics
   - Analytics reports

### Error Handling

- Automatic retry for failed API calls
- Graceful degradation for rate limits
- Logging of all operations
- Error notifications for critical issues

### Optimization Loop

1. **Performance Analysis**
   - Tracks engagement metrics
   - Identifies successful content patterns
   - Analyzes timing impact

2. **Continuous Improvement**
   - Adjusts content strategy based on performance
   - Updates hashtag selection
   - Refines posting schedules
   - Improves content templates 

## Additional Features

### Database Integration
- SQLAlchemy ORM for database operations
- Transaction management and rollback support
- Data validation and integrity checks
- Performance optimization
- Relationship management between models

### Social Media Integration
1. **Dev.to Features**:
   - API key authentication
   - Article posting with tags
   - Metrics tracking
   - Error handling

2. **Mastodon Features**:
   - OAuth authentication
   - Post creation
   - Media attachment support
   - Error handling

3. **Reddit Features**:
   - OAuth authentication
   - Subreddit posting
   - Post formatting
   - Error handling

### Error Management
1. **Database Operations**:
   - Transaction management
   - Rollback on failure
   - Error logging
   - Data validation

2. **Social Media Posting**:
   - API error handling
   - Rate limit management
   - Authentication retry
   - Session validation

3. **Content Processing**:
   - Content validation
   - Format verification
   - Size limit checks
   - Character encoding

### Environment Setup
```bash
# Database Configuration
DATABASE_URL=your_database_url

# Dev.to Credentials
DEVTO_API_KEY=your_devto_api_key_here
DEVTO_ENABLED=true

# Mastodon Credentials
MASTODON_ACCESS_TOKEN=your_mastodon_access_token_here
MASTODON_API_BASE_URL=https://mastodon.social
MASTODON_ENABLED=true

# Reddit Credentials
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USERNAME=your_reddit_username_here
REDDIT_PASSWORD=your_reddit_password_here
REDDIT_USER_AGENT=YourApp/1.0.0
REDDIT_ENABLED=true
```

## Enhanced Dev.to Blog Posts

This project includes support for enhanced blog posts on Dev.to using the DeepSeek API. This feature transforms standard tech news articles into engaging, human-like blog posts that provide real value to readers.

### Features

- **Human-Like Content**: Creates blog posts that read naturally and don't appear AI-generated
- **Adds Value**: Transforms news snippets into insightful articles with analysis and perspective
- **Proper Formatting**: Maintains correct Dev.to formatting with appropriate tags
- **Engagement**: Includes thought-provoking questions to encourage reader interaction
- **Proper Attribution**: Always includes proper attribution to the original source

### Setup

1. Obtain a DeepSeek API key
2. Add it to your `.env` file as `DEEPSEEK_API_KEY`
3. (Optional) Configure the API URL with `DEEPSEEK_API_URL` if you need a different endpoint

### Usage

To post an enhanced blog to Dev.to:

```bash
python post_dev_blog.py
```

This will:
1. Fetch the latest tech news
2. Process it through DeepSeek to create an engaging blog post
3. Post it to your Dev.to account

If the DeepSeek API key is not available, the system will fall back to a simpler formatting method.

### Configuration

You can customize the blog post generation by modifying the prompts in `social_media_bot/services/deepseek_service.py`.
