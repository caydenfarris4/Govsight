"""
Hybrid AI Router
Intelligently routes tasks between local AI processing and external APIs
Optimizes for speed, cost, and capability
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import streamlit as st

class TaskComplexity(Enum):
    SIMPLE = "simple"        # Local processing
    MODERATE = "moderate"    # Local with API fallback
    COMPLEX = "complex"      # API required
    ADVANCED = "advanced"    # Latest API models only

class AIProvider(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"

class HybridAIRouter:
    """Routes AI tasks between local processing and external APIs"""
    
    def __init__(self):
        self.local_capabilities = {
            'text_analysis', 'sentiment_analysis', 'keyword_extraction',
            'basic_summarization', 'data_classification', 'pattern_recognition',
            'financial_categorization', 'simple_qa', 'data_validation'
        }
        
        self.api_required_tasks = {
            'complex_reasoning', 'creative_writing', 'code_generation',
            'advanced_analysis', 'multi_document_reasoning', 'strategic_planning',
            'grant_writing', 'policy_analysis', 'legal_interpretation'
        }
        
        # Performance tracking
        self.routing_stats = {
            'local_requests': 0,
            'api_requests': 0,
            'local_time_saved': 0,
            'api_costs_estimated': 0
        }
    
    def classify_task(self, task_type: str, content: str = "", context: Dict[str, Any] = None) -> Tuple[TaskComplexity, AIProvider]:
        """Classify task complexity and determine best AI provider"""
        
        # Simple local tasks
        if task_type in self.local_capabilities:
            return TaskComplexity.SIMPLE, AIProvider.LOCAL
        
        # Content-based classification
        if content:
            # Short content can often be handled locally
            if len(content) < 500 and task_type in ['summarization', 'analysis', 'classification']:
                return TaskComplexity.SIMPLE, AIProvider.LOCAL
            
            # Medium content with simple tasks
            elif len(content) < 2000 and task_type in ['summarization', 'sentiment']:
                return TaskComplexity.MODERATE, AIProvider.LOCAL
        
        # Context-based routing
        if context:
            # Financial data analysis - prefer local for privacy
            if context.get('data_type') == 'financial':
                if task_type in ['analysis', 'categorization', 'validation']:
                    return TaskComplexity.SIMPLE, AIProvider.LOCAL
            
            # Real-time requirements - prefer local
            if context.get('real_time', False):
                return TaskComplexity.MODERATE, AIProvider.LOCAL
        
        # API required tasks
        if task_type in self.api_required_tasks:
            # Use best available API
            if task_type in ['strategic_planning', 'policy_analysis']:
                return TaskComplexity.ADVANCED, AIProvider.ANTHROPIC
            elif task_type in ['research', 'current_events']:
                return TaskComplexity.COMPLEX, AIProvider.PERPLEXITY
            else:
                return TaskComplexity.COMPLEX, AIProvider.OPENAI
        
        # Default to moderate complexity with local processing
        return TaskComplexity.MODERATE, AIProvider.LOCAL
    
    def route_request(self, task_type: str, content: str = "", **kwargs) -> Dict[str, Any]:
        """Route AI request to appropriate processor"""
        
        start_time = time.time()
        context = kwargs.get('context', {})
        
        # Classify the task
        complexity, provider = self.classify_task(task_type, content, context)
        
        try:
            if provider == AIProvider.LOCAL:
                result = self._process_locally(task_type, content, **kwargs)
                self.routing_stats['local_requests'] += 1
                processing_time = time.time() - start_time
                self.routing_stats['local_time_saved'] += max(0, 2.0 - processing_time)  # Assume API would take 2+ seconds
            else:
                result = self._process_via_api(provider, task_type, content, **kwargs)
                self.routing_stats['api_requests'] += 1
                self.routing_stats['api_costs_estimated'] += self._estimate_api_cost(content, task_type)
            
            result['routing_info'] = {
                'provider': provider.value,
                'complexity': complexity.value,
                'processing_time': time.time() - start_time,
                'routed_locally': provider == AIProvider.LOCAL
            }
            
            return result
            
        except Exception as e:
            # Fallback logic
            if provider == AIProvider.LOCAL:
                st.warning(f"Local processing failed, falling back to API: {e}")
                return self._process_via_api(AIProvider.OPENAI, task_type, content, **kwargs)
            else:
                st.error(f"API processing failed: {e}")
                return {'error': str(e), 'success': False}
    
    def _process_locally(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process task using local AI capabilities"""
        from .local_ai_processor import LocalAIProcessor
        
        processor = LocalAIProcessor()
        
        if task_type == 'text_analysis':
            return processor.analyze_text(content)
        elif task_type == 'sentiment_analysis':
            return processor.analyze_sentiment(content)
        elif task_type == 'summarization':
            return processor.summarize_text(content)
        elif task_type == 'keyword_extraction':
            return processor.extract_keywords(content)
        elif task_type == 'financial_categorization':
            return processor.categorize_financial_text(content)
        elif task_type == 'data_classification':
            return processor.classify_data(content, kwargs.get('categories', []))
        elif task_type == 'pattern_recognition':
            return processor.recognize_patterns(content)
        elif task_type == 'simple_qa':
            return processor.simple_question_answer(content, kwargs.get('question', ''))
        else:
            return {'error': f'Local processing not available for task: {task_type}', 'success': False}
    
    def _process_via_api(self, provider: AIProvider, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process task using external API"""
        
        if provider == AIProvider.OPENAI:
            from .api_processors import OpenAIProcessor
            processor = OpenAIProcessor()
        elif provider == AIProvider.ANTHROPIC:
            from .api_processors import AnthropicProcessor  
            processor = AnthropicProcessor()
        elif provider == AIProvider.PERPLEXITY:
            from .api_processors import PerplexityProcessor
            processor = PerplexityProcessor()
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        return processor.process_task(task_type, content, **kwargs)
    
    def _estimate_api_cost(self, content: str, task_type: str) -> float:
        """Estimate API cost for task"""
        # Rough cost estimation based on content length and task type
        base_cost = len(content) / 1000 * 0.002  # ~$0.002 per 1K tokens
        
        task_multiplier = {
            'simple': 1.0,
            'moderate': 1.5,
            'complex': 2.0,
            'advanced': 3.0
        }
        
        return base_cost * task_multiplier.get(task_type, 1.5)
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing performance statistics"""
        total_requests = self.routing_stats['local_requests'] + self.routing_stats['api_requests']
        
        if total_requests == 0:
            return {'message': 'No requests processed yet'}
        
        local_percentage = (self.routing_stats['local_requests'] / total_requests) * 100
        
        return {
            'total_requests': total_requests,
            'local_requests': self.routing_stats['local_requests'],
            'api_requests': self.routing_stats['api_requests'],
            'local_percentage': local_percentage,
            'estimated_time_saved': self.routing_stats['local_time_saved'],
            'estimated_cost_savings': self.routing_stats['local_time_saved'] * 0.01,  # $0.01 per saved second estimate
            'estimated_api_costs': self.routing_stats['api_costs_estimated']
        }
    
    def optimize_for_municipal_use(self):
        """Optimize routing for municipal government use cases"""
        # Prefer local processing for sensitive financial data
        self.local_capabilities.update({
            'budget_analysis', 'revenue_analysis', 'expense_categorization',
            'compliance_checking', 'audit_preparation', 'payroll_analysis'
        })
        
        # Add municipal-specific routing rules
        municipal_local_tasks = {
            'citizen_inquiry_classification', 'permit_categorization',
            'service_request_routing', 'basic_policy_lookup'
        }
        
        self.local_capabilities.update(municipal_local_tasks)

# Global router instance
_hybrid_router = None

def get_hybrid_router() -> HybridAIRouter:
    """Get global hybrid AI router instance"""
    global _hybrid_router
    if _hybrid_router is None:
        _hybrid_router = HybridAIRouter()
        _hybrid_router.optimize_for_municipal_use()
    return _hybrid_router

# Streamlit integration
def init_hybrid_ai_session():
    """Initialize hybrid AI router in Streamlit session"""
    if 'hybrid_ai_router' not in st.session_state:
        st.session_state.hybrid_ai_router = get_hybrid_router()

# Convenience functions for easy integration
def smart_ai_request(task_type: str, content: str = "", **kwargs):
    """Make an AI request with intelligent routing"""
    router = get_hybrid_router()
    return router.route_request(task_type, content, **kwargs)

def get_ai_stats():
    """Get AI routing statistics"""
    router = get_hybrid_router()
    return router.get_routing_stats()