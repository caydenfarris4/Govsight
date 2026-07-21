"""
Enterprise Logging System
Provides structured logging with audit trails, performance monitoring, and compliance features
"""

import logging
import logging.handlers
import json
import os
from typing import Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import streamlit as st

class LogLevel(Enum):
    """Enhanced log levels for municipal compliance"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"  # Special level for compliance auditing
    SECURITY = "SECURITY"  # Special level for security events

@dataclass
class LogEntry:
    """Structured log entry with municipal compliance fields"""
    timestamp: str
    level: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    outcome: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None

class GovSightLogger:
    """
    Enterprise logging system with compliance and audit features
    
    Features:
    - Structured JSON logging for easy parsing
    - Audit trail compliance for government requirements
    - Security event logging with detailed context
    - Performance monitoring integration
    - Log rotation and retention policies
    - Multi-destination logging (file, console, remote)
    """
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize loggers
        self.app_logger = self._setup_application_logger()
        self.audit_logger = self._setup_audit_logger()
        self.security_logger = self._setup_security_logger()
        self.performance_logger = self._setup_performance_logger()
        
        # Correlation tracking
        self.correlation_id = None
    
    def _setup_application_logger(self) -> logging.Logger:
        """Setup main application logger with rotation"""
        logger = logging.getLogger(f"govsight.app.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / f"{self.name}_app.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=10
            )
            
            # Console handler for development
            console_handler = logging.StreamHandler()
            
            # JSON formatter for structured logging
            formatter = self._create_json_formatter()
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup audit logger for compliance requirements"""
        logger = logging.getLogger(f"govsight.audit.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Separate audit log file with longer retention
            audit_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "audit.log",
                maxBytes=50*1024*1024,  # 50MB
                backupCount=50  # Longer retention for compliance
            )
            
            formatter = self._create_json_formatter()
            audit_handler.setFormatter(formatter)
            logger.addHandler(audit_handler)
        
        return logger
    
    def _setup_security_logger(self) -> logging.Logger:
        """Setup security event logger"""
        logger = logging.getLogger(f"govsight.security.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            security_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "security.log",
                maxBytes=25*1024*1024,  # 25MB
                backupCount=25
            )
            
            formatter = self._create_json_formatter()
            security_handler.setFormatter(formatter)
            logger.addHandler(security_handler)
        
        return logger
    
    def _setup_performance_logger(self) -> logging.Logger:
        """Setup performance monitoring logger"""
        logger = logging.getLogger(f"govsight.performance.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            perf_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / "performance.log",
                maxBytes=25*1024*1024,  # 25MB
                backupCount=10
            )
            
            formatter = self._create_json_formatter()
            perf_handler.setFormatter(formatter)
            logger.addHandler(perf_handler)
        
        return logger
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "module": record.module if hasattr(record, 'module') else None,
                    "function": record.funcName,
                    "line": record.lineno,
                    "message": record.getMessage(),
                }
                
                # Add custom fields if available
                for field in ['user_id', 'session_id', 'ip_address', 'action', 'resource', 'outcome', 'correlation_id']:
                    if hasattr(record, field):
                        log_entry[field] = getattr(record, field)
                
                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry, default=str)
        
        return JSONFormatter()
    
    def _get_context_info(self) -> Dict[str, Any]:
        """Extract context information from Streamlit session"""
        context = {}
        
        try:
            if hasattr(st, 'session_state'):
                # User information
                user_data = getattr(st.session_state, 'user', {})
                if isinstance(user_data, dict):
                    context['user_id'] = user_data.get('username')
                
                # Session information
                context['session_id'] = getattr(st.session_state, 'session_id', None)
                
                # Correlation ID for request tracking
                if self.correlation_id:
                    context['correlation_id'] = self.correlation_id
        except:
            pass  # Gracefully handle if session state is not available
        
        return context
    
    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """Set correlation ID for request tracking"""
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        return self.correlation_id
    
    def log(
        self, 
        level: Union[LogLevel, str], 
        message: str,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        outcome: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        logger_type: str = "app"
    ) -> None:
        """
        Enhanced logging with structured data
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, AUDIT, SECURITY)
            message: Log message
            action: Action being performed (for audit trails)
            resource: Resource being accessed (for audit trails)
            outcome: Outcome of the action (SUCCESS, FAILURE, etc.)
            additional_data: Additional structured data
            logger_type: Type of logger to use (app, audit, security, performance)
        """
        # Select appropriate logger
        if logger_type == "audit" or level == LogLevel.AUDIT:
            logger = self.audit_logger
        elif logger_type == "security" or level == LogLevel.SECURITY:
            logger = self.security_logger
        elif logger_type == "performance":
            logger = self.performance_logger
        else:
            logger = self.app_logger
        
        # Get context information
        context = self._get_context_info()
        
        # Create enhanced log record
        log_level = level.value if isinstance(level, LogLevel) else level
        record = logger.makeRecord(
            name=logger.name,
            level=getattr(logging, log_level.upper(), logging.INFO),
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Add custom fields to the record
        for key, value in context.items():
            setattr(record, key, value)
        
        if action:
            setattr(record, 'action', action)
        if resource:
            setattr(record, 'resource', resource)
        if outcome:
            setattr(record, 'outcome', outcome)
        if additional_data:
            for key, value in additional_data.items():
                setattr(record, f"data_{key}", value)
        
        logger.handle(record)
    
    # Convenience methods for different log levels
    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def audit(self, message: str, action: str, resource: str, outcome: str, **kwargs):
        """Audit log for compliance requirements"""
        self.log(
            LogLevel.AUDIT, 
            message, 
            action=action, 
            resource=resource, 
            outcome=outcome,
            logger_type="audit",
            **kwargs
        )
    
    def security(self, message: str, action: str, outcome: str, **kwargs):
        """Security event log"""
        self.log(
            LogLevel.SECURITY,
            message,
            action=action,
            outcome=outcome,
            logger_type="security",
            **kwargs
        )
    
    def performance(self, message: str, duration: float, operation: str, **kwargs):
        """Performance monitoring log"""
        additional_data = kwargs.get('additional_data', {})
        additional_data.update({
            'duration_ms': duration * 1000,
            'operation': operation
        })
        kwargs['additional_data'] = additional_data
        
        self.log(
            LogLevel.INFO,
            message,
            logger_type="performance",
            **kwargs
        )

class LoggerManager:
    """Centralized logger management"""
    
    def __init__(self):
        self.loggers: Dict[str, GovSightLogger] = {}
    
    def get_logger(self, name: str) -> GovSightLogger:
        """Get or create a logger instance"""
        if name not in self.loggers:
            self.loggers[name] = GovSightLogger(name)
        return self.loggers[name]
    
    def set_correlation_id_all(self, correlation_id: str) -> None:
        """Set correlation ID for all loggers"""
        for logger in self.loggers.values():
            logger.set_correlation_id(correlation_id)
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get summary of logging activity"""
        summary = {
            "active_loggers": len(self.loggers),
            "logger_names": list(self.loggers.keys()),
            "log_files": []
        }
        
        # Check log files
        log_dir = Path("logs")
        if log_dir.exists():
            summary["log_files"] = [
                {
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024*1024), 2),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in log_dir.glob("*.log")
            ]
        
        return summary

# Global logger manager
_logger_manager: Optional[LoggerManager] = None

def get_logger_manager() -> LoggerManager:
    """Get global logger manager instance"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager

def get_logger(name: str) -> GovSightLogger:
    """Get a logger instance"""
    return get_logger_manager().get_logger(name)

# Module-level convenience functions
def audit_log(action: str, resource: str, outcome: str, message: str, **kwargs):
    """Convenience function for audit logging"""
    logger = get_logger("system")
    logger.audit(message, action, resource, outcome, **kwargs)

def security_log(action: str, outcome: str, message: str, **kwargs):
    """Convenience function for security logging"""
    logger = get_logger("security")
    logger.security(message, action, outcome, **kwargs)

def performance_log(operation: str, duration: float, message: str, **kwargs):
    """Convenience function for performance logging"""
    logger = get_logger("performance")
    logger.performance(message, duration, operation, **kwargs)