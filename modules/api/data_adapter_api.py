"""
Data Adapter API Endpoints
Provides REST API access to the unified data adapter

Security: All endpoints require authentication via Bearer token
"""

import os
import logging
import re
import uuid
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends, Header
from pydantic import BaseModel

from modules.data_adapter import UnifiedDataAdapter, get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["Data Adapter"])

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {'.csv', '.pdf'}
ALLOWED_MIME_TYPES = {'text/csv', 'application/pdf', 'text/plain', 'application/octet-stream'}

async def verify_auth_token(authorization: Optional[str] = Header(None)):
    """Verify authentication token for data adapter endpoints"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    
    try:
        from jose import jwt
        from modules.api.auth_api import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    filename = filename.strip()
    if not filename:
        filename = f"upload_{uuid.uuid4().hex[:8]}"
    return filename

def validate_file_extension(filename: str) -> bool:
    """Validate file has allowed extension"""
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS

class ImportResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[int] = None
    record_count: Optional[int] = None

class HealthResponse(BaseModel):
    municipality: str
    source_type: str
    caselle_configured: bool
    file_importer_active: bool
    archive_active: bool
    pending_imports: int

@router.get("/health", response_model=HealthResponse)
async def data_adapter_health(
    municipality_id: str = "default",
    user: dict = Depends(verify_auth_token)
):
    """Get data adapter health status (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        health = adapter.health_check()
        return HealthResponse(
            municipality=health["municipality"],
            source_type=health["source_type"],
            caselle_configured=health["caselle_api"]["configured"],
            file_importer_active=health["file_importer"]["status"] == "active",
            archive_active=health["archive"]["status"] == "active",
            pending_imports=health["file_importer"]["pending_files"]
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/general-ledger")
async def get_general_ledger(
    municipality_id: str = "default",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fund: Optional[str] = None,
    department: Optional[str] = None,
    account: Optional[str] = None,
    user: dict = Depends(verify_auth_token)
):
    """Fetch general ledger data (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        data = adapter.get_general_ledger(
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            fiscal_year=fiscal_year,
            fund=fund,
            department=department,
            account=account
        )
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error fetching GL data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/budget")
async def get_budget_data(
    municipality_id: str = "default",
    fiscal_year: int = Query(..., description="Fiscal year for budget data"),
    fund: Optional[str] = None,
    department: Optional[str] = None,
    user: dict = Depends(verify_auth_token)
):
    """Fetch budget data (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        data = adapter.get_budget_data(
            fiscal_year=fiscal_year,
            fund=fund,
            department=department
        )
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error fetching budget data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payroll")
async def get_payroll_data(
    municipality_id: str = "default",
    fiscal_year: Optional[int] = None,
    department: Optional[str] = None,
    employee_id: Optional[str] = None,
    user: dict = Depends(verify_auth_token)
):
    """Fetch payroll data (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        data = adapter.get_payroll_data(
            fiscal_year=fiscal_year,
            department=department,
            employee_id=employee_id
        )
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error fetching payroll data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-years")
async def get_available_years(
    municipality_id: str = "default",
    user: dict = Depends(verify_auth_token)
):
    """Get list of years with data available (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        years = adapter.get_available_years()
        return {"success": True, "years": years}
    except Exception as e:
        logger.error(f"Error fetching available years: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending-imports")
async def get_pending_imports(
    municipality_id: str = "default",
    user: dict = Depends(verify_auth_token)
):
    """Get list of files pending import (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        pending = adapter.get_pending_imports()
        return {"success": True, "files": pending, "count": len(pending)}
    except Exception as e:
        logger.error(f"Error fetching pending imports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import-history")
async def get_import_history(
    municipality_id: str = "default",
    limit: int = 50,
    user: dict = Depends(verify_auth_token)
):
    """Get recent import history (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        history = adapter.get_import_history(limit)
        return {"success": True, "history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error fetching import history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import-template/{report_type}")
async def get_import_template(
    report_type: str,
    user: dict = Depends(verify_auth_token)
):
    """Get expected format template for a report type (requires authentication)"""
    try:
        adapter = get_adapter("default")
        template = adapter.get_import_template(report_type)
        return {"success": True, "template": template}
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import", response_model=ImportResponse)
async def import_file(
    file: UploadFile = File(...),
    municipality_id: str = Form("default"),
    report_type: Optional[str] = Form(None),
    fiscal_year: Optional[int] = Form(None),
    fiscal_period: Optional[str] = Form(None),
    user: dict = Depends(verify_auth_token)
):
    """Import a CSV or PDF file (requires authentication)
    
    Security:
    - File size limited to 50MB
    - Only .csv and .pdf extensions allowed
    - Filename sanitized to prevent path traversal
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename required")
        
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
            )
        
        safe_filename = sanitize_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        temp_path = f"/tmp/govsight_import_{unique_filename}"
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        try:
            adapter = get_adapter(municipality_id)
            result = adapter.import_file(
                file_path=temp_path,
                report_type=report_type,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
                auto_archive=True
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        if result["success"]:
            return ImportResponse(
                success=True,
                message="File imported successfully",
                session_id=result["result"].get("archive_session_id"),
                record_count=result["result"].get("record_count", 0)
            )
        else:
            return ImportResponse(
                success=False,
                message=result["result"].get("error", "Import failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-pending")
async def process_pending_imports(
    municipality_id: str = "default",
    fiscal_year: Optional[int] = None,
    user: dict = Depends(verify_auth_token)
):
    """Process all pending files in import folder (requires authentication)"""
    try:
        adapter = get_adapter(municipality_id)
        results = adapter.process_pending_imports(
            fiscal_year=fiscal_year,
            auto_archive=True
        )
        
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "processed": len(results),
            "successful": success_count,
            "failed": len(results) - success_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error processing pending imports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
