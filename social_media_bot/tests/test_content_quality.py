import unittest
import os
import sys
import logging
from pathlib import Path

# Add parent directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from social_media_bot.tools.content_quality import (
    ContentCredibilityEvaluator,
    TransparencyTemplates,
    ContentQualityRulesEngine,
    PostEnhancementModule
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestContentQuality(unittest.TestCase):
    """Test case for content quality framework."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.credibility_evaluator = ContentCredibilityEvaluator()
        self.templates = TransparencyTemplates()
        self.rules_engine = ContentQualityRulesEngine()
        self.enhancer = PostEnhancementModule()
        
        # Sample content for testing
        self.good_tech_news = """
        New AI Model Achieves Breakthrough in Natural Language Understanding
        
        According to research published in Nature on Monday, OpenAI's latest model has achieved a 
        significant breakthrough in understanding complex language nuances. The model demonstrates 
        a 25% improvement over previous benchmarks on linguistic reasoning tasks.
        
        The research team reported that the new architecture incorporates several novel techniques, 
        including a modified attention mechanism and improved training methodology.
        
        While the results are impressive, researchers note that challenges remain in areas such as 
        factual consistency and bias mitigation.
        
        The code and research paper are available at https://example.com/research/paper.
        """
        
        self.poor_tech_news = """
        SHOCKING New AI Will BLOW YOUR MIND!!!
        
        A new AI has been created that is better than anything ever made before. It's absolutely 
        revolutionary and will change everything forever! Everyone is talking about it!
        
        The AI can do things no other AI has ever done, and it's going to make all other AI obsolete 
        immediately. This is definitely the biggest tech breakthrough in history!!!
        """
        
        self.good_opinion = """
        My Thoughts on the Future of AI Development
        
        As someone who has worked in AI research for over five years, I believe we're approaching 
        a significant inflection point in how models are trained and deployed.
        
        In my opinion, the industry will shift toward more specialized models optimized for specific 
        domains, rather than continuing to scale general-purpose models indefinitely.
        
        I base this assessment on several trends: increasing computational costs, diminishing returns 
        from scale alone, and growing demand for domain expertise.
        
        However, I recognize that others in the field see continued scaling as the primary path forward, 
        and they make valid points about emergent capabilities that appear only at scale.
        
        What do you think about the specialization vs. scale debate?
        """
        
        self.poor_opinion = """
        AI is completely overhyped
        
        AI is just statistical pattern matching and will never achieve actual intelligence. 
        Everyone who thinks otherwise is deluded. Current models are useless for real work 
        and all fail on simple tasks.
        
        Neural networks are a dead end and we need to start over with a completely different approach.
        """
    
    def test_credibility_evaluator(self):
        """Test the credibility evaluator."""
        good_result = self.credibility_evaluator._run(
            content=self.good_tech_news,
            source_url="https://example.com/research/paper",
            content_type="tech_news"
        )
        
        poor_result = self.credibility_evaluator._run(
            content=self.poor_tech_news,
            content_type="tech_news"
        )
        
        # Check if good content scores better than poor content
        self.assertGreater(
            good_result['overall_score'], 
            poor_result['overall_score'],
            "Good content should score higher than poor content"
        )
        
        # Check source attribution detection
        self.assertGreater(
            good_result['factor_scores']['has_source_attribution'],
            poor_result['factor_scores']['has_source_attribution'],
            "Good content should have better source attribution"
        )
    
    def test_transparency_templates(self):
        """Test transparency templates."""
        # Test knowledge disclosure templates
        expert_disclosure = self.templates.get_knowledge_disclosure(
            "expert", "AI development", "here are my thoughts"
        )
        self.assertIn("extensive experience", expert_disclosure)
        self.assertIn("AI development", expert_disclosure)
        
        # Test source attribution templates
        source_attribution = self.templates.get_source_attribution(
            "article", "MIT Technology Review", "quantum computers reached a new milestone"
        )
        self.assertIn("MIT Technology Review", source_attribution)
        self.assertIn("quantum computers", source_attribution)
        
        # Test full templates, providing all required parameters
        tech_news_template = self.templates.get_full_template(
            content_type="tech_news",
            template_index=1,  # Use template that doesn't require additional_details
            headline="New breakthrough in quantum computing",
            source="Google AI",
            main_content="researchers have achieved quantum supremacy",
            source_context="is a leading AI research lab",
            implications="faster drug discovery and optimization of complex systems"
        )
        self.assertIn("New breakthrough in quantum computing", tech_news_template)
        self.assertIn("Google AI", tech_news_template)
        
        # Test with first template that would have required additional_details
        # (now handled with default value)
        first_template = self.templates.get_full_template(
            content_type="tech_news",
            template_index=0,
            headline="AI breakthrough announced",
            source="Research Institute",
            main_content="a new model surpasses human performance"
        )
        self.assertIn("AI breakthrough announced", first_template)
        self.assertIn("For more information", first_template)
    
    def test_rules_engine(self):
        """Test the rules engine."""
        good_rules_result = self.rules_engine.evaluate_content(
            self.good_tech_news, "tech_news"
        )
        
        poor_rules_result = self.rules_engine.evaluate_content(
            self.poor_tech_news, "tech_news"
        )
        
        # Check overall compliance scores
        self.assertGreater(
            good_rules_result['overall_compliance'],
            poor_rules_result['overall_compliance'],
            "Good content should have better rules compliance"
        )
        
        # Check specific rule results
        self.assertTrue(
            good_rules_result['rule_results']['cites_source'],
            "Good tech news should cite sources"
        )
        
        self.assertFalse(
            poor_rules_result['rule_results']['avoids_clickbait'],
            "Poor tech news should fail clickbait rule"
        )
        
        # Check opinion content
        good_opinion_result = self.rules_engine.evaluate_content(
            self.good_opinion, "opinion"
        )
        
        poor_opinion_result = self.rules_engine.evaluate_content(
            self.poor_opinion, "opinion"
        )
        
        self.assertTrue(
            good_opinion_result['rule_results']['clearly_marked_opinion'],
            "Good opinion should be clearly marked"
        )
        
        self.assertFalse(
            poor_opinion_result['rule_results']['acknowledges_alternatives'],
            "Poor opinion should fail to acknowledge alternatives"
        )
    
    def test_post_enhancement(self):
        """Test post enhancement module."""
        # Create a more obvious clickbait test case
        extreme_clickbait = """
        SHOCKING MIND-BLOWING AI DISCOVERY You Won't Believe!!!
        
        This REVOLUTIONARY technology will CHANGE EVERYTHING FOREVER!
        Everyone is talking about this INCREDIBLE breakthrough that will
        make everything else obsolete immediately!!!
        """
        
        # Test enhancement of clickbait content
        enhancement_result = self.enhancer.enhance_content(
            content=extreme_clickbait,
            content_type="tech_news",
            source="Tech Research Institute",
            positive_aspects="potential for improved performance in specific tasks",
            negative_aspects="limitations in generalizability and high computational requirements"
        )
        
        # Check if score improved
        self.assertGreater(
            enhancement_result['enhanced_score'],
            enhancement_result['original_score'],
            "Enhancement should improve content quality score"
        )
        
        # Check if clickbait was removed
        self.assertNotIn(
            "SHOCKING", enhancement_result['enhanced_content'],
            "Enhancement should remove clickbait elements"
        )
        self.assertNotIn(
            "MIND-BLOWING", enhancement_result['enhanced_content'],
            "Enhancement should remove clickbait elements"
        )
        self.assertNotIn(
            "Won't Believe", enhancement_result['enhanced_content'],
            "Enhancement should remove clickbait elements"
        )
        
        # Check if source attribution was added
        self.assertIn(
            "According to Tech Research Institute", enhancement_result['enhanced_content'],
            "Enhancement should add source attribution"
        )
        
        # Test enhancement of poor opinion
        opinion_enhancement = self.enhancer.enhance_content(
            content=self.poor_opinion,
            content_type="opinion",
            knowledge_level="intermediate",
            topic="artificial intelligence"
        )
        
        # Check if knowledge level was added
        self.assertIn(
            "With some background in artificial intelligence", opinion_enhancement['enhanced_content'],
            "Enhancement should add knowledge level disclosure"
        )

if __name__ == '__main__':
    unittest.main() 