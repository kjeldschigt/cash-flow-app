"""
Logging service for application-wide logging.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
from ..config.environment import EnvironmentManager


class LoggingService:
    """Centralized logging service."""
    
    def __init__(self, log_level: Optional[str] = None, log_file: Optional[str] = None):
        self.env_manager = EnvironmentManager()
        self.log_level = log_level or self.env_manager.get_log_level()
        self.log_file = log_file or "logs/cashflow.log"
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create logger
        self.logger = logging.getLogger('cashflow_app')
        self.logger.setLevel(getattr(logging, self.log_level))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler with rotation
        if self.log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(file_handler)
        
        # Console handler
        if self.env_manager.is_development():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.log_level))
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.critical(message, extra=kwargs)
    
    def log_user_action(self, user_id: str, action: str, details: Optional[str] = None) -> None:
        """Log user action for audit trail."""
        message = f"User {user_id} performed action: {action}"
        if details:
            message += f" - {details}"
        self.info(message, user_id=user_id, action=action)
    
    def log_api_call(self, service: str, endpoint: str, status_code: int, duration: float) -> None:
        """Log external API call."""
        self.info(
            f"API call to {service} {endpoint} - Status: {status_code} - Duration: {duration:.2f}s",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            duration=duration
        )
    
    def log_database_operation(self, operation: str, table: str, duration: float) -> None:
        """Log database operation."""
        self.debug(
            f"Database {operation} on {table} - Duration: {duration:.3f}s",
            operation=operation,
            table=table,
            duration=duration
        )


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logger() -> LoggingService:
    """Get the global logging service instance."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def configure_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> LoggingService:
    """Configure and return the global logging service."""
    global _logging_service
    _logging_service = LoggingService(log_level, log_file)
    return _logging_service
