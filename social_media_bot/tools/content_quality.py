import os
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from crewai.tools import BaseTool
import re
import json

logger = logging.getLogger(__name__)

class ContentCredibilitySchema(BaseModel):
    """Schema for content credibility evaluation."""
    content: str = Field(description="The content to evaluate")
    source_url: Optional[str] = Field(None, description="URL of the original source")
    claimed_facts: Optional[List[str]] = Field(None, description="List of factual claims made in the content")
    content_type: str = Field(description="Type of content (e.g., 'tech_news', 'product_review', 'opinion')")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        valid_types = ['tech_news', 'product_review', 'opinion', 'analysis', 'tutorial', 'announcement']
        if v not in valid_types:
            raise ValueError(f"content_type must be one of {valid_types}")
        return v

class ContentCredibilityEvaluator(BaseTool):
    """
    Tool to analyze content for credibility factors.
    
    Evaluates:
    - Source attribution
    - Factual consistency
    - Verification status
    - Experience level transparency
    """
    name: str = "Evaluate Content Credibility"
    description: str = """
    Evaluate content for credibility factors including source attribution,
    factual claims, verification status, and appropriate transparency.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._credibility_factors = {
            'has_source_attribution': 0,
            'factual_consistency': 0,
            'appropriate_disclosure': 0,
            'balanced_perspective': 0,
            'clear_opinion_vs_fact': 0
        }
    
    def _run(self, content: str, source_url: Optional[str] = None, 
            content_type: str = "tech_news", 
            claimed_facts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the credibility evaluation on the content.
        
        Args:
            content: The text content to evaluate
            source_url: URL of the original source if available
            content_type: Type of content being evaluated
            claimed_facts: List of factual claims made in the content
            
        Returns:
            Dictionary with credibility scores and suggestions for improvement
        """
        # Initialize results
        results = self._credibility_factors.copy()
        improvement_suggestions = []
        
        # Check for source attribution
        source_score, source_suggestions = self._evaluate_source_attribution(content, source_url)
        results['has_source_attribution'] = source_score
        improvement_suggestions.extend(source_suggestions)
        
        # Check for factual consistency
        fact_score, fact_suggestions = self._evaluate_factual_consistency(content, claimed_facts)
        results['factual_consistency'] = fact_score
        improvement_suggestions.extend(fact_suggestions)
        
        # Check for appropriate disclosures
        disclosure_score, disclosure_suggestions = self._evaluate_disclosures(content, content_type)
        results['appropriate_disclosure'] = disclosure_score
        improvement_suggestions.extend(disclosure_suggestions)
        
        # Check for balanced perspective
        balance_score, balance_suggestions = self._evaluate_balance(content, content_type)
        results['balanced_perspective'] = balance_score
        improvement_suggestions.extend(balance_suggestions)
        
        # Check for clear distinction between opinion and fact
        clarity_score, clarity_suggestions = self._evaluate_opinion_fact_clarity(content)
        results['clear_opinion_vs_fact'] = clarity_score
        improvement_suggestions.extend(clarity_suggestions)
        
        # Calculate overall credibility score (0-100)
        weights = {
            'has_source_attribution': 0.25,
            'factual_consistency': 0.25,
            'appropriate_disclosure': 0.20,
            'balanced_perspective': 0.15,
            'clear_opinion_vs_fact': 0.15
        }
        
        overall_score = sum(score * weights[factor] for factor, score in results.items()) * 20
        
        return {
            'overall_score': round(overall_score, 1),
            'factor_scores': results,
            'improvement_suggestions': improvement_suggestions
        }
    
    def _evaluate_source_attribution(self, content: str, source_url: Optional[str]) -> tuple:
        """Evaluate content for proper source attribution."""
        score = 0
        suggestions = []
        
        # Check if content mentions source
        source_patterns = [
            r'source[s]?:',
            r'according to',
            r'reported by',
            r'published (on|in|by)',
            r'from [a-zA-Z\s]+ article',
            r'credit[s]? to',
            r'originally (on|in|at|by)',
            r'via'
        ]
        
        has_attribution = any(re.search(pattern, content, re.IGNORECASE) for pattern in source_patterns)
        
        # Check if URL is included
        has_url = bool(source_url) or bool(re.search(r'https?://[^\s]+', content))
        
        if has_attribution and has_url:
            score = 5  # Full score
        elif has_attribution:
            score = 3  # Partial score
            suggestions.append("Include a link to the original source")
        elif has_url:
            score = 2  # Lower partial score
            suggestions.append("Add explicit attribution to the source (e.g., 'According to [Source]')")
        else:
            score = 0  # No score
            suggestions.append("Add proper attribution and a link to the original source")
        
        return score, suggestions
    
    def _evaluate_factual_consistency(self, content: str, claimed_facts: Optional[List[str]]) -> tuple:
        """Evaluate content for factual consistency."""
        # This would normally use external verification APIs if available
        # For now, we'll use a rule-based approach
        
        score = 3  # Default middle score without fact checking APIs
        suggestions = []
        
        # Check for qualifying language that indicates factual care
        qualifying_patterns = [
            r'reportedly',
            r'allegedly',
            r'according to',
            r'claims',
            r'suggests',
            r'may',
            r'might',
            r'could',
            r'appears to'
        ]
        
        qualifier_count = sum(1 for pattern in qualifying_patterns if re.search(pattern, content, re.IGNORECASE))
        
        if claimed_facts and len(claimed_facts) > 0:
            # If specific claims were provided, we can score based on their presence
            score = 4
            suggestions.append("Consider adding sources for specific factual claims")
        
        if qualifier_count > 0:
            # Appropriately qualified claims
            score = min(5, score + 1)
        elif qualifier_count == 0 and re.search(r'definitely|absolutely|always|never|all|none', content, re.IGNORECASE):
            # Absolute claims without qualification
            score = max(1, score - 1)
            suggestions.append("Use qualifying language for claims that aren't universally verified")
        
        return score, suggestions
    
    def _evaluate_disclosures(self, content: str, content_type: str) -> tuple:
        """Evaluate appropriate disclosures based on content type."""
        score = 0
        suggestions = []
        
        # Different disclosure expectations based on content type
        if content_type == "tech_news":
            # For news, we expect source citation
            if re.search(r'source|according to|reported by', content, re.IGNORECASE):
                score = 5
            else:
                score = 2
                suggestions.append("Include source information for news content")
                
        elif content_type == "product_review":
            # For reviews, we expect experience disclosure
            if re.search(r'(I|we) (tried|tested|used|experienced|reviewed)', content, re.IGNORECASE):
                score = 5
            elif re.search(r'based on (reports|reviews|feedback)', content, re.IGNORECASE):
                score = 4
                suggestions.append("Clarify whether this is a first-hand or second-hand review")
            else:
                score = 2
                suggestions.append("Disclose your level of experience with the product")
                
        elif content_type == "opinion" or content_type == "analysis":
            # For opinions, we expect clear labeling
            if re.search(r'(in my opinion|I think|I believe|my take|my analysis)', content, re.IGNORECASE):
                score = 5
            else:
                score = 3
                suggestions.append("Clearly indicate when you're sharing an opinion or analysis")
        
        # Check for knowledge level disclosure
        if re.search(r'(I\'m not an expert|I have limited experience|from what I understand)', content, re.IGNORECASE):
            score = min(5, score + 1)  # Bonus for honest disclosure of limitations
        
        return score, suggestions
    
    def _evaluate_balance(self, content: str, content_type: str) -> tuple:
        """Evaluate content for balanced perspective."""
        score = 3  # Default middle score
        suggestions = []
        
        # Skip balance check for opinion pieces
        if content_type == "opinion":
            return 5, []
            
        # Check for balanced language
        positive_patterns = [r'benefit', r'advantage', r'pro', r'good', r'great', r'excellent']
        negative_patterns = [r'drawback', r'limitation', r'con', r'bad', r'poor', r'problem']
        
        positive_count = sum(1 for pattern in positive_patterns if re.search(pattern, content, re.IGNORECASE))
        negative_count = sum(1 for pattern in negative_patterns if re.search(pattern, content, re.IGNORECASE))
        
        # Check for "however", "but", "on the other hand" etc.
        has_contrasting = bool(re.search(r'however|but|on the other hand|conversely|despite', content, re.IGNORECASE))
        
        if positive_count > 0 and negative_count > 0:
            score = 5  # Both perspectives mentioned
        elif has_contrasting:
            score = 4  # Some contrast indicated
        elif positive_count > 3 and negative_count == 0:
            score = 1  # Overly positive
            suggestions.append("Include potential limitations or challenges")
        elif negative_count > 3 and positive_count == 0:
            score = 1  # Overly negative
            suggestions.append("Include potential benefits or advantages")
        else:
            score = 3  # Neutral
            
        return score, suggestions
        
    def _evaluate_opinion_fact_clarity(self, content: str) -> tuple:
        """Evaluate clarity between opinion statements and factual claims."""
        score = 3  # Default middle score
        suggestions = []
        
        # Opinion indicators
        opinion_patterns = [
            r'I (think|believe|feel)',
            r'in my opinion',
            r'it seems',
            r'appears to be',
            r'might be',
            r'could be',
            r'may be'
        ]
        
        # Fact indicators
        fact_patterns = [
            r'research shows',
            r'studies indicate',
            r'according to data',
            r'statistics show',
            r'evidence suggests',
            r'measurements indicate'
        ]
        
        opinion_indicators = sum(1 for pattern in opinion_patterns if re.search(pattern, content, re.IGNORECASE))
        fact_indicators = sum(1 for pattern in fact_patterns if re.search(pattern, content, re.IGNORECASE))
        
        if opinion_indicators > 0 and fact_indicators > 0:
            # Clear distinction between facts and opinions
            score = 5
        elif opinion_indicators > 0:
            # At least opinions are marked
            score = 4
        elif fact_indicators > 0:
            # At least facts are sourced
            score = 4
        else:
            # No clear distinction
            score = 2
            suggestions.append("Clearly distinguish between facts and opinions")
            
        # Look for absolute statements presented without evidence
        if re.search(r'(always|never|all|everyone|nobody) (is|are|do|does|will)', content, re.IGNORECASE):
            score = max(1, score - 1)
            suggestions.append("Avoid absolute statements unless they can be definitively proven")
            
        return score, suggestions

class TransparencyTemplates:
    """
    Provides templates for adding proper transparency and disclosure to content.
    
    These templates help maintain credibility by appropriately disclosing:
    - Knowledge level
    - Source attribution
    - Personal experience
    - Opinion vs fact
    """
    
    def __init__(self):
        self.templates = {
            'knowledge_disclosure': {
                'expert': "As someone with extensive experience in {topic}, {content}",
                'intermediate': "With some background in {topic}, {content}",
                'beginner': "While I'm still learning about {topic}, {content}",
                'observer': "Based on what I've observed about {topic}, {content}",
                'research_only': "From my research on {topic} (though I haven't used it directly), {content}"
            },
            'source_attribution': {
                'direct': "According to {source}, {content}",
                'article': "In a recent article by {source}, {content}",
                'announcement': "{source} has announced that {content}",
                'multiple': "Multiple sources including {sources} indicate that {content}",
                'unverified': "Reports suggest that {content}, though this hasn't been officially confirmed"
            },
            'opinion_markers': {
                'clear_opinion': "In my opinion, {content}",
                'personal_take': "My take on this is that {content}",
                'speculation': "It seems possible that {content}, though more information is needed",
                'analysis': "Analyzing the available information, {content}",
                'prediction': "Based on current trends, I predict that {content}"
            },
            'balance_indicators': {
                'advantages': "Some potential advantages include {advantages}",
                'limitations': "However, there are limitations such as {limitations}",
                'balanced_view': "While {positive_aspects}, it's important to note that {negative_aspects}",
                'uncertainty': "There's still uncertainty regarding {uncertain_aspects}"
            }
        }
        
        self.full_templates = {
            'tech_news': [
                "**News**: {headline}\n\n"
                "According to {source}, {main_content}\n\n"
                "{additional_details}\n\n"
                "What are your thoughts on this development?",
                
                "**Tech Update**: {headline}\n\n"
                "{main_content}\n\n"
                "This news comes from {source}, which {source_context}.\n\n"
                "The potential implications include {implications}."
            ],
            'product_review': [
                "**{product_name} Review**\n\n"
                "{knowledge_level} about {product_category}, I found that {main_points}.\n\n"
                "The standout features include {positive_points}.\n\n"
                "However, there are some limitations: {negative_points}.\n\n"
                "Have you tried this product?",
                
                "**My experience with {product_name}**\n\n"
                "{knowledge_level} with {product_category} products, {main_content}.\n\n"
                "What I liked: {positive_points}\n\n"
                "What could be improved: {negative_points}\n\n"
                "Who this might be good for: {recommendation}"
            ],
            'opinion': [
                "**My thoughts on {topic}**\n\n"
                "In my opinion, {main_point}.\n\n"
                "I believe this because {reasoning}.\n\n"
                "Of course, {alternative_perspective} is also a valid perspective.\n\n"
                "What do you think?",
                
                "**Perspective: {topic}**\n\n"
                "From my perspective, {main_point}.\n\n"
                "This is based on {evidence_or_experience}.\n\n"
                "While I think {opinion_detail}, I recognize that {counterpoint}.\n\n"
                "I'm curious about others' experiences with this."
            ]
        }
        
    def get_knowledge_disclosure(self, level: str, topic: str, content: str) -> str:
        """Get a knowledge level disclosure template."""
        if level not in self.templates['knowledge_disclosure']:
            level = 'observer'  # Default fallback
        
        template = self.templates['knowledge_disclosure'][level]
        return template.format(topic=topic, content=content)
    
    def get_source_attribution(self, attribution_type: str, source: str, content: str, 
                               sources: Optional[List[str]] = None) -> str:
        """Get a source attribution template."""
        if attribution_type not in self.templates['source_attribution']:
            attribution_type = 'direct'  # Default fallback
            
        template = self.templates['source_attribution'][attribution_type]
        
        # Handle multiple sources case
        if attribution_type == 'multiple' and sources:
            source_list = ", ".join(sources[:-1]) + " and " + sources[-1] if len(sources) > 1 else sources[0]
            return template.format(sources=source_list, content=content)
        
        return template.format(source=source, content=content)
    
    def get_opinion_marker(self, marker_type: str, content: str) -> str:
        """Get an opinion marker template."""
        if marker_type not in self.templates['opinion_markers']:
            marker_type = 'clear_opinion'  # Default fallback
            
        template = self.templates['opinion_markers'][marker_type]
        return template.format(content=content)
    
    def get_balance_indicator(self, indicator_type: str, **kwargs) -> str:
        """Get a balance indicator template."""
        if indicator_type not in self.templates['balance_indicators']:
            indicator_type = 'balanced_view'  # Default fallback
            
        template = self.templates['balance_indicators'][indicator_type]
        return template.format(**kwargs)
    
    def get_full_template(self, content_type: str, template_index: int = 0, **kwargs) -> str:
        """Get a full content template based on content type."""
        if content_type not in self.full_templates:
            content_type = 'tech_news'  # Default fallback
            
        templates = self.full_templates[content_type]
        template_index = min(template_index, len(templates) - 1)  # Ensure valid index
        
        template = templates[template_index]
        
        # Add default values for optional parameters
        if content_type == 'tech_news' and template_index == 0 and 'additional_details' not in kwargs:
            kwargs['additional_details'] = "For more information, check the original source."
            
        # Prepare other optional parameters with defaults
        optional_params = {
            'product_review': {
                'recommendation': 'users looking for a balance of features and usability'
            },
            'opinion': {
                'alternative_perspective': 'a different approach'
            }
        }
        
        if content_type in optional_params:
            for param, default in optional_params[content_type].items():
                if param not in kwargs:
                    kwargs[param] = default
        
        return template.format(**kwargs)

class ContentQualityRulesEngine:
    """
    Rule-based system to evaluate posts against quality criteria.
    
    Evaluates:
    - Structure requirements
    - Fact-checking requirements
    - Source attribution requirements
    - Disclosure requirements
    """
    
    def __init__(self):
        self.rules = {
            'tech_news': [
                {'name': 'has_clear_headline', 'required': True, 'description': 'Post must have a clear headline'},
                {'name': 'cites_source', 'required': True, 'description': 'News must cite a credible source'},
                {'name': 'includes_url', 'required': True, 'description': 'Must include original source URL'},
                {'name': 'avoids_clickbait', 'required': True, 'description': 'Headline must not be clickbait style'},
                {'name': 'presents_balanced_view', 'required': False, 'description': 'Should present multiple perspectives'},
                {'name': 'has_relevant_details', 'required': True, 'description': 'Includes key technical details'},
                {'name': 'uses_qualifying_language', 'required': True, 'description': 'Uses appropriate qualifying language for claims'},
                {'name': 'free_of_plagiarism', 'required': True, 'description': 'Content must not be plagiarized'},
                {'name': 'acceptable_length', 'required': True, 'description': 'Content must be of appropriate length'}
            ],
            'product_review': [
                {'name': 'discloses_experience_level', 'required': True, 'description': 'Must disclose experience level with product'},
                {'name': 'lists_pros_cons', 'required': True, 'description': 'Must include both pros and cons'},
                {'name': 'specific_details', 'required': True, 'description': 'Includes specific product details'},
                {'name': 'clear_recommendation', 'required': False, 'description': 'Provides clear recommendation or use case'},
                {'name': 'authentic_experience', 'required': True, 'description': 'Reflects authentic experience or research'},
                {'name': 'comparable_alternatives', 'required': False, 'description': 'Mentions comparable alternatives'},
                {'name': 'acceptable_length', 'required': True, 'description': 'Content must be of appropriate length'}
            ],
            'opinion': [
                {'name': 'clearly_marked_opinion', 'required': True, 'description': 'Must be clearly marked as opinion'},
                {'name': 'provides_reasoning', 'required': True, 'description': 'Provides reasoning for opinions'},
                {'name': 'acknowledges_alternatives', 'required': True, 'description': 'Acknowledges alternative viewpoints'},
                {'name': 'avoids_absolutism', 'required': True, 'description': 'Avoids absolute statements without evidence'},
                {'name': 'experience_disclosure', 'required': True, 'description': 'Discloses basis for opinion'},
                {'name': 'invites_discussion', 'required': False, 'description': 'Invites further discussion'},
                {'name': 'acceptable_length', 'required': True, 'description': 'Content must be of appropriate length'}
            ]
        }
        
        # Rule detector patterns (simplified regex patterns)
        self.rule_detectors = {
            'has_clear_headline': r'^[^\.!?]{10,100}[\.\s]*$',
            'cites_source': r'(according to|reported by|published (by|in)|via|source)',
            'includes_url': r'https?://[^\s]+',
            'avoids_clickbait': r'(!{2,}|\?{2,}|shocking|won\'t believe|mind-?blown)',
            'presents_balanced_view': r'(however|on the other hand|conversely|but|while)',
            'has_relevant_details': r'(\d+(\.\d+)?(GB|MB|TB|Hz|GHz|MHz)|\d+\s*%|\$\s*\d+)',
            'uses_qualifying_language': r'(reportedly|allegedly|according to|may|might|could|appears)',
            'discloses_experience_level': r'((I|we) (have used|tried|tested|reviewed)|my experience|from my testing)',
            'lists_pros_cons': r'(pros?:.+cons?:|advantages?.+disadvantages?|benefits?.+drawbacks?)',
            'specific_details': r'(features include|specifications|dimensions|compatibility)',
            'clear_recommendation': r'(recommend|ideal for|perfect for|suitable for|best for)',
            'comparable_alternatives': r'(alternatives include|similar products|comparable|in contrast to)',
            'clearly_marked_opinion': r'(in my opinion|I (think|believe|feel)|my (take|view|perspective))',
            'provides_reasoning': r'(because|since|due to|as a result of|the reason)',
            'acknowledges_alternatives': r'(others may|some might|another perspective|some argue)',
            'avoids_absolutism': r'(always|never|everyone|no one|nobody|all|none)',
            'experience_disclosure': r'(based on (my|our) experience|from what I\'ve seen|in my practice)',
            'invites_discussion': r'(what (do|are) you think|your thoughts|let me know|share your)',
            'acceptable_length': None  # This requires actual character counting
        }
        
    def evaluate_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        Evaluate content against the quality rules for its type.
        
        Args:
            content: The content to evaluate
            content_type: The type of content (tech_news, product_review, opinion)
            
        Returns:
            Dictionary with rule compliance results and suggestions
        """
        if content_type not in self.rules:
            content_type = 'tech_news'  # Default fallback
            
        applicable_rules = self.rules[content_type]
        results = {}
        failed_required = []
        suggestions = []
        
        # Check content against each rule
        for rule in applicable_rules:
            rule_name = rule['name']
            required = rule['required']
            
            # Special case for length check
            if rule_name == 'acceptable_length':
                # For different platforms, length requirements vary
                min_length = 50  # Minimum sensible length
                max_length = 5000  # Maximum sensible length
                content_length = len(content)
                
                compliance = min_length <= content_length <= max_length
                
                if not compliance:
                    if content_length < min_length:
                        suggestions.append(f"Content is too short. Add more details (minimum {min_length} characters).")
                    else:
                        suggestions.append(f"Content is too long. Consider shortening (maximum {max_length} characters).")
            else:
                # For regex-based rules
                pattern = self.rule_detectors.get(rule_name)
                
                if pattern:
                    # For 'avoids_clickbait', we want to NOT match the pattern
                    if rule_name == 'avoids_clickbait':
                        compliance = not bool(re.search(pattern, content, re.IGNORECASE))
                    # For 'avoids_absolutism', we want to NOT match the pattern
                    elif rule_name == 'avoids_absolutism':
                        compliance = not bool(re.search(pattern, content, re.IGNORECASE))
                    else:
                        compliance = bool(re.search(pattern, content, re.IGNORECASE))
                else:
                    # Default to compliant if no pattern defined
                    compliance = True
            
            results[rule_name] = compliance
            
            # Add to failed required list and suggestions if necessary
            if required and not compliance:
                failed_required.append(rule_name)
                suggestions.append(f"{rule['description']}")
            
        # Calculate overall compliance percentage
        total_rules = len(applicable_rules)
        compliant_rules = sum(1 for rule_result in results.values() if rule_result)
        compliance_percentage = (compliant_rules / total_rules) * 100 if total_rules > 0 else 0
        
        return {
            'content_type': content_type,
            'overall_compliance': round(compliance_percentage, 1),
            'rule_results': results,
            'failed_required_rules': failed_required,
            'improvement_suggestions': suggestions,
            'is_publishable': len(failed_required) == 0
        }

class PostEnhancementModule:
    """
    Tools to improve post quality:
    - Structure formatter
    - Source validator
    - Fact-checking prompts
    - Disclosure generator
    """
    
    def __init__(self):
        self.templates = TransparencyTemplates()
        self.rules_engine = ContentQualityRulesEngine()
        
    def enhance_content(self, content: str, content_type: str, 
                        source_url: Optional[str] = None,
                        knowledge_level: str = 'observer',
                        topic: str = '',
                        **kwargs) -> Dict[str, Any]:
        """
        Enhance content quality by applying improvements based on rules and templates.
        
        Args:
            content: The content to enhance
            content_type: Type of content (tech_news, product_review, opinion)
            source_url: Original source URL if applicable
            knowledge_level: Level of knowledge on the topic
            topic: The topic of the content
            **kwargs: Additional parameters for specific templates
            
        Returns:
            Dictionary with enhanced content and improvement metrics
        """
        # First evaluate content against rules
        evaluation = self.rules_engine.evaluate_content(content, content_type)
        original_score = evaluation['overall_compliance']
        
        # Create enhanced content
        enhanced_content = content
        enhancements_applied = []
        
        # Check for clickbait headlines and fix if possible
        # Do this first to ensure we don't embed clickbait in source attribution
        if not evaluation['rule_results'].get('avoids_clickbait', True):
            lines = enhanced_content.splitlines()
            if lines:
                headline = lines[0]
                # Remove excessive punctuation and clickbait phrases
                cleaned_headline = re.sub(r'!{2,}', '!', headline)
                cleaned_headline = re.sub(r'\?{2,}', '?', cleaned_headline)
                
                # Remove clickbait words with a more comprehensive pattern
                clickbait_words = [
                    r'shocking', r'mind-?blown', r'won\'t believe', 
                    r'amazing', r'incredible', r'unbelievable', 
                    r'insane', r'crazy', r'breathtaking', r'revolutionary',
                    r'game-?changer', r'break the internet', r'changed forever'
                ]
                
                for word in clickbait_words:
                    cleaned_headline = re.sub(word, '', cleaned_headline, flags=re.IGNORECASE)
                
                # Clean up extra spaces and title case if needed
                cleaned_headline = re.sub(r'\s+', ' ', cleaned_headline).strip()
                
                if headline != cleaned_headline and cleaned_headline:
                    # Use rest of content but with new headline
                    enhanced_content = cleaned_headline + '\n' + '\n'.join(lines[1:])
                    enhancements_applied.append('Removed clickbait elements from headline')
        
        # Apply source attribution if missing
        if content_type == 'tech_news' and not evaluation['rule_results'].get('cites_source', True):
            if 'source' in kwargs:
                source_template = self.templates.get_source_attribution('direct', kwargs['source'], '')
                # Insert at beginning if no clear headline, or after headline
                if re.match(r'^[^\.!?]{10,100}[\.\s]*$', enhanced_content.splitlines()[0] if enhanced_content.splitlines() else ''):
                    lines = enhanced_content.splitlines()
                    headline = lines[0] if lines else ''
                    content_body = '\n'.join(lines[1:]) if len(lines) > 1 else ''
                    enhanced_content = f"{headline}\n\n{source_template}{content_body}"
                else:
                    enhanced_content = f"{source_template}{enhanced_content}"
                enhancements_applied.append('Added source attribution')
        
        # Add knowledge level disclosure if needed for reviews/opinions
        if content_type in ('product_review', 'opinion'):
            if not evaluation['rule_results'].get('discloses_experience_level', True):
                knowledge_template = self.templates.get_knowledge_disclosure(knowledge_level, topic, '')
                lines = enhanced_content.splitlines()
                headline = lines[0] if lines else ''
                content_body = '\n'.join(lines[1:]) if len(lines) > 1 else enhanced_content
                enhanced_content = f"{headline}\n\n{knowledge_template}{content_body}"
                enhancements_applied.append('Added knowledge level disclosure')
        
        # Add balanced view if missing
        if not evaluation['rule_results'].get('presents_balanced_view', True):
            if content_type == 'tech_news':
                # Add a balanced perspective section
                if 'implications' in kwargs:
                    balance_template = self.templates.get_balance_indicator(
                        'balanced_view',
                        positive_aspects=kwargs.get('positive_aspects', 'this technology offers potential advancements'),
                        negative_aspects=kwargs.get('negative_aspects', 'there are still questions about its practical applications')
                    )
                    if not enhanced_content.endswith('\n'):
                        enhanced_content += '\n\n'
                    else:
                        enhanced_content += '\n'
                    enhanced_content += balance_template
                    enhancements_applied.append('Added balanced perspective')
        
        # Ensure appropriate length
        if not evaluation['rule_results'].get('acceptable_length', True):
            content_length = len(enhanced_content)
            if content_length < 50:  # Too short
                if 'additional_details' in kwargs:
                    enhanced_content += f"\n\n{kwargs['additional_details']}"
                    enhancements_applied.append('Added more details to meet length requirements')
            elif content_length > 5000:  # Too long
                # This would require more sophisticated summarization
                # We'll just note it as an enhancement that would be needed
                enhancements_applied.append('Content exceeds maximum length - needs manual shortening')
        
        # Re-evaluate enhanced content
        enhanced_evaluation = self.rules_engine.evaluate_content(enhanced_content, content_type)
        enhanced_score = enhanced_evaluation['overall_compliance']
        
        return {
            'original_content': content,
            'enhanced_content': enhanced_content,
            'original_score': original_score,
            'enhanced_score': enhanced_score,
            'enhancements_applied': enhancements_applied,
            'remaining_issues': enhanced_evaluation['improvement_suggestions']
        }

class ContentEnhancementSchema(BaseModel):
    """Schema for content enhancement."""
    content: str = Field(description="The content to enhance")
    content_type: str = Field(description="Type of content (tech_news, product_review, opinion)")
    source_url: Optional[str] = Field(None, description="URL of the original source")
    knowledge_level: Optional[str] = Field("observer", description="Level of knowledge on the topic")
    topic: Optional[str] = Field("", description="The topic of the content")
    source: Optional[str] = Field(None, description="The source of the information")
    positive_aspects: Optional[str] = Field(None, description="Positive aspects to highlight")
    negative_aspects: Optional[str] = Field(None, description="Negative aspects to acknowledge")
    additional_details: Optional[str] = Field(None, description="Additional details to include")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        valid_types = ['tech_news', 'product_review', 'opinion', 'analysis', 'tutorial', 'announcement']
        if v not in valid_types:
            raise ValueError(f"content_type must be one of {valid_types}")
        return v
    
    @validator('knowledge_level')
    def validate_knowledge_level(cls, v):
        if v:
            valid_levels = ['expert', 'intermediate', 'beginner', 'observer', 'research_only']
            if v not in valid_levels:
                raise ValueError(f"knowledge_level must be one of {valid_levels}")
        return v

class ContentEnhancementTool(BaseTool):
    """Tool to enhance content quality."""
    name: str = "Enhance Content Quality"
    description: str = """
    Enhance content quality by applying improvements based on rules and templates.
    Checks for and addresses issues with:
    - Source attribution
    - Knowledge level disclosure
    - Balance in perspectives
    - Appropriate length
    - Clickbait avoidance
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._enhancer = PostEnhancementModule()
    
    def _run(self, content: str, content_type: str, source_url: Optional[str] = None,
            knowledge_level: str = 'observer', topic: str = '', source: Optional[str] = None,
            positive_aspects: Optional[str] = None, negative_aspects: Optional[str] = None,
            additional_details: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the content enhancement process.
        
        Args:
            content: The content to enhance
            content_type: Type of content
            source_url: URL of original source
            knowledge_level: Level of knowledge on topic
            topic: Content topic
            source: Information source
            positive_aspects: Positive aspects to highlight
            negative_aspects: Negative aspects to acknowledge
            additional_details: Extra details to include
            
        Returns:
            Dictionary with enhanced content and improvement metrics
        """
        enhancement_result = self._enhancer.enhance_content(
            content=content,
            content_type=content_type,
            source_url=source_url,
            knowledge_level=knowledge_level,
            topic=topic,
            source=source,
            positive_aspects=positive_aspects,
            negative_aspects=negative_aspects,
            additional_details=additional_details
        )
        
        return enhancement_result
        
# Create BaseTool implementation for ContentCredibilityEvaluator for easy use with CrewAI
class ContentCredibilityEvaluatorTool(BaseTool):
    """Tool to evaluate content credibility."""
    name: str = "Evaluate Content Credibility"
    description: str = """
    Evaluate content for credibility factors including source attribution,
    factual claims, verification status, and appropriate transparency.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._evaluator = ContentCredibilityEvaluator()
    
    def _run(self, content: str, source_url: Optional[str] = None, 
            content_type: str = "tech_news", 
            claimed_facts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the credibility evaluation.
        
        Args:
            content: The content to evaluate
            source_url: URL of the original source
            content_type: Type of content
            claimed_facts: List of factual claims
            
        Returns:
            Dictionary with credibility scores and suggestions
        """
        return self._evaluator._run(
            content=content,
            source_url=source_url,
            content_type=content_type,
            claimed_facts=claimed_facts
        )

# Create BaseTool implementation for ContentQualityRulesEngine for easy use with CrewAI
class ContentQualityRulesTool(BaseTool):
    """Tool to evaluate content against quality rules."""
    name: str = "Evaluate Content Quality Rules"
    description: str = """
    Evaluate content against quality rules for its type.
    Checks structure, facts, sources, disclosures, etc.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rules_engine = ContentQualityRulesEngine()
    
    def _run(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        Run the quality rules evaluation.
        
        Args:
            content: The content to evaluate
            content_type: Type of content
            
        Returns:
            Dictionary with rule compliance results and suggestions
        """
        return self._rules_engine.evaluate_content(
            content=content,
            content_type=content_type
        ) 