"""
RAG Indexing Service for GovSight
Manages the indexing and updating of database content for RAG retrieval
"""

import os
import sqlite3
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.ai_engine.simple_rag_engine import SimpleRAGEngine, get_rag_engine

class RAGIndexingService:
    """Service for managing RAG indexing of GovSight databases"""
    
    def __init__(self):
        self.rag_engine = get_rag_engine()
        self.indexed_databases = {}
        self.indexing_stats = {
            'total_documents': 0,
            'databases_indexed': [],
            'last_update': None,
            'errors': []
        }
    
    def index_gl_database(self, db_path: str = "databases/core/caselle_gl0_mock.db") -> bool:
        """Index the General Ledger database"""
        print("Indexing General Ledger database...")
        
        if not os.path.exists(db_path):
            print(f"GL database not found at {db_path}")
            self.indexing_stats['errors'].append(f"GL database not found: {db_path}")
            return False
        
        try:
            # Define GL tables and their schemas for better context
            gl_tables_schema = {
                'tblGLAccount': {
                    'description': 'General Ledger Accounts',
                    'key_fields': ['AccountNumber', 'AccountName', 'AccountType', 'Fund', 'Department'],
                    'importance': 'high'
                },
                'tblTransaction': {
                    'description': 'Financial Transactions',
                    'key_fields': ['TransactionID', 'AccountNumber', 'Amount', 'Date', 'Description', 'Vendor'],
                    'importance': 'high'
                },
                'departments': {
                    'description': 'Department Information',
                    'key_fields': ['department_id', 'department_name', 'manager', 'budget'],
                    'importance': 'high'
                },
                'DepartmentPerformance': {
                    'description': 'Department Performance Metrics',
                    'key_fields': ['Department', 'Fund', 'Budget', 'Actual', 'Variance'],
                    'importance': 'high'
                },
                'scenarios': {
                    'description': 'Budget Scenarios',
                    'key_fields': ['id', 'name', 'total_funding', 'created_at'],
                    'importance': 'medium'
                },
                'scenario_department_allocations': {
                    'description': 'Scenario Department Allocations',
                    'key_fields': ['scenario_id', 'department_name', 'funding_amount'],
                    'importance': 'medium'
                }
            }
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get actual tables in database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            available_tables = [row[0] for row in cursor.fetchall()]
            
            documents_added = 0
            
            for table_name, schema_info in gl_tables_schema.items():
                if table_name not in available_tables:
                    print(f"  Table {table_name} not found, skipping...")
                    continue
                
                print(f"  Indexing table: {table_name}")
                
                try:
                    # Get table columns
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Build query with only existing columns
                    select_columns = []
                    for col in schema_info.get('key_fields', []):
                        if col in columns:
                            select_columns.append(col)
                    
                    if not select_columns:
                        select_columns = columns[:10]  # Use first 10 columns if no key fields match
                    
                    query = f"SELECT {', '.join(select_columns)} FROM {table_name} LIMIT 500"
                    
                    df = pd.read_sql_query(query, conn)
                    
                    # Convert rows to documents
                    documents = []
                    for _, row in df.iterrows():
                        doc_text = f"Table: {table_name} ({schema_info['description']})"
                        
                        for col in select_columns:
                            if pd.notna(row[col]):
                                doc_text += f" | {col}: {row[col]}"
                        
                        documents.append({
                            'id': f"gl_{table_name}_{_}",
                            'text': doc_text,
                            'metadata': {
                                'database': 'general_ledger',
                                'table': table_name,
                                'importance': schema_info['importance'],
                                'indexed_at': datetime.now().isoformat()
                            }
                        })
                    
                    if documents:
                        self.rag_engine.add_documents(documents)
                        documents_added += len(documents)
                        print(f"    Added {len(documents)} documents from {table_name}")
                    
                except Exception as e:
                    print(f"    Error indexing {table_name}: {e}")
                    self.indexing_stats['errors'].append(f"Error indexing {table_name}: {e}")
            
            conn.close()
            
            self.indexing_stats['databases_indexed'].append('general_ledger')
            self.indexing_stats['total_documents'] += documents_added
            
            print(f"GL database indexed successfully: {documents_added} documents")
            return True
            
        except Exception as e:
            print(f"Error indexing GL database: {e}")
            self.indexing_stats['errors'].append(f"GL indexing error: {e}")
            return False
    
    def index_payroll_database(self, db_path: str = "databases/payroll_city_payroll_demo.db") -> bool:
        """Index the Payroll database"""
        print("Indexing Payroll database...")
        
        if not os.path.exists(db_path):
            # Try alternative path
            alt_path = "databases/core/payroll_city_payroll_demo.db"
            if os.path.exists(alt_path):
                db_path = alt_path
            else:
                print(f"Payroll database not found at {db_path}")
                self.indexing_stats['errors'].append(f"Payroll database not found: {db_path}")
                return False
        
        try:
            # Define Payroll tables schema
            payroll_tables_schema = {
                'Employees': {
                    'description': 'Employee Records',
                    'key_fields': ['EmployeeID', 'FirstName', 'LastName', 'Department', 'Position', 'HourlyRate'],
                    'importance': 'high'
                },
                'PaycheckLines': {
                    'description': 'Paycheck Line Items',
                    'key_fields': ['PaycheckLineID', 'EmployeeID', 'PayPeriodID', 'PayCodeID', 'Hours', 'Amount'],
                    'importance': 'high'
                },
                'PaycheckBenefits': {
                    'description': 'Paycheck Benefits',
                    'key_fields': ['PaycheckBenefitID', 'EmployeeID', 'PayPeriodID', 'BenefitPlanID', 'EmployeeAmount', 'EmployerAmount'],
                    'importance': 'high'
                },
                'EmployeeBenefitElections': {
                    'description': 'Employee Benefit Elections',
                    'key_fields': ['ElectionID', 'EmployeeID', 'BenefitPlanID', 'CoverageLevel', 'EffectiveDate'],
                    'importance': 'medium'
                },
                'PayPeriods': {
                    'description': 'Pay Period Information',
                    'key_fields': ['PayPeriodID', 'StartDate', 'EndDate', 'PayDate', 'PeriodType'],
                    'importance': 'high'
                },
                'BenefitPlans': {
                    'description': 'Benefit Plan Information',
                    'key_fields': ['BenefitPlanID', 'PlanName', 'PlanType', 'Provider', 'EmployeeCost', 'EmployerCost'],
                    'importance': 'medium'
                },
                'Positions': {
                    'description': 'Position Information',
                    'key_fields': ['PositionID', 'PositionTitle', 'Department', 'PayGrade', 'MinSalary', 'MaxSalary'],
                    'importance': 'medium'
                }
            }
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get actual tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            available_tables = [row[0] for row in cursor.fetchall()]
            
            documents_added = 0
            
            for table_name, schema_info in payroll_tables_schema.items():
                if table_name not in available_tables:
                    # Try without 's' suffix (singular form)
                    singular_name = table_name.rstrip('s')
                    if singular_name in available_tables:
                        table_name = singular_name
                    else:
                        print(f"  Table {table_name} not found, skipping...")
                        continue
                
                print(f"  Indexing table: {table_name}")
                
                try:
                    # Get first 200 rows for indexing
                    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 200", conn)
                    
                    # Convert rows to documents
                    documents = []
                    for idx, row in df.iterrows():
                        doc_text = f"Table: {table_name} ({schema_info['description']})"
                        
                        for col in df.columns:
                            if pd.notna(row[col]):
                                doc_text += f" | {col}: {row[col]}"
                        
                        documents.append({
                            'id': f"payroll_{table_name}_{idx}",
                            'text': doc_text,
                            'metadata': {
                                'database': 'payroll',
                                'table': table_name,
                                'importance': schema_info['importance'],
                                'indexed_at': datetime.now().isoformat()
                            }
                        })
                    
                    if documents:
                        self.rag_engine.add_documents(documents)
                        documents_added += len(documents)
                        print(f"    Added {len(documents)} documents from {table_name}")
                    
                except Exception as e:
                    print(f"    Error indexing {table_name}: {e}")
                    self.indexing_stats['errors'].append(f"Error indexing {table_name}: {e}")
            
            conn.close()
            
            self.indexing_stats['databases_indexed'].append('payroll')
            self.indexing_stats['total_documents'] += documents_added
            
            print(f"Payroll database indexed successfully: {documents_added} documents")
            return True
            
        except Exception as e:
            print(f"Error indexing Payroll database: {e}")
            self.indexing_stats['errors'].append(f"Payroll indexing error: {e}")
            return False
    
    def index_all_databases(self) -> Dict[str, Any]:
        """Index all configured databases"""
        print("Starting comprehensive database indexing...")
        
        self.indexing_stats['last_update'] = datetime.now().isoformat()
        
        # Index GL database
        gl_success = self.index_gl_database()
        
        # Index Payroll database
        payroll_success = self.index_payroll_database()
        
        # Save indexing stats
        self.save_indexing_stats()
        
        print("\n=== Indexing Complete ===")
        print(f"Total documents indexed: {self.indexing_stats['total_documents']}")
        print(f"Databases indexed: {', '.join(self.indexing_stats['databases_indexed'])}")
        
        if self.indexing_stats['errors']:
            print(f"Errors encountered: {len(self.indexing_stats['errors'])}")
            for error in self.indexing_stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        return self.indexing_stats
    
    def save_indexing_stats(self):
        """Save indexing statistics to file"""
        stats_file = "rag_indices/indexing_stats.json"
        
        try:
            os.makedirs("rag_indices", exist_ok=True)
            with open(stats_file, 'w') as f:
                json.dump(self.indexing_stats, f, indent=2)
            print(f"Indexing stats saved to {stats_file}")
        except Exception as e:
            print(f"Error saving indexing stats: {e}")
    
    def clear_index(self):
        """Clear all indexed documents"""
        self.rag_engine.clear_index()
        self.indexing_stats = {
            'total_documents': 0,
            'databases_indexed': [],
            'last_update': None,
            'errors': []
        }
        print("Index cleared successfully")
    
    def get_index_status(self) -> Dict[str, Any]:
        """Get current index status"""
        return {
            'total_documents': len(self.rag_engine.documents),
            'databases_indexed': self.indexing_stats['databases_indexed'],
            'last_update': self.indexing_stats['last_update'],
            'index_size': len(self.rag_engine.documents) if self.rag_engine else 0
        }


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='RAG Indexing Service for GovSight')
    parser.add_argument('--index-all', action='store_true', help='Index all databases')
    parser.add_argument('--index-gl', action='store_true', help='Index GL database only')
    parser.add_argument('--index-payroll', action='store_true', help='Index Payroll database only')
    parser.add_argument('--clear', action='store_true', help='Clear existing index')
    parser.add_argument('--status', action='store_true', help='Show index status')
    
    args = parser.parse_args()
    
    service = RAGIndexingService()
    
    if args.clear:
        service.clear_index()
    elif args.index_all:
        service.index_all_databases()
    elif args.index_gl:
        service.index_gl_database()
    elif args.index_payroll:
        service.index_payroll_database()
    elif args.status:
        status = service.get_index_status()
        print("=== Index Status ===")
        print(json.dumps(status, indent=2))
    else:
        print("No action specified. Use --help for options.")


if __name__ == "__main__":
    main()