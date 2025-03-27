#!/usr/bin/env python3
"""
Example script demonstrating how to use the content quality framework.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from social_media_bot.tools.content_quality import (
    ContentCredibilityEvaluator,
    TransparencyTemplates,
    ContentQualityRulesEngine,
    PostEnhancementModule
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function demonstrating content quality framework usage."""
    # Initialize components
    evaluator = ContentCredibilityEvaluator()
    templates = TransparencyTemplates()
    rules_engine = ContentQualityRulesEngine()
    enhancer = PostEnhancementModule()
    
    # Example 1: Evaluating a tech news article
    example_tech_news = """
    Revolutionary New AI Model Can Generate Realistic 3D Models from Text
    
    A team of researchers has developed a new AI system that can create detailed 3D models
    directly from text descriptions. The technology could revolutionize game development,
    industrial design, and virtual reality experiences by drastically reducing the time
    and expertise needed to create 3D assets.
    
    The system uses a novel approach that combines large language models with diffusion-based
    3D generation techniques.
    """
    
    logger.info("Evaluating example tech news article...")
    
    # Evaluate credibility
    credibility_result = evaluator._run(
        content=example_tech_news,
        content_type="tech_news"
    )
    
    logger.info(f"Credibility score: {credibility_result['overall_score']}/100")
    logger.info(f"Improvement suggestions: {credibility_result['improvement_suggestions']}")
    
    # Evaluate against quality rules
    rules_result = rules_engine.evaluate_content(
        content=example_tech_news,
        content_type="tech_news"
    )
    
    logger.info(f"Quality compliance: {rules_result['overall_compliance']}%")
    logger.info(f"Failed required rules: {rules_result['failed_required_rules']}")
    logger.info(f"Is publishable: {rules_result['is_publishable']}")
    
    # Enhance the content
    enhanced_result = enhancer.enhance_content(
        content=example_tech_news,
        content_type="tech_news",
        source="AI Research Journal",
        positive_aspects="faster content creation and democratization of 3D modeling",
        negative_aspects="potential copyright and ethical concerns regarding generated content"
    )
    
    logger.info(f"Original score: {enhanced_result['original_score']}%")
    logger.info(f"Enhanced score: {enhanced_result['enhanced_score']}%")
    logger.info(f"Enhancements applied: {enhanced_result['enhancements_applied']}")
    
    # Display enhanced content
    logger.info("\nEnhanced content:")
    logger.info("-----------------")
    logger.info(enhanced_result['enhanced_content'])
    
    # Example 2: Using transparency templates
    logger.info("\nTransparency templates examples:")
    logger.info("------------------------------")
    
    knowledge_disclosure = templates.get_knowledge_disclosure(
        level="beginner",
        topic="3D modeling AI",
        content="this technology seems promising but I have questions about its practical applications"
    )
    
    logger.info(f"Knowledge disclosure example: {knowledge_disclosure}")
    
    source_attribution = templates.get_source_attribution(
        attribution_type="article",
        source="AI Research Journal",
        content="the new model achieves 85% accuracy on benchmark tests"
    )
    
    logger.info(f"Source attribution example: {source_attribution}")
    
    balance_indicator = templates.get_balance_indicator(
        indicator_type="balanced_view",
        positive_aspects="the technology offers significant productivity gains",
        negative_aspects="there are concerns about accuracy and usability for complex models"
    )
    
    logger.info(f"Balance indicator example: {balance_indicator}")
    
    # Example 3: Complete tech news template
    full_template = templates.get_full_template(
        content_type="tech_news",
        template_index=1,
        headline="New AI System Generates 3D Models from Text",
        main_content="researchers have developed an AI system that can create detailed 3D models directly from text descriptions",
        source="AI Research Journal",
        source_context="publishes peer-reviewed research on artificial intelligence applications",
        implications="faster game development, more accessible industrial design, and enhanced virtual reality experiences"
    )
    
    logger.info("\nFull template example:")
    logger.info("---------------------")
    logger.info(full_template)

if __name__ == "__main__":
    main() 