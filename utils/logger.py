"""
Structured Logging with JSON Format and Performance Metrics
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import streamlit as st
from logging.handlers import RotatingFileHandler
import threading
import time
import functools

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add user context if available
        if hasattr(st.session_state, 'user') and st.session_state.user:
            log_entry['user_id'] = st.session_state.user.get('email', 'unknown')
            log_entry['user_role'] = st.session_state.user.get('role', 'unknown')
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add custom fields from extra
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self, logger_name: str = 'performance'):
        self.logger = logging.getLogger(logger_name)
        self.timers = {}
        self.metrics = {}
        self._lock = threading.Lock()
    
    def start_timer(self, operation: str, context: Dict[str, Any] = None):
        """Start timing an operation"""
        timer_key = f"{operation}_{threading.current_thread().ident}"
        with self._lock:
            self.timers[timer_key] = {
                'start_time': time.time(),
                'operation': operation,
                'context': context or {}
            }
    
    def end_timer(self, operation: str, success: bool = True, additional_metrics: Dict[str, Any] = None):
        """End timing and log performance metrics"""
        timer_key = f"{operation}_{threading.current_thread().ident}"
        
        with self._lock:
            if timer_key not in self.timers:
                self.logger.warning(f"Timer not found for operation: {operation}")
                return
            
            timer_info = self.timers.pop(timer_key)
            duration = time.time() - timer_info['start_time']
            
            metrics = {
                'operation': operation,
                'duration_seconds': round(duration, 4),
                'success': success,
                'context': timer_info['context'],
                'timestamp': datetime.now().isoformat()
            }
            
            if additional_metrics:
                metrics.update(additional_metrics)
            
            # Store metrics for analysis
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(metrics)
            
            # Log performance
            self.logger.info(
                f"Performance: {operation} completed in {duration:.4f}s",
                extra={'extra_fields': metrics}
            )
    
    def get_performance_summary(self, operation: str = None) -> Dict[str, Any]:
        """Get performance summary for operations"""
        with self._lock:
            if operation:
                if operation not in self.metrics:
                    return {}
                
                operation_metrics = self.metrics[operation]
                durations = [m['duration_seconds'] for m in operation_metrics]
                
                return {
                    'operation': operation,
                    'total_calls': len(operation_metrics),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'success_rate': sum(1 for m in operation_metrics if m['success']) / len(operation_metrics)
                }
            else:
                # Summary for all operations
                summary = {}
                for op in self.metrics:
                    summary[op] = self.get_performance_summary(op)
                return summary

class CashFlowLogger:
    """Main application logger with structured logging and performance tracking"""
    
    def __init__(self, app_name: str = 'cash_flow_dashboard'):
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)
        self.performance_logger = PerformanceLogger()
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        log_level = logging.INFO
        if hasattr(st.session_state, 'debug_mode') and st.session_state.debug_mode:
            log_level = logging.DEBUG
        
        self.logger.setLevel(log_level)
        
        # JSON formatter
        json_formatter = JSONFormatter()
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_dir / f'{self.app_name}.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(logging.INFO)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            log_dir / f'{self.app_name}_errors.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setFormatter(json_formatter)
        error_handler.setLevel(logging.ERROR)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        console_handler.setLevel(logging.WARNING)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        # Performance logger setup
        perf_handler = RotatingFileHandler(
            log_dir / f'{self.app_name}_performance.log',
            maxBytes=5*1024*1024,
            backupCount=3
        )
        perf_handler.setFormatter(json_formatter)
        self.performance_logger.logger.addHandler(perf_handler)
        self.performance_logger.logger.setLevel(logging.INFO)
    
    def log_user_action(self, action: str, details: Dict[str, Any] = None, user_id: str = None):
        """Log user actions with context"""
        user_id = user_id or self._get_current_user_id()
        
        log_data = {
            'action_type': 'user_action',
            'action': action,
            'user_id': user_id,
            'details': details or {},
            'session_id': self._get_session_id()
        }
        
        self.logger.info(f"User action: {action}", extra={'extra_fields': log_data})
    
    def log_financial_operation(self, operation: str, amount: float = None, 
                              currency: str = None, details: Dict[str, Any] = None):
        """Log financial operations with amounts and currency"""
        user_id = self._get_current_user_id()
        
        log_data = {
            'operation_type': 'financial',
            'operation': operation,
            'amount': amount,
            'currency': currency,
            'user_id': user_id,
            'details': details or {},
            'session_id': self._get_session_id()
        }
        
        self.logger.info(f"Financial operation: {operation}", extra={'extra_fields': log_data})
    
    def log_api_call(self, service: str, endpoint: str, status_code: int = None, 
                    response_time: float = None, error: str = None):
        """Log external API calls"""
        log_data = {
            'call_type': 'api_call',
            'service': service,
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time_ms': response_time * 1000 if response_time else None,
            'error': error,
            'user_id': self._get_current_user_id()
        }
        
        level = logging.ERROR if error else logging.INFO
        message = f"API call to {service}: {endpoint}"
        if error:
            message += f" - Error: {error}"
        
        self.logger.log(level, message, extra={'extra_fields': log_data})
    
    def log_data_operation(self, operation: str, table: str = None, 
                          records_affected: int = None, details: Dict[str, Any] = None):
        """Log database operations"""
        log_data = {
            'operation_type': 'data_operation',
            'operation': operation,
            'table': table,
            'records_affected': records_affected,
            'user_id': self._get_current_user_id(),
            'details': details or {}
        }
        
        self.logger.info(f"Data operation: {operation}", extra={'extra_fields': log_data})
    
    def log_security_event(self, event_type: str, severity: str = 'info', 
                          details: Dict[str, Any] = None):
        """Log security-related events"""
        log_data = {
            'event_type': 'security',
            'security_event': event_type,
            'severity': severity,
            'user_id': self._get_current_user_id(),
            'ip_address': self._get_client_ip(),
            'details': details or {}
        }
        
        level_map = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        
        level = level_map.get(severity, logging.INFO)
        self.logger.log(level, f"Security event: {event_type}", extra={'extra_fields': log_data})
    
    def _get_current_user_id(self) -> str:
        """Get current user ID from session"""
        if hasattr(st.session_state, 'user') and st.session_state.user:
            return st.session_state.user.get('email', 'anonymous')
        return 'anonymous'
    
    def _get_session_id(self) -> str:
        """Get session ID"""
        return getattr(st.session_state, 'session_id', 'unknown')
    
    def _get_client_ip(self) -> str:
        """Get client IP address (simplified for Streamlit)"""
        return '127.0.0.1'  # In production, extract from headers

def performance_monitor(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            perf_logger = PerformanceLogger()
            
            perf_logger.start_timer(op_name, {'function': func.__name__})
            
            try:
                result = func(*args, **kwargs)
                perf_logger.end_timer(op_name, success=True)
                return result
            except Exception as e:
                perf_logger.end_timer(op_name, success=False, additional_metrics={'error': str(e)})
                raise
        
        return wrapper
    return decorator

def log_user_action(action: str, details: Dict[str, Any] = None):
    """Convenience function to log user actions"""
    logger = CashFlowLogger()
    logger.log_user_action(action, details)

def log_financial_operation(operation: str, amount: float = None, currency: str = None, details: Dict[str, Any] = None):
    """Convenience function to log financial operations"""
    logger = CashFlowLogger()
    logger.log_financial_operation(operation, amount, currency, details)

# Global logger instance
app_logger = CashFlowLogger()

# Backward compatibility
def setup_logging():
    """Setup logging (for backward compatibility)"""
    return app_logger
