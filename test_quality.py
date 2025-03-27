import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

try:
    logger.info("Importing content quality modules...")
    from social_media_bot.tools.content_quality import (
        ContentCredibilityEvaluator,
        TransparencyTemplates,
        ContentQualityRulesEngine,
        PostEnhancementModule
    )
    logger.info("Modules imported successfully!")
except Exception as e:
    logger.error(f"Error importing modules: {str(e)}")
    raise

def main():
    """Test the content quality framework"""
    logger.info("Testing Content Quality Framework...")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        evaluator = ContentCredibilityEvaluator()
        templates = TransparencyTemplates()
        rules_engine = ContentQualityRulesEngine()
        enhancer = PostEnhancementModule()
        logger.info("Components initialized successfully!")
        
        # Example clickbait content
        clickbait_content = """
        SHOCKING AI Will BLOW YOUR MIND!!!
        
        This revolutionary technology will change everything forever!
        Everyone is talking about this incredible breakthrough.
        """
        
        # Evaluate content quality
        logger.info("Evaluating content credibility...")
        credibility_result = evaluator._run(
            content=clickbait_content,
            content_type="tech_news"
        )
        
        logger.info(f"Credibility Score: {credibility_result['overall_score']}/100")
        logger.info(f"Improvement Suggestions: {credibility_result['improvement_suggestions']}")
        
        # Enhance the content
        logger.info("Enhancing content...")
        enhanced_result = enhancer.enhance_content(
            content=clickbait_content,
            content_type="tech_news",
            source="AI Research Journal",
            positive_aspects="potential productivity improvements",
            negative_aspects="limited real-world testing"
        )
        
        logger.info("\nOriginal Content:")
        logger.info("-----------------")
        logger.info(clickbait_content)
        
        logger.info("\nEnhanced Content:")
        logger.info("-----------------")
        logger.info(enhanced_result['enhanced_content'])
        
        logger.info(f"\nEnhancements Applied: {enhanced_result['enhancements_applied']}")
        logger.info(f"Original Score: {enhanced_result['original_score']}%")
        logger.info(f"Enhanced Score: {enhanced_result['enhanced_score']}%")
        
        # Test transparency templates
        logger.info("\nTransparency Templates:")
        logger.info("-----------------------")
        
        knowledge_disclosure = templates.get_knowledge_disclosure(
            "beginner", 
            "AI technology", 
            "this seems interesting but I have questions"
        )
        
        logger.info(f"Knowledge Disclosure: {knowledge_disclosure}")
        
        # Test content quality rules
        logger.info("Evaluating content against quality rules...")
        rules_result = rules_engine.evaluate_content(
            enhanced_result['enhanced_content'],
            "tech_news"
        )
        
        logger.info(f"\nRules Compliance: {rules_result['overall_compliance']}%")
        logger.info(f"Is Publishable: {rules_result['is_publishable']}")
        
        if not rules_result['is_publishable']:
            logger.info(f"Failed Required Rules: {rules_result['failed_required_rules']}")
            
        logger.info("Content quality test completed successfully!")
    
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 