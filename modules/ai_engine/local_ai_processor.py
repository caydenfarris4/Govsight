"""
Local AI Processor
Uses lightweight AI libraries for fast, privacy-focused processing
No external API calls - everything runs locally
"""

import re
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import streamlit as st

# Import available AI/ML libraries
try:
    import pandas as pd
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import LogisticRegression
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

class LocalAIProcessor:
    """Local AI processing using built-in Python and lightweight libraries"""
    
    def __init__(self):
        # Financial keywords for municipal government
        self.financial_keywords = {
            'revenue': ['revenue', 'income', 'tax', 'fees', 'grants', 'federal', 'state'],
            'expenses': ['expense', 'cost', 'salary', 'benefits', 'supplies', 'equipment', 'contract'],
            'budget': ['budget', 'allocation', 'appropriation', 'fund', 'reserve'],
            'assets': ['assets', 'property', 'infrastructure', 'equipment', 'vehicles'],
            'liabilities': ['debt', 'liability', 'bond', 'loan', 'obligation'],
            'personnel': ['employee', 'staff', 'payroll', 'benefits', 'pension', 'hiring']
        }
        
        # Sentiment analysis patterns (simple rule-based)
        self.positive_patterns = [
            r'\b(good|great|excellent|positive|success|improve|increase|growth)\b',
            r'\b(efficient|effective|beneficial|advantageous|profitable)\b'
        ]
        
        self.negative_patterns = [
            r'\b(bad|poor|negative|decline|decrease|loss|problem|issue)\b',
            r'\b(inefficient|wasteful|concerning|deficit|shortfall)\b'
        ]
        
        # Initialize ML models if sklearn is available
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            self.sentiment_classifier = None
            self.category_classifier = None
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Comprehensive text analysis using local processing"""
        start_time = time.time()
        
        analysis = {
            'success': True,
            'text_length': len(text),
            'word_count': len(text.split()),
            'sentence_count': len(re.findall(r'[.!?]+', text)),
            'keywords': self.extract_keywords(text)['keywords'],
            'sentiment': self.analyze_sentiment(text)['sentiment'],
            'financial_categories': self.categorize_financial_text(text)['categories'],
            'processing_time': time.time() - start_time
        }
        
        # Add readability if available
        if TEXTSTAT_AVAILABLE:
            analysis['readability_score'] = textstat.flesch_reading_ease(text)
            analysis['grade_level'] = textstat.flesch_kincaid_grade(text)
        
        return analysis
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Simple rule-based sentiment analysis"""
        text_lower = text.lower()
        
        positive_count = sum(len(re.findall(pattern, text_lower)) for pattern in self.positive_patterns)
        negative_count = sum(len(re.findall(pattern, text_lower)) for pattern in self.negative_patterns)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            confidence = min(0.9, 0.5 + (positive_count - negative_count) / 10)
        elif negative_count > positive_count:
            sentiment = 'negative'
            confidence = min(0.9, 0.5 + (negative_count - positive_count) / 10)
        else:
            sentiment = 'neutral'
            confidence = 0.5
        
        return {
            'success': True,
            'sentiment': sentiment,
            'confidence': confidence,
            'positive_indicators': positive_count,
            'negative_indicators': negative_count
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> Dict[str, Any]:
        """Extract keywords using frequency analysis and TF-IDF if available"""
        
        # Clean text
        text_clean = re.sub(r'[^\w\s]', '', text.lower())
        words = [word for word in text_clean.split() if len(word) > 3]
        
        # Remove common stop words
        stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'about'}
        words = [word for word in words if word not in stop_words]
        
        if SKLEARN_AVAILABLE and len(words) > 5:
            # Use TF-IDF for better keyword extraction
            try:
                tfidf_matrix = self.tfidf_vectorizer.fit_transform([' '.join(words)])
                feature_names = self.tfidf_vectorizer.get_feature_names_out()
                tfidf_scores = tfidf_matrix.toarray()[0]
                
                # Get top keywords by TF-IDF score
                keyword_scores = list(zip(feature_names, tfidf_scores))
                keyword_scores.sort(key=lambda x: x[1], reverse=True)
                keywords = [kw[0] for kw in keyword_scores[:max_keywords] if kw[1] > 0]
                
            except Exception:
                # Fallback to frequency analysis
                keywords = [word for word, count in Counter(words).most_common(max_keywords)]
        else:
            # Simple frequency analysis
            keywords = [word for word, count in Counter(words).most_common(max_keywords)]
        
        return {
            'success': True,
            'keywords': keywords,
            'total_unique_words': len(set(words))
        }
    
    def categorize_financial_text(self, text: str) -> Dict[str, Any]:
        """Categorize text based on financial keywords"""
        text_lower = text.lower()
        categories_found = {}
        
        for category, keywords in self.financial_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                categories_found[category] = matches
        
        # Sort by relevance
        sorted_categories = sorted(categories_found.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'success': True,
            'categories': [cat for cat, count in sorted_categories],
            'category_scores': dict(sorted_categories),
            'primary_category': sorted_categories[0][0] if sorted_categories else 'general'
        }
    
    def summarize_text(self, text: str, max_sentences: int = 3) -> Dict[str, Any]:
        """Simple extractive summarization using sentence scoring"""
        
        if len(text) < 100:
            return {
                'success': True,
                'summary': text,
                'method': 'text_too_short'
            }
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(sentences) <= max_sentences:
            return {
                'success': True,
                'summary': text,
                'method': 'no_reduction_needed'
            }
        
        # Score sentences based on keyword frequency and position
        sentence_scores = {}
        keywords = self.extract_keywords(text, max_keywords=20)['keywords']
        
        for i, sentence in enumerate(sentences):
            score = 0
            sentence_lower = sentence.lower()
            
            # Keyword frequency score
            for keyword in keywords:
                if keyword in sentence_lower:
                    score += 1
            
            # Position score (first and last sentences are important)
            if i == 0 or i == len(sentences) - 1:
                score += 2
            elif i < len(sentences) * 0.3:  # First third
                score += 1
            
            # Length score (medium length sentences preferred)
            if 20 < len(sentence.split()) < 50:
                score += 1
            
            sentence_scores[i] = score
        
        # Select top sentences
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
        top_sentences.sort(key=lambda x: x[0])  # Sort by original order
        
        summary_sentences = [sentences[i] for i, score in top_sentences]
        summary = '. '.join(summary_sentences) + '.'
        
        return {
            'success': True,
            'summary': summary,
            'method': 'extractive',
            'original_sentences': len(sentences),
            'summary_sentences': len(summary_sentences),
            'compression_ratio': len(summary) / len(text)
        }
    
    def classify_data(self, text: str, categories: List[str]) -> Dict[str, Any]:
        """Classify text into provided categories using keyword matching"""
        
        if not categories:
            return {'success': False, 'error': 'No categories provided'}
        
        text_lower = text.lower()
        category_scores = {}
        
        for category in categories:
            # Simple keyword matching - could be enhanced with ML
            category_words = category.lower().split()
            score = sum(1 for word in category_words if word in text_lower)
            
            # Boost score for exact category mention
            if category.lower() in text_lower:
                score += 5
            
            category_scores[category] = score
        
        # Find best match
        if max(category_scores.values()) == 0:
            best_category = 'unclassified'
            confidence = 0.1
        else:
            best_category = max(category_scores, key=category_scores.get)
            max_score = category_scores[best_category]
            confidence = min(0.95, max_score / (len(text.split()) * 0.1))
        
        return {
            'success': True,
            'classification': best_category,
            'confidence': confidence,
            'all_scores': category_scores
        }
    
    def recognize_patterns(self, text: str) -> Dict[str, Any]:
        """Recognize common patterns in text"""
        
        patterns = {
            'dates': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'dollar_amounts': r'\$[\d,]+\.?\d*',
            'percentages': r'\d+\.?\d*%',
            'phone_numbers': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email_addresses': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'account_numbers': r'\b\d{4}[-.]?\d{4}[-.]?\d{4}[-.]?\d{4}\b',
            'department_codes': r'\b[A-Z]{2,4}-\d{2,4}\b'
        }
        
        found_patterns = {}
        for pattern_name, pattern_regex in patterns.items():
            matches = re.findall(pattern_regex, text)
            if matches:
                found_patterns[pattern_name] = {
                    'count': len(matches),
                    'examples': matches[:3]  # Show first 3 examples
                }
        
        return {
            'success': True,
            'patterns_found': found_patterns,
            'total_patterns': len(found_patterns)
        }
    
    def simple_question_answer(self, text: str, question: str) -> Dict[str, Any]:
        """Simple Q&A using keyword matching and context extraction"""
        
        if not question:
            return {'success': False, 'error': 'No question provided'}
        
        text_sentences = re.split(r'[.!?]+', text)
        text_sentences = [s.strip() for s in text_sentences if len(s.strip()) > 5]
        
        question_lower = question.lower()
        question_words = set(question_lower.split())
        
        # Score sentences based on question word overlap
        sentence_scores = {}
        for i, sentence in enumerate(text_sentences):
            sentence_lower = sentence.lower()
            sentence_words = set(sentence_lower.split())
            
            # Calculate overlap
            overlap = len(question_words.intersection(sentence_words))
            
            # Boost score for question words
            question_indicators = ['what', 'when', 'where', 'who', 'why', 'how']
            for indicator in question_indicators:
                if indicator in question_lower and indicator in sentence_lower:
                    overlap += 2
            
            sentence_scores[i] = overlap
        
        # Find best matching sentence
        if not sentence_scores or max(sentence_scores.values()) == 0:
            return {
                'success': True,
                'answer': 'I could not find a specific answer to that question in the provided text.',
                'confidence': 0.1
            }
        
        best_sentence_idx = max(sentence_scores, key=sentence_scores.get)
        best_sentence = text_sentences[best_sentence_idx]
        confidence = min(0.8, sentence_scores[best_sentence_idx] / len(question_words))
        
        return {
            'success': True,
            'answer': best_sentence,
            'confidence': confidence,
            'source_sentence_index': best_sentence_idx
        }
    
    def municipal_specific_analysis(self, text: str) -> Dict[str, Any]:
        """Analysis specific to municipal government needs"""
        
        municipal_indicators = {
            'citizen_services': ['citizen', 'resident', 'public', 'service', 'community'],
            'infrastructure': ['road', 'water', 'sewer', 'bridge', 'facility', 'maintenance'],
            'public_safety': ['police', 'fire', 'emergency', 'safety', 'security'],
            'governance': ['council', 'mayor', 'ordinance', 'policy', 'meeting', 'vote'],
            'finance': ['budget', 'revenue', 'tax', 'fund', 'audit', 'fiscal'],
            'planning': ['development', 'zoning', 'permit', 'construction', 'land_use']
        }
        
        text_lower = text.lower()
        department_scores = {}
        
        for dept, keywords in municipal_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                department_scores[dept] = score
        
        return {
            'success': True,
            'municipal_categories': department_scores,
            'primary_focus': max(department_scores, key=department_scores.get) if department_scores else 'general',
            'municipal_relevance_score': sum(department_scores.values())
        }