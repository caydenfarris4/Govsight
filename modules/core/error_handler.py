"""
Enterprise Error Handling Framework
Provides comprehensive error handling with graceful degradation and user-friendly messaging
"""

import traceback
import logging
import streamlit as st
import functools
from typing import Any, Callable, Dict, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid

class ErrorSeverity(Enum):
    """Error severity levels for classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better organization"""
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    FILE_PROCESSING = "file_processing"
    VALIDATION = "validation"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    USER_INPUT = "user_input"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Error context information for comprehensive logging"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    function_name: Optional[str] = None
    module_name: Optional[str] = None
    user_message: Optional[str] = None
    technical_details: Optional[str] = None
    stack_trace: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class GovSightError(Exception):
    """Base exception class for GovSight application errors"""
    
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: Optional[str] = None,
        technical_details: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.user_message = user_message or message
        self.technical_details = technical_details or message
        self.additional_data = additional_data or {}
        self.error_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now()

class DatabaseError(GovSightError):
    """Database-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)

class SecurityError(GovSightError):
    """Security-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.SECURITY, severity=ErrorSeverity.HIGH, **kwargs)

class ValidationError(GovSightError):
    """Input validation errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, severity=ErrorSeverity.LOW, **kwargs)

class ConfigurationError(GovSightError):
    """Configuration-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CONFIGURATION, severity=ErrorSeverity.HIGH, **kwargs)

class ErrorHandler:
    """
    Comprehensive error handling system with multiple reporting mechanisms
    """
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.error_history: Dict[str, ErrorContext] = {}
        self.error_counts: Dict[str, int] = {}
        
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging for errors"""
        logger = logging.getLogger("govsight.errors")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Console handler for development
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler for production logging
            try:
                file_handler = logging.FileHandler('logs/govsight_errors.log')
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except:
                pass  # Gracefully handle if logs directory doesn't exist
        
        return logger
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        show_user_message: bool = True,
        fallback_action: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Comprehensive error handling with logging and user notification
        
        Args:
            error: The exception that occurred
            context: Additional context information
            show_user_message: Whether to show message to user
            fallback_action: Fallback function to execute
            
        Returns:
            Result of fallback_action if provided, None otherwise
        """
        # Generate error context
        error_context = self._create_error_context(error, context or {})
        
        # Log the error
        self._log_error(error_context)
        
        # Store error for debugging
        self.error_history[error_context.error_id] = error_context
        
        # Update error counts for monitoring
        error_key = f"{error_context.category.value}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Show user-friendly message
        if show_user_message:
            self._show_user_message(error_context)
        
        # Execute fallback action if provided
        if fallback_action:
            try:
                return fallback_action()
            except Exception as fallback_error:
                self.logger.error(f"Fallback action failed: {fallback_error}")
        
        return None
    
    def _create_error_context(self, error: Exception, context: Dict[str, Any]) -> ErrorContext:
        """Create comprehensive error context"""
        
        # Extract information from GovSight errors
        if isinstance(error, GovSightError):
            severity = error.severity
            category = error.category
            user_message = error.user_message
            technical_details = error.technical_details
            additional_data = error.additional_data
            error_id = error.error_id
            timestamp = error.timestamp
        else:
            # Default values for standard exceptions
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.SYSTEM
            user_message = "An unexpected error occurred. Please try again."
            technical_details = str(error)
            additional_data = {}
            error_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now()
        
        # Get session information
        session_id = None
        user_id = None
        if hasattr(st, 'session_state'):
            session_id = getattr(st.session_state, 'session_id', None)
            user_data = getattr(st.session_state, 'user', {})
            if isinstance(user_data, dict):
                user_id = user_data.get('username')
        
        # Get function and module information
        stack = traceback.extract_tb(error.__traceback__)
        function_name = None
        module_name = None
        if stack:
            frame = stack[-1]
            function_name = frame.name
            module_name = frame.filename.split('/')[-1] if '/' in frame.filename else frame.filename
        
        return ErrorContext(
            error_id=error_id,
            timestamp=timestamp,
            severity=severity,
            category=category,
            user_id=user_id,
            session_id=session_id,
            function_name=function_name,
            module_name=module_name,
            user_message=user_message,
            technical_details=technical_details,
            stack_trace=traceback.format_exc(),
            additional_data={**additional_data, **context}
        )
    
    def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with appropriate level based on severity"""
        log_message = (
            f"[{error_context.error_id}] {error_context.category.value.upper()} ERROR "
            f"in {error_context.module_name or 'unknown'}::{error_context.function_name or 'unknown'} "
            f"- {error_context.technical_details}"
        )
        
        # Add user context if available
        if error_context.user_id:
            log_message += f" (User: {error_context.user_id})"
        
        # Log based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log stack trace for medium and above
        if error_context.severity.value in ['medium', 'high', 'critical']:
            self.logger.debug(f"Stack trace for {error_context.error_id}:\\n{error_context.stack_trace}")
    
    def _show_user_message(self, error_context: ErrorContext) -> None:
        """Show appropriate user message based on error severity"""
        
        # Choose appropriate Streamlit message type
        if error_context.severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 Critical Error: {error_context.user_message}")
            st.error(f"Error ID: {error_context.error_id} - Please contact support immediately.")
        elif error_context.severity == ErrorSeverity.HIGH:
            st.error(f" {error_context.user_message}")
            st.info(f"Error ID: {error_context.error_id} - Please try again or contact support if the problem persists.")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            st.warning(f" {error_context.user_message}")
        else:
            st.info(f"ℹ️ {error_context.user_message}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors for monitoring"""
        return {
            "total_errors": len(self.error_history),
            "error_counts": self.error_counts,
            "recent_errors": [
                {
                    "id": ctx.error_id,
                    "timestamp": ctx.timestamp.isoformat(),
                    "severity": ctx.severity.value,
                    "category": ctx.category.value,
                    "message": ctx.technical_details[:100] + "..." if len(ctx.technical_details) > 100 else ctx.technical_details
                }
                for ctx in sorted(self.error_history.values(), key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }

# Global error handler instance
_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def handle_errors(
    fallback_return=None,
    show_message: bool = True,
    category: ErrorCategory = ErrorCategory.SYSTEM
):
    """
    Decorator for automatic error handling
    
    Args:
        fallback_return: Value to return if error occurs
        show_message: Whether to show user message
        category: Error category for classification
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Convert to appropriate GovSight error if needed
                if not isinstance(e, GovSightError):
                    e = GovSightError(
                        message=str(e),
                        category=category,
                        technical_details=f"Error in {func.__name__}: {str(e)}"
                    )
                
                handler = get_error_handler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # Limit length
                    "kwargs": str(kwargs)[:200]
                }
                
                handler.handle_error(e, context, show_message)
                return fallback_return
        
        return wrapper
    return decorator

# Convenience functions for specific error types
def handle_database_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Handle database-specific errors"""
    db_error = DatabaseError(
        message="Database operation failed",
        technical_details=str(error),
        user_message="Unable to access database. Please try again in a moment."
    )
    get_error_handler().handle_error(db_error, context)

def handle_security_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Handle security-specific errors"""
    sec_error = SecurityError(
        message="Security validation failed",
        technical_details=str(error),
        user_message="Access denied. Please check your permissions."
    )
    get_error_handler().handle_error(sec_error, context)

def handle_validation_error(error: Exception, field_name: str = "input") -> None:
    """Handle input validation errors"""
    val_error = ValidationError(
        message=f"Validation failed for {field_name}",
        technical_details=str(error),
        user_message=f"Please check your {field_name} and try again."
    )
    get_error_handler().handle_error(val_error)