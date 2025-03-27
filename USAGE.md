# Unified Content Posting System - Usage Guide

## Overview

The Social Media Bot now includes a unified content posting system that allows you to post the same content to multiple platforms with a single command while maintaining platform-specific formatting.

## News API Configuration

The system now supports multiple news APIs to provide redundancy and increase the daily request quota:

1. **NewsAPI.org** (Primary)
   - Free tier: 100 requests per day
   - Configure with `NEWS_API_KEY` in `.env`

2. **TheNewsAPI.com** (Secondary)
   - Free tier: 100 requests per day (3 articles per request)
   - Configure with `THE_NEWS_API_KEY` in `.env`

3. **NewsData.io** (Tertiary)
   - Free tier: 200 requests per day
   - Configure with `NEWSDATA_API_KEY` in `.env`

The system will automatically try these APIs in sequence:
1. First attempts NewsAPI.org
2. If rate-limited or no results, tries TheNewsAPI.com
3. If still no results, tries NewsData.io
4. If all APIs fail, uses cached content

This effectively triples your daily quota and provides excellent redundancy to ensure you always have fresh content.

### Content Filtering

The system now implements strict filtering to ensure only high-quality tech news (not blog posts):

- Filters for reputable tech news sources like TechCrunch, Wired, The Verge, etc.
- Explicitly blocks content from blogging platforms like Medium
- Uses domain filtering directly in API calls to prioritize quality sources
- Ensures sufficient content length and relevance to technology topics

This ensures your social media accounts only post professional tech news articles, not personal blog content.

## Duplicate Post Detection

The system now automatically detects and prevents duplicate posts:

- Checks if the same article URL has been posted before
- Prevents posting the same content to the same platform within 24 hours
- Tracks all posted content in the database for future reference

This ensures your social media accounts remain fresh and engaging without repetitive content.

## Commands

### Post to All Enabled Platforms

```bash
python -m social_media_bot.main --strategy tech_news
```

This command will:
1. Fetch tech news from reputable sources using available news APIs
2. Check for duplicate content to avoid reposting
3. Validate that the content is appropriate for all platforms
4. Format the content specifically for each enabled platform
5. Post to all enabled platforms at once

### Post to Specific Platforms

```bash
python -m social_media_bot.main --strategy tech_news --platforms reddit,devto,mastodon
```

This allows you to specify which platforms to post to (comma-separated, no spaces).

### Force Content Generation

```bash
python -m social_media_bot.main --strategy tech_news --force
```

This forces content generation even when APIs are rate-limited by using cached content when necessary.

### Post Only to Reddit (Original Functionality)

```bash
python -m social_media_bot.post_tech_news
```

This preserves the original functionality, posting only to Reddit with r/technews-specific formatting.

## Platform-Specific Formatting

The system automatically formats content appropriately for each platform:

- **Reddit**: Formats posts for r/technews with appropriate flairs and link attribution
- **Dev.to**: Creates properly formatted articles with:
  - Clean title at the top
  - Organized hashtags on a single line
  - Original article content
  - Personalized commentary that varies based on the article topic
  - Engaging questions to encourage reader interaction
  - Proper attribution with clickable link to the original source
- **Mastodon**: Creates concise posts that meet character limits
- **Threads**: Creates mobile-friendly posts with appropriate formatting

## Enabling/Disabling Platforms

Platforms can be enabled or disabled in your `.env` file:

```
DEVTO_ENABLED=true
MASTODON_ENABLED=true
REDDIT_ENABLED=true
THREADS_ENABLED=true
```

## Extending the System

To add a new content strategy:

1. Create a new class that inherits from `ContentStrategyBase` in `social_media_bot/tools/content_strategies.py`
2. Implement the required methods: `generate_content()`, `validate_content()`, and `format_for_platform()`
3. Add your new strategy to the main CLI argument choices

Example:

```python
class MyCustomStrategy(ContentStrategyBase):
    def __init__(self, platform_manager, db_manager):
        super().__init__(platform_manager, db_manager)
        # Your initialization code here
        
    def generate_content(self):
        # Your custom content generation logic
        # Returns a list of content items
        pass
        
    def validate_content(self, content):
        # Your custom validation logic
        pass
        
    def format_for_platform(self, content, platform):
        # Your custom formatting logic for each platform
        pass
```

## Troubleshooting

- Check logs for detailed error messages
- Ensure all required API keys are in your `.env` file
- Verify that platforms are properly enabled
- Check your connection to each platform's API
- If duplicate content is flagged incorrectly, you can clear the post history database
- If news APIs are rate-limited, the system will use cached content or fallback articles 