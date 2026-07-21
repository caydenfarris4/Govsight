"""
Google BigQuery Connector
Provides data warehousing and analytics capabilities using BigQuery
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Iterator
import logging

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError, NotFound
from google.api_core import retry
import pandas as pd

from modules.security.secret_manager import UnifiedSecretManager

logger = logging.getLogger(__name__)


class BigQueryConnector:
    """
    Production-ready BigQuery connector with:
    - Automatic authentication via UnifiedSecretManager
    - Dataset and table management
    - Schema design and migrations
    - Query execution with parameterization
    - Data loading from multiple sources
    - Analytics views creation
    """
    
    def __init__(self, project_id: Optional[str] = None, 
                 dataset_id: Optional[str] = "govsight_analytics"):
        """
        Initialize BigQuery connector with deferred client creation for graceful degradation.
        The client is only created on first use, allowing the application to start
        without GCP configuration.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            dataset_id: Default dataset for operations
        """
        secret_manager = UnifiedSecretManager()
        
        # Store project ID without raising error - allows graceful degradation
        self.project_id = project_id or secret_manager.get_secret("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = dataset_id
        
        # Defer client creation until first use
        self._client = None
        self._client_error = None
    
    def is_configured(self) -> bool:
        """Check if GCP is properly configured"""
        return self.project_id is not None
    
    def _get_client(self) -> Optional[bigquery.Client]:
        """
        Lazily initialize BigQuery client on first use.
        Returns None if GCP is not configured, allowing graceful degradation.
        """
        # Return cached client if available
        if self._client is not None:
            return self._client
        
        # Return None if previous initialization failed
        if self._client_error is not None:
            return None
        
        # Check if project ID is configured
        if not self.project_id:
            self._client_error = "GCP project ID not configured. Set GOOGLE_CLOUD_PROJECT environment variable."
            logger.warning(self._client_error)
            return None
        
        # Initialize BigQuery client with Application Default Credentials
        try:
            self._client = bigquery.Client(project=self.project_id)
            logger.info(f"BigQuery connector initialized for project: {self.project_id}")
            return self._client
        except Exception as e:
            self._client_error = f"Failed to initialize BigQuery client: {e}"
            logger.error(self._client_error)
            return None
    
    def get_config_error(self) -> Optional[str]:
        """Get configuration error message if GCP is not properly configured"""
        if not self.project_id:
            return "GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable."
        return self._client_error
    
    def create_dataset(self, dataset_id: Optional[str] = None,
                      location: str = "US",
                      description: Optional[str] = None) -> Optional[bigquery.Dataset]:
        """
        Create a BigQuery dataset
        
        Args:
            dataset_id: Dataset ID (defaults to self.dataset_id)
            location: Dataset location
            description: Optional description
            
        Returns:
            Created dataset object, or None if GCP not configured
        """
        client = self._get_client()
        if not client:
            logger.warning(f"Cannot create dataset: {self.get_config_error()}")
            return None
        
        try:
            dataset_id = dataset_id or self.dataset_id
            dataset_ref = f"{self.project_id}.{dataset_id}"
            
            # Check if dataset exists
            try:
                dataset = client.get_dataset(dataset_ref)
                logger.info(f"Dataset {dataset_id} already exists")
                return dataset
            except NotFound:
                pass
            
            # Create dataset
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location
            
            if description:
                dataset.description = description
            
            dataset = client.create_dataset(dataset, timeout=30)
            logger.info(f"Created dataset: {dataset_id} in {location}")
            
            return dataset
            
        except GoogleCloudError as e:
            logger.error(f"Failed to create dataset {dataset_id}: {e}")
            raise
    
    def create_table(self, table_id: str, schema: List[bigquery.SchemaField],
                    dataset_id: Optional[str] = None,
                    partitioning_field: Optional[str] = None,
                    clustering_fields: Optional[List[str]] = None) -> bigquery.Table:
        """
        Create a BigQuery table with schema
        
        Args:
            table_id: Table ID
            schema: List of SchemaField objects
            dataset_id: Dataset ID (defaults to self.dataset_id)
            partitioning_field: Optional field for time partitioning
            clustering_fields: Optional fields for clustering
            
        Returns:
            Created table object
        """
        client = self._get_client()
        if not client:
            logger.warning(f"Cannot create table: {{self.get_config_error()}}")
            return None
        
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            # Check if table exists
            try:
                table = client.get_table(table_ref)
                logger.info(f"Table {table_id} already exists")
                return table
            except NotFound:
                pass
            
            # Create table
            table = bigquery.Table(table_ref, schema=schema)
            
            # Add partitioning if specified
            if partitioning_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=partitioning_field
                )
            
            # Add clustering if specified
            if clustering_fields:
                table.clustering_fields = clustering_fields
            
            table = client.create_table(table, timeout=30)
            logger.info(f"Created table: {table_id}")
            
            return table
            
        except GoogleCloudError as e:
            logger.error(f"Failed to create table {table_id}: {e}")
            raise
    
    def create_view(self, view_id: str, query: str,
                   dataset_id: Optional[str] = None) -> bigquery.Table:
        """
        Create a BigQuery view
        
        Args:
            view_id: View ID
            query: SQL query defining the view
            dataset_id: Dataset ID (defaults to self.dataset_id)
            
        Returns:
            Created view object
        """
        client = self._get_client()
        if not client:
            logger.warning(f"Cannot create view: {{self.get_config_error()}}")
            return None
        
        try:
            dataset_id = dataset_id or self.dataset_id
            view_ref = f"{self.project_id}.{dataset_id}.{view_id}"
            
            # Check if view exists
            try:
                view = client.get_table(view_ref)
                logger.info(f"View {view_id} already exists, updating")
                view.view_query = query
                view = client.update_table(view, ["view_query"])
                return view
            except NotFound:
                pass
            
            # Create view
            view = bigquery.Table(view_ref)
            view.view_query = query
            
            view = client.create_table(view, timeout=30)
            logger.info(f"Created view: {view_id}")
            
            return view
            
        except GoogleCloudError as e:
            logger.error(f"Failed to create view {view_id}: {e}")
            raise
    
    def execute_query(self, query: str, 
                     parameters: Optional[List] = None,
                     as_dataframe: bool = True) -> Any:
        """
        Execute a BigQuery SQL query
        
        Args:
            query: SQL query string
            parameters: Optional query parameters
            as_dataframe: Return results as pandas DataFrame
            
        Returns:
            Query results as DataFrame or QueryJob
        """
        client = self._get_client()
        if not client:
            logger.warning(f"Cannot execute query: {{self.get_config_error()}}")
            return None
        
        try:
            # Configure query job
            job_config = bigquery.QueryJobConfig()
            
            if parameters:
                job_config.query_parameters = parameters
            
            # Execute query
            query_job = client.query(query, job_config=job_config)
            
            # Wait for completion
            query_job.result()
            
            logger.info(f"Query executed successfully")
            
            if as_dataframe:
                return query_job.to_dataframe()
            else:
                return query_job
            
        except GoogleCloudError as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def load_dataframe(self, df: pd.DataFrame, table_id: str,
                      dataset_id: Optional[str] = None,
                      write_disposition: str = "WRITE_APPEND") -> bigquery.LoadJob:
        """
        Load pandas DataFrame into BigQuery table
        
        Args:
            df: pandas DataFrame
            table_id: Target table ID
            dataset_id: Dataset ID (defaults to self.dataset_id)
            write_disposition: WRITE_APPEND, WRITE_TRUNCATE, or WRITE_EMPTY
            
        Returns:
            LoadJob object
        """
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            # Configure load job
            job_config = bigquery.LoadJobConfig()
            job_config.write_disposition = write_disposition
            job_config.autodetect = True
            
            # Load DataFrame
            job = client.load_table_from_dataframe(
                df,
                table_ref,
                job_config=job_config
            )
            
            # Wait for completion
            job.result()
            
            logger.info(f"Loaded {len(df)} rows into {table_id}")
            return job
            
        except GoogleCloudError as e:
            logger.error(f"Failed to load data into {table_id}: {e}")
            raise
    
    def load_from_csv(self, csv_path: str, table_id: str,
                     dataset_id: Optional[str] = None,
                     skip_leading_rows: int = 1,
                     write_disposition: str = "WRITE_APPEND") -> bigquery.LoadJob:
        """
        Load CSV file into BigQuery table
        
        Args:
            csv_path: Path to CSV file
            table_id: Target table ID
            dataset_id: Dataset ID (defaults to self.dataset_id)
            skip_leading_rows: Number of header rows to skip
            write_disposition: WRITE_APPEND, WRITE_TRUNCATE, or WRITE_EMPTY
            
        Returns:
            LoadJob object
        """
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            # Configure load job
            job_config = bigquery.LoadJobConfig()
            job_config.source_format = bigquery.SourceFormat.CSV
            job_config.skip_leading_rows = skip_leading_rows
            job_config.autodetect = True
            job_config.write_disposition = write_disposition
            
            # Load from file
            with open(csv_path, "rb") as source_file:
                job = client.load_table_from_file(
                    source_file,
                    table_ref,
                    job_config=job_config
                )
            
            # Wait for completion
            job.result()
            
            logger.info(f"Loaded CSV {csv_path} into {table_id}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to load CSV into {table_id}: {e}")
            raise
    
    def get_table_info(self, table_id: str,
                      dataset_id: Optional[str] = None) -> Dict[str, Any]:
        """Get table metadata and statistics"""
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            table = client.get_table(table_ref)
            
            info = {
                "table_id": table.table_id,
                "dataset_id": table.dataset_id,
                "project": table.project,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "num_bytes_mb": table.num_bytes / (1024 * 1024) if table.num_bytes else 0,
                "schema": [{"name": field.name, "type": field.field_type, "mode": field.mode} 
                          for field in table.schema],
                "partitioning": str(table.time_partitioning) if table.time_partitioning else None,
                "clustering": table.clustering_fields if table.clustering_fields else None
            }
            
            return info
            
        except NotFound:
            logger.error(f"Table {table_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return None
    
    def list_tables(self, dataset_id: Optional[str] = None) -> List[str]:
        """List all tables in dataset"""
        try:
            dataset_id = dataset_id or self.dataset_id
            dataset_ref = f"{self.project_id}.{dataset_id}"
            
            tables = list(client.list_tables(dataset_ref))
            table_ids = [table.table_id for table in tables]
            
            logger.info(f"Found {len(table_ids)} tables in {dataset_id}")
            return table_ids
            
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    def delete_table(self, table_id: str,
                    dataset_id: Optional[str] = None,
                    not_found_ok: bool = True) -> bool:
        """Delete a table"""
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            client.delete_table(table_ref, not_found_ok=not_found_ok)
            logger.info(f"Deleted table: {table_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete table {table_id}: {e}")
            return False
    
    def export_to_gcs(self, table_id: str, gcs_uri: str,
                     dataset_id: Optional[str] = None,
                     format: str = "CSV") -> bigquery.ExtractJob:
        """
        Export table to Google Cloud Storage
        
        Args:
            table_id: Source table ID
            gcs_uri: GCS destination URI (gs://bucket/path/*)
            dataset_id: Dataset ID (defaults to self.dataset_id)
            format: Export format (CSV, JSON, AVRO, PARQUET)
            
        Returns:
            ExtractJob object
        """
        try:
            dataset_id = dataset_id or self.dataset_id
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            
            # Configure extract job
            job_config = bigquery.ExtractJobConfig()
            job_config.destination_format = getattr(bigquery.DestinationFormat, format)
            
            # Start extract job
            extract_job = client.extract_table(
                table_ref,
                gcs_uri,
                job_config=job_config
            )
            
            # Wait for completion
            extract_job.result()
            
            logger.info(f"Exported {table_id} to {gcs_uri}")
            return extract_job
            
        except Exception as e:
            logger.error(f"Failed to export table: {e}")
            raise
    
    def get_query_cost_estimate(self, query: str) -> Dict[str, Any]:
        """
        Estimate query cost before execution
        
        Returns:
            Dictionary with estimated bytes processed and cost
        """
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            
            query_job = client.query(query, job_config=job_config)
            
            bytes_processed = query_job.total_bytes_processed
            gb_processed = bytes_processed / (1024 ** 3)
            
            # BigQuery pricing: $5 per TB processed
            estimated_cost = (gb_processed / 1024) * 5.0
            
            return {
                "bytes_processed": bytes_processed,
                "gb_processed": gb_processed,
                "estimated_cost_usd": estimated_cost,
                "query": query[:100] + "..." if len(query) > 100 else query
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate query cost: {e}")
            return {"error": str(e)}


# Schema definitions for common GovSight tables
def get_gl_transactions_schema() -> List[bigquery.SchemaField]:
    """Schema for GL transactions table"""
    return [
        bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("transaction_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("account_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("account_name", "STRING"),
        bigquery.SchemaField("department", "STRING"),
        bigquery.SchemaField("amount", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("debit_credit", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("fiscal_year", "INTEGER"),
        bigquery.SchemaField("fiscal_period", "INTEGER"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
    ]


def get_audit_log_schema() -> List[bigquery.SchemaField]:
    """Schema for audit logs table"""
    return [
        bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("severity", "STRING"),
        bigquery.SchemaField("user_id", "STRING"),
        bigquery.SchemaField("session_id", "STRING"),
        bigquery.SchemaField("action", "STRING"),
        bigquery.SchemaField("resource", "STRING"),
        bigquery.SchemaField("outcome", "STRING"),
        bigquery.SchemaField("message", "STRING"),
        bigquery.SchemaField("correlation_id", "STRING"),
        bigquery.SchemaField("metadata", "JSON"),
    ]


def get_budget_data_schema() -> List[bigquery.SchemaField]:
    """Schema for budget data table"""
    return [
        bigquery.SchemaField("budget_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("fiscal_year", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("department", "STRING"),
        bigquery.SchemaField("account_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("account_name", "STRING"),
        bigquery.SchemaField("budgeted_amount", "FLOAT64"),
        bigquery.SchemaField("actual_amount", "FLOAT64"),
        bigquery.SchemaField("variance", "FLOAT64"),
        bigquery.SchemaField("variance_percent", "FLOAT64"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("updated_at", "TIMESTAMP"),
    ]


if __name__ == "__main__":
    # Example usage
    connector = BigQueryConnector()
    print(f"BigQuery Connector initialized for project: {connector.project_id}")
    
    # List tables
    tables = connector.list_tables()
    print(f"Found {len(tables)} tables")
