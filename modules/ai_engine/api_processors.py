"""
API Processors for Advanced AI Tasks
Handles external API calls for complex AI operations
Integrates with existing OpenAI, Anthropic, and Perplexity implementations
"""

import os
import time
from typing import Dict, Any, List, Optional
import streamlit as st

class BaseAPIProcessor:
    """Base class for API processors"""
    
    def __init__(self):
        self.request_count = 0
        self.total_cost = 0.0
        self.processing_time = 0.0
    
    def process_task(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process task using API - to be overridden by subclasses"""
        raise NotImplementedError
    
    def estimate_cost(self, content: str, task_type: str) -> float:
        """Estimate API cost"""
        # Base estimation - override in subclasses
        return len(content) / 1000 * 0.002

class OpenAIProcessor(BaseAPIProcessor):
    """OpenAI API processor for advanced tasks"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
    
    def process_task(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process task using OpenAI API"""
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            # Task-specific prompt generation
            prompt = self._generate_prompt(task_type, content, **kwargs)
            
            start_time = time.time()
            
            # Use GPT-4 for complex tasks, GPT-3.5 for simpler ones
            model = self._select_model(task_type)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(task_type)},
                    {"role": "user", "content": prompt}
                ],
                temperature=self._get_temperature(task_type),
                max_tokens=self._get_max_tokens(task_type)
            )
            
            processing_time = time.time() - start_time
            self.processing_time += processing_time
            self.request_count += 1
            
            result = {
                'success': True,
                'result': response.choices[0].message.content,
                'model_used': model,
                'processing_time': processing_time,
                'tokens_used': response.usage.total_tokens,
                'estimated_cost': response.usage.total_tokens * 0.00002,  # Rough estimate
                'provider': 'openai'
            }
            
            # Parse structured results if needed
            if task_type in ['analysis', 'categorization']:
                result['parsed_result'] = self._parse_structured_response(result['result'])
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'openai'
            }
    
    def _generate_prompt(self, task_type: str, content: str, **kwargs) -> str:
        """Generate task-specific prompts"""
        
        prompts = {
            'complex_analysis': f"""
            Analyze the following municipal data and provide detailed insights:
            
            {content}
            
            Please provide:
            1. Key findings
            2. Trends and patterns
            3. Recommendations for action
            4. Risk factors to consider
            """,
            
            'strategic_planning': f"""
            Based on the following information, help develop a strategic plan:
            
            {content}
            
            Please provide:
            1. Strategic objectives
            2. Key initiatives
            3. Timeline recommendations
            4. Success metrics
            5. Potential challenges and mitigation strategies
            """,
            
            'policy_analysis': f"""
            Analyze the following policy or regulatory content:
            
            {content}
            
            Please provide:
            1. Policy implications
            2. Compliance requirements
            3. Implementation considerations
            4. Potential impacts on municipal operations
            """,
            
            'grant_writing': f"""
            Help develop grant proposal content based on:
            
            {content}
            
            Please provide:
            1. Problem statement
            2. Proposed solution
            3. Expected outcomes
            4. Budget considerations
            5. Implementation timeline
            """
        }
        
        return prompts.get(task_type, f"Please analyze and provide insights on the following: {content}")
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get system prompt for task type"""
        
        base_prompt = """You are an AI assistant specialized in municipal government operations and financial analysis. 
        Provide accurate, actionable insights that help government officials make informed decisions. 
        Focus on practical recommendations and consider regulatory compliance."""
        
        specialized_prompts = {
            'financial_analysis': base_prompt + " You are particularly focused on municipal financial analysis, budgeting, and fiscal responsibility.",
            'policy_analysis': base_prompt + " You specialize in policy analysis and regulatory compliance for local governments.",
            'strategic_planning': base_prompt + " You focus on strategic planning and long-term municipal development.",
            'grant_writing': base_prompt + " You specialize in grant writing and federal funding opportunities for municipalities."
        }
        
        return specialized_prompts.get(task_type, base_prompt)
    
    def _select_model(self, task_type: str) -> str:
        """Select appropriate model based on task complexity"""
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        complex_tasks = ['strategic_planning', 'policy_analysis', 'grant_writing', 'complex_analysis']
        
        if task_type in complex_tasks:
            return "gpt-5"  # Use latest model for complex tasks
        else:
            return "gpt-4"  # Use GPT-4 for standard tasks
    
    def _get_temperature(self, task_type: str) -> float:
        """Get temperature setting for task type"""
        
        creative_tasks = ['grant_writing', 'strategic_planning']
        if task_type in creative_tasks:
            return 0.7
        else:
            return 0.3  # More deterministic for analysis tasks
    
    def _get_max_tokens(self, task_type: str) -> int:
        """Get max tokens for task type"""
        
        long_form_tasks = ['strategic_planning', 'policy_analysis', 'grant_writing']
        if task_type in long_form_tasks:
            return 2000
        else:
            return 1000
    
    def _parse_structured_response(self, response: str) -> Dict[str, Any]:
        """Parse structured responses into components"""
        
        # Simple parsing - could be enhanced
        sections = {}
        current_section = "main"
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('##') or line.startswith('**'):
                # New section header
                current_section = line.replace('#', '').replace('*', '').strip().lower()
                sections[current_section] = []
            elif line and current_section in sections:
                sections[current_section].append(line)
        
        return sections

class AnthropicProcessor(BaseAPIProcessor):
    """Anthropic Claude processor for advanced reasoning tasks"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found in environment variables")
    
    def process_task(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process task using Anthropic Claude API"""
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            start_time = time.time()
            
            # The newest Anthropic model is "claude-sonnet-4-20250514"
            # do not change this unless explicitly requested by the user
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": self._generate_anthropic_prompt(task_type, content, **kwargs)
                }]
            )
            
            processing_time = time.time() - start_time
            self.processing_time += processing_time
            self.request_count += 1
            
            return {
                'success': True,
                'result': response.content[0].text,
                'model_used': "claude-sonnet-4-20250514",
                'processing_time': processing_time,
                'provider': 'anthropic'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'anthropic'
            }
    
    def _generate_anthropic_prompt(self, task_type: str, content: str, **kwargs) -> str:
        """Generate Claude-optimized prompts"""
        
        claude_prompts = {
            'complex_reasoning': f"""
            I need you to analyze this municipal information and provide deep insights with clear reasoning:
            
            {content}
            
            Please think through this step by step and provide:
            1. Your analysis process
            2. Key insights discovered
            3. Logical connections between different elements
            4. Practical recommendations
            """,
            
            'policy_analysis': f"""
            Please analyze this policy document with careful attention to implications:
            
            {content}
            
            Consider:
            1. Legal and regulatory implications
            2. Operational impacts
            3. Stakeholder effects
            4. Implementation challenges
            5. Recommendations for compliance
            """
        }
        
        return claude_prompts.get(task_type, f"Please provide a thorough analysis of: {content}")

class PerplexityProcessor(BaseAPIProcessor):
    """Perplexity processor for research and current information tasks"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not self.api_key:
            st.warning("Perplexity API key not found - research features will be limited")
            self.api_key = None
    
    def process_task(self, task_type: str, content: str, **kwargs) -> Dict[str, Any]:
        """Process research tasks using Perplexity API"""
        
        if not self.api_key:
            return {
                'success': False,
                'error': 'Perplexity API key not configured',
                'provider': 'perplexity'
            }
        
        try:
            import requests
            
            start_time = time.time()
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{
                        "role": "user",
                        "content": self._generate_research_prompt(task_type, content, **kwargs)
                    }],
                    "temperature": 0.2,
                    "search_recency_filter": "month"
                }
            )
            
            processing_time = time.time() - start_time
            self.processing_time += processing_time
            self.request_count += 1
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'result': result['choices'][0]['message']['content'],
                    'citations': result.get('citations', []),
                    'model_used': "llama-3.1-sonar-small-128k-online",
                    'processing_time': processing_time,
                    'provider': 'perplexity'
                }
            else:
                return {
                    'success': False,
                    'error': f"API error: {response.status_code}",
                    'provider': 'perplexity'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'perplexity'
            }
    
    def _generate_research_prompt(self, task_type: str, content: str, **kwargs) -> str:
        """Generate research-focused prompts"""
        
        research_prompts = {
            'current_events': f"""
            Research current information and recent developments related to:
            {content}
            
            Focus on information from the last 6 months and provide sources.
            """,
            
            'grant_opportunities': f"""
            Research current federal and state grant opportunities for:
            {content}
            
            Include application deadlines, requirements, and funding amounts.
            """,
            
            'regulatory_updates': f"""
            Find recent regulatory changes and updates related to:
            {content}
            
            Focus on changes that would affect municipal operations.
            """
        }
        
        return research_prompts.get(task_type, f"Research and provide current information about: {content}")

# Factory function to get appropriate processor
def get_api_processor(provider: str):
    """Get API processor for specified provider"""
    
    processors = {
        'openai': OpenAIProcessor,
        'anthropic': AnthropicProcessor,
        'perplexity': PerplexityProcessor
    }
    
    if provider not in processors:
        raise ValueError(f"Unknown provider: {provider}")
    
    return processors[provider]()