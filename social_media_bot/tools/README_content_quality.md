# Content Quality Framework

This module provides a comprehensive framework for ensuring high-quality, credible, and transparent content in social media posts. It is designed to help maintain professional standards in content curation and generation, especially for tech news and analyses.

## Components

### 1. Content Credibility Evaluator

Analyzes content for key credibility factors:
- Source attribution
- Factual consistency
- Appropriate disclosures
- Balanced perspectives
- Clarity between opinion and fact

```python
from social_media_bot.tools.content_quality import ContentCredibilityEvaluatorTool

evaluator = ContentCredibilityEvaluatorTool()
result = evaluator._run(
    content="Your content here",
    source_url="https://example.com/source",
    content_type="tech_news"
)
```

### 2. Transparency Templates

Provides templates for adding proper transparency and disclosure to content:
- Knowledge level disclosures
- Source attribution formats
- Opinion markers
- Balance indicators
- Complete content templates

```python
from social_media_bot.tools.content_quality import TransparencyTemplates

templates = TransparencyTemplates()
disclosure = templates.get_knowledge_disclosure(
    level="beginner",
    topic="AI development",
    content="this looks promising but I have questions"
)
```

### 3. Content Quality Rules Engine

A rule-based system to evaluate posts against quality criteria:
- Structure requirements
- Fact-checking requirements
- Source attribution requirements
- Disclosure requirements

```python
from social_media_bot.tools.content_quality import ContentQualityRulesTool

rules_tool = ContentQualityRulesTool()
result = rules_tool._run(
    content="Your content here",
    content_type="tech_news"
)
```

### 4. Post Enhancement Module

Tools to improve post quality:
- Structure formatter
- Source validator
- Fact-checking prompts
- Disclosure generator

```python
from social_media_bot.tools.content_quality import ContentEnhancementTool

enhancer = ContentEnhancementTool()
result = enhancer._run(
    content="Your content here",
    content_type="tech_news",
    source="Reliable Source",
    knowledge_level="observer"
)
```

## Integration with CrewAI

The framework is designed to integrate with the CrewAI system:

```python
from crewai import Agent, Task
from social_media_bot.tools.content_quality import ContentCredibilityEvaluatorTool

content_quality_agent = Agent(
    role="Content Quality Manager",
    goal="Ensure content meets quality standards",
    backstory="Expert in content credibility and transparency",
    tools=[ContentCredibilityEvaluatorTool()]
)

evaluate_task = Task(
    description="Evaluate content credibility and suggest improvements",
    agent=content_quality_agent
)
```

## Best Practices

1. **Always check content quality before posting**:
   - Evaluate credibility score
   - Check rule compliance
   - Apply enhancements if needed

2. **Be transparent about knowledge level**:
   - Use appropriate disclosure templates
   - Be honest about limitations
   - Clearly distinguish between firsthand and secondhand knowledge

3. **Properly attribute sources**:
   - Include original source links
   - Use proper attribution templates
   - Credit original creators

4. **Maintain balanced perspective**:
   - Present multiple viewpoints
   - Acknowledge limitations and challenges
   - Avoid overly positive or negative content

5. **Clearly distinguish fact from opinion**:
   - Use opinion markers for subjective statements
   - Provide evidence for factual claims
   - Avoid absolute statements without proof

## Example Usage

See the example script in `social_media_bot/examples/content_quality_example.py` for a complete demonstration of the framework.

## Running Tests

Tests for the content quality framework can be found in `social_media_bot/tests/test_content_quality.py`.

To run the tests:

```bash
cd path/to/project
python -m social_media_bot.tests.test_content_quality
``` 