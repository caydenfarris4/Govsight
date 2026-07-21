"""
Archive API Router for FastAPI
Provides REST endpoints for document archiving and retrieval
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import logging
import tempfile

from modules.cloud_services.document_archive import DocumentArchive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/archive", tags=["archive"])


class ArchiveResponse(BaseModel):
    success: bool
    message: str
    uri: Optional[str] = None
    blob_name: Optional[str] = None


class DocumentMetadata(BaseModel):
    name: str
    size: int
    content_type: str
    created: str
    uri: str
    custom_metadata: Dict[str, str]


class ArchiveStats(BaseModel):
    bucket: str
    document_count: int
    total_size_mb: float
    retention_days: int
    archive_days: int


_archive_instance = None


def get_archive() -> DocumentArchive:
    """Lazy initialization of DocumentArchive"""
    global _archive_instance
    if _archive_instance is None:
        _archive_instance = DocumentArchive()
    return _archive_instance


@router.post("/report", response_model=ArchiveResponse)
async def archive_report_endpoint(
    file: UploadFile = File(...),
    report_type: str = Query(..., description="Type of report (budget, balance_sheet, etc.)"),
    metadata: Optional[str] = Query(None, description="JSON string of custom metadata")
):
    """Archive a financial report to Google Cloud Storage"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Parse metadata if provided
        custom_metadata = None
        if metadata:
            import json
            custom_metadata = json.loads(metadata)
        
        # Archive the report
        uri = archive.archive_report(temp_path, report_type, metadata=custom_metadata)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if uri:
            return ArchiveResponse(
                success=True,
                message=f"Report archived successfully",
                uri=uri,
                blob_name=uri.split('/')[-1]
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to archive report: {archive.connector.get_config_error()}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive report: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/export", response_model=ArchiveResponse)
async def archive_export_endpoint(
    file: UploadFile = File(...),
    export_type: str = Query(..., description="Type of export (gl_accounts, transactions, etc.)"),
    metadata: Optional[str] = Query(None, description="JSON string of custom metadata")
):
    """Archive a CSV export to Google Cloud Storage"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Validate CSV file
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Parse metadata if provided
        custom_metadata = None
        if metadata:
            import json
            custom_metadata = json.loads(metadata)
        
        # Archive the export
        uri = archive.archive_csv_export(temp_path, export_type, metadata=custom_metadata)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if uri:
            return ArchiveResponse(
                success=True,
                message=f"CSV export archived successfully",
                uri=uri,
                blob_name=uri.split('/')[-1]
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to archive export: {archive.connector.get_config_error()}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive export: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/backup", response_model=ArchiveResponse)
async def archive_backup_endpoint(
    file: UploadFile = File(...),
    database_name: str = Query(..., description="Database name (caselle_gl0, payroll, etc.)"),
    metadata: Optional[str] = Query(None, description="JSON string of custom metadata")
):
    """Archive a database backup to Google Cloud Storage"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Parse metadata if provided
        custom_metadata = None
        if metadata:
            import json
            custom_metadata = json.loads(metadata)
        
        # Archive the backup
        uri = archive.archive_database_backup(temp_path, database_name, metadata=custom_metadata)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if uri:
            return ArchiveResponse(
                success=True,
                message=f"Database backup archived successfully",
                uri=uri,
                blob_name=uri.split('/')[-1]
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to archive backup: {archive.connector.get_config_error()}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive backup: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/search/{archive_type}", response_model=List[DocumentMetadata])
async def search_archives_endpoint(
    archive_type: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    prefix: Optional[str] = Query(None, description="Path prefix filter")
):
    """Search for archived documents"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Validate archive type
        valid_types = ["reports", "exports", "backups", "documents"]
        if archive_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid archive type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        
        # Search archives
        results = archive.search_archives(
            archive_type,
            start_date=start_dt,
            end_date=end_dt,
            filter_prefix=prefix
        )
        
        # Convert to response model
        documents = []
        for result in results:
            documents.append(DocumentMetadata(
                name=result["name"],
                size=result["size"],
                content_type=result["content_type"],
                created=result["created"],
                uri=f"gs://{result['bucket']}/{result['name']}",
                custom_metadata=result.get("custom_metadata", {})
            ))
        
        return documents
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search archives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve/{archive_type}")
async def retrieve_document_endpoint(
    archive_type: str,
    blob_name: str = Query(..., description="Full blob path in bucket")
):
    """Retrieve an archived document"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Validate archive type
        valid_types = ["reports", "exports", "backups", "documents"]
        if archive_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid archive type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Retrieve document
        local_path = archive.retrieve_document(archive_type, blob_name)
        
        if not local_path or not os.path.exists(local_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Return file
        return FileResponse(
            path=local_path,
            filename=os.path.basename(blob_name),
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-url/{archive_type}")
async def generate_download_url_endpoint(
    archive_type: str,
    blob_name: str = Query(..., description="Full blob path in bucket"),
    expiration_minutes: int = Query(60, description="URL expiration time in minutes")
):
    """Generate a temporary signed URL for direct download"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        # Validate archive type
        valid_types = ["reports", "exports", "backups", "documents"]
        if archive_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid archive type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Generate signed URL
        url = archive.generate_access_url(archive_type, blob_name, expiration_minutes)
        
        if not url:
            raise HTTPException(status_code=404, detail="Failed to generate download URL")
        
        return {
            "success": True,
            "url": url,
            "expires_in_minutes": expiration_minutes
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, ArchiveStats])
async def get_archive_statistics_endpoint():
    """Get statistics for all archive buckets"""
    try:
        # Check if GCP is configured
        archive = get_archive()
        if not archive.connector.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving."
            )
        
        stats = archive.get_archive_statistics()
        
        # Convert to response model
        response = {}
        for archive_type, stat in stats.items():
            if "error" not in stat:
                response[archive_type] = ArchiveStats(**stat)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get archive statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def archive_health_check():
    """Health check for archive service"""
    try:
        # Try to list buckets to verify connectivity
        stats = get_archive().get_archive_statistics()
        
        return {
            "status": "healthy",
            "service": "document-archive",
            "buckets_configured": len(stats),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "document-archive",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
