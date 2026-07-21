"""
Simple RAG (Retrieval-Augmented Generation) Engine for GovSight
Uses basic TF-IDF and cosine similarity for document retrieval without external dependencies
"""

import sqlite3
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import hashlib

class SimpleRAGEngine:
    """
    Lightweight RAG implementation using TF-IDF for embeddings
    and cosine similarity for retrieval
    """
    
    def __init__(self, index_name: str = "govsight_rag"):
        self.index_name = index_name
        self.index_dir = "rag_indices"
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.documents = []
        self.document_vectors = None
        self.metadata = []
        
        # Create index directory if it doesn't exist
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
        
        # Load existing index if available
        self.load_index()
    
    def create_document_from_db_row(self, table_name: str, row: Dict, 
                                  schema: Dict = None) -> Dict[str, Any]:
        """Convert a database row to a searchable document"""
        
        # Convert numpy types to native Python types for JSON serialization
        def convert_numpy_types(obj):
            """Convert numpy types to native Python types"""
            import numpy as np
            if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            return obj
        
        # Clean row data of numpy types
        clean_row = {k: convert_numpy_types(v) for k, v in row.items()}
        
        # Create text representation of the row
        text_parts = [f"Table: {table_name}"]
        
        # Add column-value pairs
        for key, value in clean_row.items():
            if value is not None:
                # Add field description if available in schema
                if schema and key in schema:
                    text_parts.append(f"{schema[key].get('description', key)}: {value}")
                else:
                    text_parts.append(f"{key}: {value}")
        
        document_text = " | ".join(text_parts)
        
        # Create document ID using clean row data
        try:
            doc_id = hashlib.md5(f"{table_name}_{json.dumps(clean_row, sort_keys=True)}".encode()).hexdigest()
        except Exception:
            # Fallback if JSON serialization still fails
            doc_id = hashlib.md5(f"{table_name}_{str(clean_row)}".encode()).hexdigest()
        
        return {
            'id': doc_id,
            'text': document_text,
            'metadata': {
                'table': table_name,
                'data': clean_row,
                'indexed_at': datetime.now().isoformat()
            }
        }
    
    def index_database_tables(self, db_path: str, tables_to_index: List[str] = None):
        """Index specified tables from a database"""
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get list of tables if not specified
            if tables_to_index is None:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables_to_index = [row[0] for row in cursor.fetchall()]
            
            documents_to_add = []
            
            for table in tables_to_index:
                # Skip system tables
                if table.startswith('sqlite_'):
                    continue
                
                # Get table data
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 1000", conn)
                    
                    # Convert each row to a document
                    for _, row in df.iterrows():
                        doc = self.create_document_from_db_row(table, row.to_dict())
                        documents_to_add.append(doc)
                    
                    print(f"Indexed {len(df)} rows from table {table}")
                    
                except Exception as e:
                    print(f"Error indexing table {table}: {e}")
                    continue
            
            conn.close()
            
            # Add documents to index
            if documents_to_add:
                self.add_documents(documents_to_add)
                print(f"Total documents indexed: {len(documents_to_add)}")
            
        except Exception as e:
            print(f"Error indexing database: {e}")
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the index"""
        
        for doc in documents:
            # Check if document already exists
            if not any(d['id'] == doc['id'] for d in self.documents):
                self.documents.append(doc)
                self.metadata.append(doc.get('metadata', {}))
        
        # Re-vectorize all documents
        if self.documents:
            texts = [doc['text'] for doc in self.documents]
            self.document_vectors = self.vectorizer.fit_transform(texts)
        
        # Save index
        self.save_index()
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        
        if not self.documents or self.document_vectors is None:
            return []
        
        try:
            # Vectorize query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.document_vectors)[0]
            
            # Get top-k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    results.append({
                        'document': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'score': float(similarities[idx])
                    })
            
            return results
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def get_context_for_query(self, query: str, max_context_length: int = 2000) -> str:
        """Get relevant context for a query"""
        
        results = self.search(query, top_k=5)
        
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for result in results:
            doc_text = result['document']['text']
            metadata = result['metadata']
            
            # Format context with source information
            context_entry = f"[Source: {metadata.get('table', 'Unknown')}]\n{doc_text}\n"
            
            if current_length + len(context_entry) <= max_context_length:
                context_parts.append(context_entry)
                current_length += len(context_entry)
            else:
                break
        
        return "\n---\n".join(context_parts)
    
    def save_index(self):
        """Save index to disk"""
        
        index_path = os.path.join(self.index_dir, f"{self.index_name}.json")
        
        try:
            # Get vectorizer params but filter out non-serializable values
            vectorizer_params = self.vectorizer.get_params()
            serializable_params = {}
            for key, value in vectorizer_params.items():
                try:
                    json.dumps(value)  # Test if value is JSON serializable
                    serializable_params[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable values (like class types)
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        serializable_params[key] = value
                    else:
                        serializable_params[key] = str(value)  # Convert to string
            
            index_data = {
                'documents': self.documents,
                'metadata': self.metadata,
                'vectorizer_params': serializable_params
            }
            
            with open(index_path, 'w') as f:
                json.dump(index_data, f, default=str)
            
            # Save vectorizer vocabulary with numpy type conversion
            if hasattr(self.vectorizer, 'vocabulary_'):
                vocab_path = os.path.join(self.index_dir, f"{self.index_name}_vocab.json")
                # Convert numpy int64 values to regular Python ints for JSON serialization
                serializable_vocab = {k: int(v) for k, v in self.vectorizer.vocabulary_.items()}
                with open(vocab_path, 'w') as f:
                    json.dump(serializable_vocab, f)
            
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def load_index(self):
        """Load index from disk with defensive handling of legacy formats"""
        
        index_path = os.path.join(self.index_dir, f"{self.index_name}.json")
        vocab_path = os.path.join(self.index_dir, f"{self.index_name}_vocab.json")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                
                # Validate and clean the loaded data
                self.documents = self._validate_documents(index_data.get('documents', []))
                self.metadata = self._validate_metadata(index_data.get('metadata', []))
                
                # Re-vectorize documents if we have them
                if self.documents:
                    texts = [doc['text'] for doc in self.documents]
                    
                    # Load vocabulary if available with defensive handling
                    if os.path.exists(vocab_path):
                        vocabulary = self._load_vocabulary_safely(vocab_path)
                        if vocabulary:
                            self.vectorizer = TfidfVectorizer(
                                max_features=5000, 
                                stop_words='english',
                                vocabulary=vocabulary
                            )
                    
                    self.document_vectors = self.vectorizer.fit_transform(texts)
                    print(f"Loaded {len(self.documents)} documents from index")
                
            except Exception as e:
                print(f"Error loading index: {e}")
                print("Clearing corrupted index and starting fresh...")
                self.clear_index()
                
    def _validate_documents(self, documents):
        """Validate and clean document data"""
        cleaned_docs = []
        for doc in documents:
            if isinstance(doc, dict) and 'id' in doc and 'text' in doc:
                # Ensure all values are JSON serializable
                try:
                    json.dumps(doc)
                    cleaned_docs.append(doc)
                except (TypeError, ValueError):
                    # Skip corrupted documents
                    continue
        return cleaned_docs
    
    def _validate_metadata(self, metadata_list):
        """Validate and clean metadata"""
        cleaned_metadata = []
        for meta in metadata_list:
            if isinstance(meta, dict):
                try:
                    # Ensure metadata is JSON serializable
                    json.dumps(meta)
                    cleaned_metadata.append(meta)
                except (TypeError, ValueError):
                    # Create empty metadata for corrupted entries
                    cleaned_metadata.append({})
            else:
                cleaned_metadata.append({})
        return cleaned_metadata
    
    def _load_vocabulary_safely(self, vocab_path):
        """Safely load vocabulary with fallback for different formats"""
        try:
            with open(vocab_path, 'r') as f:
                vocab_data = json.load(f)
            
            # Handle different vocabulary formats
            if isinstance(vocab_data, dict):
                # Check if it's a nested format
                if 'vocabulary' in vocab_data:
                    vocabulary = vocab_data['vocabulary']
                else:
                    vocabulary = vocab_data
                
                # Validate that all values are integers (required for TfidfVectorizer)
                if vocabulary and all(isinstance(v, int) for v in vocabulary.values()):
                    return vocabulary
                else:
                    print("Invalid vocabulary format, regenerating...")
                    return None
            else:
                print("Vocabulary data is not a dictionary, regenerating...")
                return None
                
        except Exception as e:
            print(f"Error loading vocabulary: {e}")
            return None
    
    def clear_index(self):
        """Clear the current index"""
        
        self.documents = []
        self.document_vectors = None
        self.metadata = []
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        
        # Remove saved index files
        index_path = os.path.join(self.index_dir, f"{self.index_name}.json")
        vocab_path = os.path.join(self.index_dir, f"{self.index_name}_vocab.json")
        
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(vocab_path):
            os.remove(vocab_path)


class RAGQueryProcessor:
    """Process queries using RAG with OpenAI integration"""
    
    def __init__(self, rag_engine: SimpleRAGEngine, openai_client=None):
        self.rag_engine = rag_engine
        self.openai_client = openai_client
    
    def process_query(self, query: str, use_openai: bool = True) -> Dict[str, Any]:
        """Process a query using RAG"""
        
        # Get relevant context
        context = self.rag_engine.get_context_for_query(query)
        search_results = self.rag_engine.search(query, top_k=5)
        
        response = {
            'query': query,
            'context': context,
            'sources': []
        }
        
        # Extract sources
        for result in search_results:
            source_info = {
                'table': result['metadata'].get('table', 'Unknown'),
                'score': result['score'],
                'data_preview': str(result['metadata'].get('data', {}))[:200]
            }
            response['sources'].append(source_info)
        
        # Generate answer using OpenAI if available
        if use_openai and self.openai_client:
            try:
                prompt = f"""Based on the following context from our database, answer the user's question.
                
Context:
{context}

User Question: {query}

Please provide a comprehensive answer based on the context. If the context doesn't contain enough information, say so.
Include specific data points and cite the source tables when relevant."""
                
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a municipal finance assistant analyzing database information."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                response['answer'] = completion.choices[0].message.content
                response['model_used'] = "gpt-4o-mini"
                
            except Exception as e:
                response['answer'] = f"Error generating AI response: {e}"
                response['fallback'] = self._generate_fallback_answer(query, context)
        else:
            # Fallback to simple response without OpenAI
            response['answer'] = self._generate_fallback_answer(query, context)
            response['model_used'] = "fallback"
        
        return response
    
    def _generate_fallback_answer(self, query: str, context: str) -> str:
        """Generate a simple answer without AI"""
        
        if not context:
            return "No relevant information found in the database for your query."
        
        # Simple template-based response
        answer = f"Based on the database search for '{query}':\n\n"
        answer += "Relevant information found:\n"
        answer += context[:1000]  # Limit context length
        
        if len(context) > 1000:
            answer += "\n\n[Additional context truncated for brevity]"
        
        return answer


# Singleton instance for global access
_rag_engine_instance = None

def get_rag_engine() -> SimpleRAGEngine:
    """Get or create the singleton RAG engine instance"""
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = SimpleRAGEngine()
    return _rag_engine_instance