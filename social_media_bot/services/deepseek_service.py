"""
DeepSeek API Service for content processing and enhancement.
"""
import os
import logging
import requests
import json
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

class DeepSeekService:
    """
    Service for processing content using DeepSeek API
    """
    
    def __init__(self):
        """Initialize the DeepSeek API service"""
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        logger.info("DeepSeek service initialized")
        
        if not self.api_key:
            logger.warning("DeepSeek API key not found. Some features will be limited.")
    
    def process_news_to_blog(self, news_content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a news article into a well-structured blog post using DeepSeek
        
        Args:
            news_content: Dictionary containing news article data
            
        Returns:
            Dictionary with processed blog content or None if processing failed
        """
        if not self.api_key:
            logger.warning("DeepSeek API key not provided, skipping processing")
            return None
            
        try:
            # Extract news content
            title = news_content.get('title', '')
            description = news_content.get('description', '')
            content = news_content.get('content', '')
            # Use fullContent if available (from article extractor)
            full_content = news_content.get('fullContent', content)
            url = news_content.get('url', '')
            source = news_content.get('source', {}).get('name', '') if isinstance(news_content.get('source'), dict) else news_content.get('source', '')
            authors = news_content.get('authors', [])
            keywords = news_content.get('keywords', [])
            
            # Use the most detailed content available
            article_text = full_content if full_content else (content if content else description)
            
            # Skip if not enough source content
            if not title or not article_text:
                logger.warning("Insufficient content for DeepSeek processing")
                return None
                
            # Determine article category for better prompting
            article_category = self._determine_article_category(title, article_text, keywords)
            logger.info(f"Determined article category: {article_category}")
            
            # Create system prompt based on article category
            system_prompt = self._create_system_prompt(article_category)
            
            # Create user prompt
            user_prompt = f"""
Transform this {article_category} article into an engaging, informative blog post for a developer/tech audience:

TITLE: {title}

SOURCE: {source}

AUTHORS: {', '.join(authors) if authors else 'Not specified'}

KEYWORDS: {', '.join(keywords) if keywords else 'Not specified'}

FULL ARTICLE TEXT:
{article_text[:4000]}  # Limit to first 4000 chars to avoid token limits

URL: {url}

The blog post should:
- Have a professional, conversational tone that sounds like it was written by a human expert
- Include insights and analysis relevant to the specific topic
- Be formatted properly with suitable headings, lists, and emphasis
- End with thoughtful questions to engage readers
- Include a source attribution: *Source: [{source}]({url})*

IMPORTANT:
1. DO NOT wrap your entire response in a markdown code block
2. Only use code blocks for actual code examples IF THEY ARE RELEVANT to this article
3. Don't create a generic template-filled post - be specific to this article's content
4. Maintain journalistic integrity - don't make up facts not present in the original
5. Format should match the article's content - technical articles can include technical details, but not every article needs code examples
"""

            # Prepare the API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # Log the API call (without sensitive data)
            logger.debug(f"Calling DeepSeek API for article: {title}")
            
            # Make the API request
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # Process the response
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the generated content
                if (response_data.get('choices') and
                    len(response_data['choices']) > 0 and
                    response_data['choices'][0].get('message') and
                    response_data['choices'][0]['message'].get('content')):
                    
                    processed_content = response_data['choices'][0]['message']['content']
                    
                    # Remove any wrapping markdown code blocks
                    processed_content = self._fix_markdown_formatting(processed_content)
                    
                    # Ensure source attribution is present
                    if f"*Source: [{source}]({url})*" not in processed_content and f"*Originally published on [{source}]({url})*" not in processed_content:
                        processed_content += f"\n\n---\n\n*Source: [{source}]({url})*"
                    
                    logger.info(f"Successfully processed article with DeepSeek: {title}")
                    
                    return {
                        'title': title,
                        'processed_content': processed_content,
                        'source_url': url,
                        'category': article_category
                    }
                else:
                    logger.warning(f"Unexpected response structure from DeepSeek API: {json.dumps(response_data)[:200]}...")
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.exception(f"Error processing news with DeepSeek: {str(e)}")
            
        return None
    
    def _fix_markdown_formatting(self, content: str) -> str:
        """
        Fix common markdown formatting issues in generated content
        
        Args:
            content: The content to fix
            
        Returns:
            Fixed content with proper markdown formatting
        """
        # Remove wrapping markdown code blocks if present
        if content.startswith("```markdown") and content.endswith("```"):
            content = content[len("```markdown"):].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        
        # Ensure code blocks are properly formatted
        import re
        
        # Fix python code blocks that don't have proper syntax highlighting
        content = re.sub(r'```\s*\n(def |import |from |class |\s*#)', r'```python\n\1', content)
        
        # Fix Python code blocks with common Python keywords
        content = re.sub(r'```\s*\n(if |for |while |try:|except:|finally:|with |return |print\(|assert )', 
                         r'```python\n\1', content)
        
        # Fix indented code blocks
        content = re.sub(r'```\s*\n(\s{2,})', r'```python\n\1', content)
        
        # Protect existing code blocks before processing
        protected_blocks = []
        
        def protect_code_blocks(match):
            protected_blocks.append(match.group(0))
            return f"PROTECTED_BLOCK_{len(protected_blocks)-1}"
            
        content_protected = re.sub(r'```[\s\S]*?```', protect_code_blocks, content)
        
        # Simplified patterns that avoid look-behind for better compatibility
        potential_code_patterns = [
            # Function definitions
            r'(\n|^)(def \w+\([^)]*\):\s*\n\s+[^\n]+(?:\n\s+[^\n]+)*)',
            
            # Import statements
            r'(\n|^)((?:from|import) \w+[^\n]*\n(?:\s+[^\n]+)*)',
            
            # Class definitions
            r'(\n|^)(class \w+(?:\([^)]*\))?:\s*\n\s+[^\n]+(?:\n\s+[^\n]+)*)',
            
            # Variable assignments with Python data structures
            r'(\n|^)(\w+ = (?:\{|\[|\(|")[^\n]*(?:\n\s+[^\n]+)*)'
        ]
        
        # Wrap potential code sections in code blocks
        for pattern in potential_code_patterns:
            content_protected = re.sub(pattern, r'\1\n```python\n\2\n```\n', content_protected)
        
        # Restore protected blocks
        for i, block in enumerate(protected_blocks):
            content_protected = content_protected.replace(f"PROTECTED_BLOCK_{i}", block)
        
        # Ensure all code blocks have a language specifier (default to plain text)
        content_protected = re.sub(r'```\s*\n', r'```\n', content_protected)
        
        # Fix inline code formatting (ensuring there's a space after backticks)
        content_protected = re.sub(r'(`{3})([^\s`])', r'\1 \2', content_protected)
        
        # Ensure source attribution is properly formatted
        if "*Source:" in content_protected and not content_protected.endswith("*"):
            content_protected += "\n"
        
        return content_protected
    
    def generate_tech_tags(self, title: str, content: str) -> List[str]:
        """
        Generate appropriate tech tags for a blog post
        
        Args:
            title: The blog post title
            content: The blog post content
            
        Returns:
            List of tags suitable for the post
        """
        # Combine title and beginning of content for analysis
        analysis_text = f"{title} {content[:500]}".lower()
        
        # Base tag is always technology
        tags = ["technology"]
        
        # Add specific tech categories based on content
        if any(kw in analysis_text for kw in ['ai', 'artificial intelligence', 'machine learning', 'neural', 'model']):
            tags.append('ai')
            
        if any(kw in analysis_text for kw in ['security', 'cyber', 'vulnerability', 'hack', 'breach', 'encryption']):
            tags.append('security')
            
        if any(kw in analysis_text for kw in ['web', 'javascript', 'typescript', 'frontend', 'css', 'html', 'react', 'vue', 'angular']):
            tags.append('webdev')
            
        if any(kw in analysis_text for kw in ['cloud', 'aws', 'azure', 'gcp', 'devops', 'kubernetes', 'docker', 'container']):
            tags.append('cloud')
            
        if any(kw in analysis_text for kw in ['mobile', 'android', 'ios', 'app', 'smartphone', 'tablet']):
            tags.append('mobile')
            
        if any(kw in analysis_text for kw in ['database', 'sql', 'nosql', 'data', 'analytics', 'big data']):
            tags.append('database')
            
        if any(kw in analysis_text for kw in ['programming', 'code', 'developer', 'software', 'engineering']):
            tags.append('programming')
            
        if any(kw in analysis_text for kw in ['opensource', 'open source', 'github', 'community', 'contribution']):
            tags.append('opensource')
            
        # Return at most 4 tags (Dev.to recommendation)
        return tags[:4]
    
    def _determine_article_category(self, title: str, content: str, keywords: List[str]) -> str:
        """
        Determine the category of an article based on its content
        
        Args:
            title: The article title
            content: The article content
            keywords: Keywords extracted from the article
            
        Returns:
            Category name as a string
        """
        # Combine title, content and keywords for analysis
        combined_text = f"{title} {content} {' '.join(keywords)}".lower()
        
        # Define categories with their keywords
        categories = {
            'technical': [
                'programming', 'code', 'developer', 'javascript', 'python', 'java', 'typescript',
                'framework', 'library', 'api', 'database', 'coding', 'algorithm', 'software development'
            ],
            'ai-research': [
                'artificial intelligence', 'machine learning', 'neural network', 'deep learning', 'nlp',
                'computer vision', 'reinforcement learning', 'transformer', 'large language model', 'llm',
                'gpt', 'bert', 'research paper', 'ai research'
            ],
            'ai-business': [
                'ai company', 'ai startup', 'ai funding', 'ai product', 'ai tool', 'ai application',
                'chatgpt', 'copilot', 'business model', 'monetization', 'ai industry'
            ],
            'cybersecurity': [
                'security', 'hack', 'breach', 'vulnerability', 'exploit', 'malware', 'ransomware',
                'phishing', 'authentication', 'encryption', 'zero-day', 'attack vector'
            ],
            'tech-industry': [
                'tech company', 'acquisition', 'merger', 'tech industry', 'big tech', 'startup',
                'funding', 'ipo', 'silicon valley', 'tech regulation', 'tech policy'
            ],
            'product-release': [
                'launch', 'release', 'announced', 'unveil', 'new version', 'update', 'feature',
                'product', 'device', 'hardware', 'gadget', 'smartphone', 'app update'
            ],
            'creative-tech': [
                'design', 'ux', 'ui', 'user experience', 'creative', 'art', 'animation', 'gaming',
                'game development', 'virtual reality', 'augmented reality', 'metaverse', '3d'
            ]
        }
        
        # Calculate scores for each category
        scores = {}
        for category, keywords in categories.items():
            score = sum(keyword in combined_text for keyword in keywords)
            scores[category] = score
            
        # Get the category with highest score
        max_score = 0
        best_category = 'tech-news'  # default
        
        for category, score in scores.items():
            if score > max_score:
                max_score = score
                best_category = category
                
        return best_category
        
    def _create_system_prompt(self, article_category: str) -> str:
        """
        Create a system prompt tailored to the article category
        
        Args:
            article_category: The category of the article
            
        Returns:
            System prompt as a string
        """
        # Base prompt elements
        base_prompt = """
You are a professional tech journalist and developer with deep expertise in the technology industry. 
Your task is to transform news articles into engaging, informative blog posts that sound natural, 
well-researched, and written by a human tech professional.

Follow these guidelines:
1. Write in a conversational but professional tone
2. Include relevant analysis that demonstrates domain expertise
3. Add valuable context and industry perspective
4. Structure the post with clear headings and a logical flow
5. Add a personal analysis section that shows critical thinking
6. NEVER mention AI, language models, or that you're transforming content
7. NEVER include phrases like "As a tech enthusiast" or "As a developer"
8. NEVER wrap your entire content in a markdown code block - only use code blocks for actual code snippets

Format requirements:
- Use proper Markdown formatting (headings with #, lists with -, etc.)
- Always include a source attribution at the end
- Don't include unnecessary markdown code block wrappers around your entire post
"""

        # Category-specific prompt additions
        category_prompts = {
            'technical': """
For this technical article:
- Include specific technical details and explanations when relevant
- When appropriate, provide code examples that illustrate key concepts
- Explain technical concepts clearly for both beginners and experienced developers
- Compare with alternatives or related technologies when relevant
- Focus on practical implications for developers
""",
            'ai-research': """
For this AI research article:
- Explain complex AI concepts in accessible terms without oversimplifying
- Highlight key innovations or breakthroughs and their significance
- Provide context on how this research fits into the broader AI landscape
- Discuss potential applications and limitations of the research
- Avoid hype while maintaining excitement about genuine advances
""",
            'ai-business': """
For this AI business/industry article:
- Analyze the business strategy and market positioning
- Consider how this development affects the competitive landscape
- Discuss implications for developers, users, and other stakeholders
- Provide perspective on business model and growth potential
- Maintain balanced perspective on business claims
""",
            'cybersecurity': """
For this cybersecurity article:
- Explain the technical aspects of security issues clearly
- Provide context on the severity and scope of security concerns
- Include practical takeaways for developers and organizations
- Discuss broader implications for security practices
- Be factual and avoid unnecessary alarm or downplaying of issues
""",
            'tech-industry': """
For this tech industry article:
- Analyze how this news affects the broader technology landscape
- Provide context on company strategy and industry trends
- Consider implications for developers and technology professionals
- Discuss potential future developments based on this news
- Maintain objectivity when discussing company announcements
""",
            'product-release': """
For this product announcement/release article:
- Focus on the most significant features and improvements
- Provide context on how this product fits in its category
- Analyze how it might impact developers and users
- Compare with competing products when relevant
- Be balanced - discuss both strengths and potential limitations
""",
            'creative-tech': """
For this creative technology article:
- Highlight the intersection of creativity and technology
- Discuss implications for designers, developers, and content creators
- Analyze trends in creative technology and digital experiences
- Provide perspective on user experience and design considerations
- Connect to broader trends in digital creativity
"""
        }
        
        # Get category-specific prompt or use default
        category_prompt = category_prompts.get(article_category, """
For this tech news article:
- Highlight the most important aspects of the news
- Provide context on why this matters to the tech community
- Consider implications for various stakeholders
- Be factual while providing thoughtful analysis
- Maintain a balanced perspective
""")
        
        return base_prompt + category_prompt
        
    def generate_platform_summary(self, content: Dict[str, Any], platform: str, max_length: int = 250) -> Optional[Dict[str, Any]]:
        """
        Generate a concise summary optimized for specific platforms with character limits
        
        Args:
            content: Dictionary containing article data
            platform: Platform name (e.g., "mastodon", "twitter")
            max_length: Maximum length of the summary in characters
            
        Returns:
            Dictionary with generated summary or None if generation failed
        """
        if not self.api_key:
            logger.warning("DeepSeek API key not provided, skipping summary generation")
            return None
            
        try:
            # Extract content
            title = content.get('title', '')
            description = content.get('description', '')
            article_content = content.get('content', '')
            full_content = content.get('fullContent', '')  # From article extractor
            url = content.get('url', '')
            source = content.get('source', {}).get('name', '') if isinstance(content.get('source'), dict) else content.get('source', '')
            
            # Use the best available content
            article_text = full_content if full_content else (article_content if article_content else description)
            
            # Skip if not enough content
            if not title or not article_text:
                logger.warning("Insufficient content for summary generation")
                return None
                
            # Use different prompts based on platform
            if platform.lower() == "mastodon":
                system_prompt = f"""
You are a tech journalist tasked with creating concise, engaging summaries for Mastodon posts.

Guidelines:
1. Create a single-sentence or very short paragraph that captures the core news
2. Focus on the most important technical information or insight
3. Maintain a professional tone while being conversational
4. Avoid using hashtags in the summary itself
5. Keep the summary under {max_length} characters MAXIMUM
6. Do not include the URL or title in your response

The summary should stand alone as an informative teaser that makes readers want to click the link.
"""
            else:  # Default/generic summary
                system_prompt = f"""
You are a tech journalist tasked with creating concise, engaging summaries for social media.

Guidelines:
1. Create a brief summary that captures the essential information
2. Focus on the most relevant details for a tech audience
3. Maintain a professional tone
4. Keep the summary under {max_length} characters MAXIMUM
5. Do not include the URL or title in your response

The summary should provide clear value even in limited space.
"""

            # Create user prompt
            user_prompt = f"""
Create a concise summary of this tech article for {platform}:

TITLE: {title}

FULL ARTICLE:
{article_text[:3000]}  # Limit to avoid token issues

The summary must:
- Be under {max_length} characters
- Capture the most important information
- Be engaging enough to make people want to read more
- Not repeat the title
- Not include hashtags or URLs

IMPORTANT: Your response should be ONLY the summary text, nothing else.
"""

            # Prepare the API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            # Log the API call
            logger.debug(f"Calling DeepSeek API for {platform} summary: {title}")
            
            # Make the API request
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # Process the response
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the generated summary
                if (response_data.get('choices') and
                    len(response_data['choices']) > 0 and
                    response_data['choices'][0].get('message') and
                    response_data['choices'][0]['message'].get('content')):
                    
                    summary = response_data['choices'][0]['message']['content'].strip()
                    
                    # Ensure summary is within length limit
                    if len(summary) > max_length:
                        summary = summary[:max_length-3] + "..."
                    
                    logger.info(f"Successfully generated {platform} summary: {len(summary)} characters")
                    
                    return {
                        'title': title,
                        'summary': summary,
                        'source_url': url,
                        'platform': platform
                    }
                else:
                    logger.warning(f"Unexpected response structure from DeepSeek API: {json.dumps(response_data)[:200]}...")
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.exception(f"Error generating {platform} summary: {str(e)}")
            
        return None 