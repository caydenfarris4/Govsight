"""
Google Vertex AI Connector
Provides AI/ML model deployment, training, and prediction capabilities using Vertex AI
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from google.cloud import aiplatform
from google.cloud.aiplatform import gapic
from google.api_core import retry
import pandas as pd

from modules.security.secret_manager import UnifiedSecretManager

logger = logging.getLogger(__name__)


class VertexAIConnector:
    """
    Production-ready Vertex AI connector with:
    - Automatic authentication via UnifiedSecretManager
    - Model deployment and management
    - Training job orchestration
    - Online and batch prediction
    - AutoML integration
    - Graceful degradation when GCP not configured
    """
    
    def __init__(self, project_id: Optional[str] = None,
                 location: str = "us-central1"):
        """
        Initialize Vertex AI connector with deferred client creation.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: GCP region for Vertex AI resources
        """
        secret_manager = UnifiedSecretManager()
        
        # Store configuration without raising error - allows graceful degradation
        self.project_id = project_id or secret_manager.get_secret("GOOGLE_CLOUD_PROJECT")
        self.location = location
        
        # Defer initialization until first use
        self._initialized = False
        self._init_error = None
    
    def is_configured(self) -> bool:
        """Check if GCP and Vertex AI are properly configured"""
        return self.project_id is not None
    
    def _initialize(self) -> bool:
        """
        Lazily initialize Vertex AI on first use.
        Returns False if GCP is not configured, allowing graceful degradation.
        """
        # Return cached result if already attempted
        if self._initialized:
            return True
        
        # Return False if previous initialization failed
        if self._init_error is not None:
            return False
        
        # Check if project ID is configured
        if not self.project_id:
            self._init_error = "GCP project ID not configured. Set GOOGLE_CLOUD_PROJECT environment variable."
            logger.warning(self._init_error)
            return False
        
        # Initialize Vertex AI with Application Default Credentials
        try:
            aiplatform.init(
                project=self.project_id,
                location=self.location
            )
            self._initialized = True
            logger.info(f"Vertex AI initialized for project: {self.project_id}, location: {self.location}")
            return True
        except Exception as e:
            self._init_error = f"Failed to initialize Vertex AI: {e}"
            logger.error(self._init_error)
            return False
    
    def get_config_error(self) -> Optional[str]:
        """Get configuration error message if GCP is not properly configured"""
        if not self.project_id:
            return "GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable Vertex AI."
        return self._init_error
    
    def deploy_model(self, 
                     model_display_name: str,
                     model_artifact_uri: str,
                     serving_container_image_uri: str,
                     machine_type: str = "n1-standard-4",
                     min_replica_count: int = 1,
                     max_replica_count: int = 1) -> Optional[Dict[str, Any]]:
        """
        Deploy a model to Vertex AI endpoint
        
        Args:
            model_display_name: Display name for the model
            model_artifact_uri: GCS URI containing model artifacts
            serving_container_image_uri: Docker image for serving
            machine_type: Machine type for deployment
            min_replica_count: Minimum number of replicas
            max_replica_count: Maximum number of replicas
            
        Returns:
            Deployment info dict, or None if GCP not configured
        """
        if not self._initialize():
            logger.warning(f"Cannot deploy model: {self.get_config_error()}")
            return None
        
        try:
            # Upload model
            model = aiplatform.Model.upload(
                display_name=model_display_name,
                artifact_uri=model_artifact_uri,
                serving_container_image_uri=serving_container_image_uri
            )
            
            # Create endpoint
            endpoint = aiplatform.Endpoint.create(
                display_name=f"{model_display_name}_endpoint"
            )
            
            # Deploy model to endpoint
            model.deploy(
                endpoint=endpoint,
                machine_type=machine_type,
                min_replica_count=min_replica_count,
                max_replica_count=max_replica_count
            )
            
            logger.info(f"Model {model_display_name} deployed to endpoint {endpoint.resource_name}")
            
            return {
                "model_name": model.resource_name,
                "model_display_name": model.display_name,
                "endpoint_name": endpoint.resource_name,
                "endpoint_display_name": endpoint.display_name,
                "deployment_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            return None
    
    def list_models(self, filter_str: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        List all models in the project
        
        Args:
            filter_str: Optional filter string (e.g., 'display_name="my_model"')
            
        Returns:
            List of model info dicts, or None if GCP not configured
        """
        if not self._initialize():
            logger.warning(f"Cannot list models: {self.get_config_error()}")
            return None
        
        try:
            models = aiplatform.Model.list(filter=filter_str)
            
            model_list = []
            for model in models:
                model_list.append({
                    "name": model.resource_name,
                    "display_name": model.display_name,
                    "create_time": model.create_time.isoformat() if model.create_time else None,
                    "update_time": model.update_time.isoformat() if model.update_time else None,
                    "deployed": len(model.gca_resource.deployed_models) > 0
                })
            
            logger.info(f"Retrieved {len(model_list)} models from Vertex AI")
            return model_list
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return None
    
    def get_predictions(self,
                       endpoint_id: str,
                       instances: List[Dict[str, Any]]) -> Optional[List[Any]]:
        """
        Get predictions from a deployed model
        
        Args:
            endpoint_id: Vertex AI endpoint ID or resource name
            instances: List of prediction instances
            
        Returns:
            List of predictions, or None if GCP not configured
        """
        if not self._initialize():
            logger.warning(f"Cannot get predictions: {self.get_config_error()}")
            return None
        
        try:
            # Get endpoint
            if "/" in endpoint_id:
                endpoint = aiplatform.Endpoint(endpoint_id)
            else:
                endpoint = aiplatform.Endpoint(
                    endpoint_name=f"projects/{self.project_id}/locations/{self.location}/endpoints/{endpoint_id}"
                )
            
            # Get predictions
            predictions = endpoint.predict(instances=instances)
            
            logger.info(f"Retrieved {len(predictions.predictions)} predictions from endpoint {endpoint_id}")
            return predictions.predictions
            
        except Exception as e:
            logger.error(f"Failed to get predictions: {e}")
            return None
    
    def create_automl_tabular_training(self,
                                      display_name: str,
                                      dataset_id: str,
                                      target_column: str,
                                      optimization_objective: str = "minimize-rmse",
                                      budget_milli_node_hours: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Create AutoML tabular training job
        
        Args:
            display_name: Display name for the training job
            dataset_id: Vertex AI dataset ID
            target_column: Name of the target column to predict
            optimization_objective: Optimization objective (minimize-rmse, maximize-au-prc, etc.)
            budget_milli_node_hours: Training budget in milli node hours
            
        Returns:
            Training job info dict, or None if GCP not configured
        """
        if not self._initialize():
            logger.warning(f"Cannot create training job: {self.get_config_error()}")
            return None
        
        try:
            # Create AutoML tabular training job
            job = aiplatform.AutoMLTabularTrainingJob(
                display_name=display_name,
                optimization_prediction_type="regression",
                optimization_objective=optimization_objective
            )
            
            # Get dataset
            dataset = aiplatform.TabularDataset(dataset_id)
            
            # Run training
            model = job.run(
                dataset=dataset,
                target_column=target_column,
                budget_milli_node_hours=budget_milli_node_hours,
                model_display_name=f"{display_name}_model"
            )
            
            logger.info(f"AutoML training job created: {job.resource_name}")
            
            return {
                "job_name": job.resource_name,
                "job_display_name": job.display_name,
                "model_name": model.resource_name if model else None,
                "create_time": datetime.now().isoformat(),
                "state": job.state.name if hasattr(job, 'state') else "RUNNING"
            }
            
        except Exception as e:
            logger.error(f"Failed to create AutoML training job: {e}")
            return None
    
    def delete_model(self, model_id: str) -> bool:
        """
        Delete a model from Vertex AI
        
        Args:
            model_id: Model ID or resource name
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialize():
            logger.warning(f"Cannot delete model: {self.get_config_error()}")
            return False
        
        try:
            # Get model
            if "/" in model_id:
                model = aiplatform.Model(model_id)
            else:
                model = aiplatform.Model(
                    model_name=f"projects/{self.project_id}/locations/{self.location}/models/{model_id}"
                )
            
            # Delete model
            model.delete()
            
            logger.info(f"Model {model_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a model
        
        Args:
            model_id: Model ID or resource name
            
        Returns:
            Model info dict, or None if not found
        """
        if not self._initialize():
            logger.warning(f"Cannot get model info: {self.get_config_error()}")
            return None
        
        try:
            # Get model
            if "/" in model_id:
                model = aiplatform.Model(model_id)
            else:
                model = aiplatform.Model(
                    model_name=f"projects/{self.project_id}/locations/{self.location}/models/{model_id}"
                )
            
            return {
                "name": model.resource_name,
                "display_name": model.display_name,
                "description": model.description,
                "create_time": model.create_time.isoformat() if model.create_time else None,
                "update_time": model.update_time.isoformat() if model.update_time else None,
                "deployed_models": [dm.endpoint for dm in model.gca_resource.deployed_models],
                "labels": dict(model.labels) if model.labels else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
