"""
AI Assistant Module

Conversational AI interface for budget questions and document analysis
"""

from .assistant_core import render_ai_assistant
from .document_processor import extract_text_from_document, analyze_document
from .ai_engine import generate_ai_commentary, call_ai_with_context

__all__ = [
    'render_ai_assistant',
    'extract_text_from_document',
    'analyze_document',
    'generate_ai_commentary',
    'call_ai_with_context'
]