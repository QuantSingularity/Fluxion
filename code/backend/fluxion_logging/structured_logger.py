"""
Comprehensive Structured Logging System for Fluxion Backend
Implements enterprise-grade logging with structured formats, correlation IDs,
security event logging, and compliance audit trails.
"""

import json
import logging
import logging.handlers
import sys
import threading
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings


class LogLevel(Enum):
    """Log levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """Types of events for structured logging"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    TRANSACTION = "transaction"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    AUDIT = "audit"
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"
    SYSTEM = "system"


@dataclass
class LogContext:
    """Log context information"""

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None


@dataclass
class StructuredLogEntry:
    """Structured log entry"""

    timestamp: str
    level: str
    message: str
    event_type: str
    service: str
    version: str
    environment: str
    context: LogContext
    data: Dict[str, Any]
    error: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    compliance: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def __init__(
        self, service_name: str = "fluxion-backend", version: str = "1.0.0"
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.version = version
        self.environment = getattr(settings, "ENVIRONMENT", "development")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        context = getattr(_context_storage, "context", LogContext())
        data = {}
        error_info = None
        performance_info = None
        security_info = None
        compliance_info = None
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                if key.startswith("perf_"):
                    if not performance_info:
                        performance_info = {}
                    performance_info[key[5:]] = value
                elif key.startswith("security_"):
                    if not security_info:
                        security_info = {}
                    security_info[key[9:]] = value
                elif key.startswith("compliance_"):
                    if not compliance_info:
                        compliance_info = {}
                    compliance_info[key[11:]] = value
                else:
                    data[key] = value
        if record.exc_info:
            error_info = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        event_type = getattr(record, "event_type", EventType.SYSTEM.value)
        log_entry = StructuredLogEntry(
            timestamp=datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            event_type=event_type,
            service=self.service_name,
            version=self.version,
            environment=self.environment,
            context=context,
            data=data,
            error=error_info,
            performance=performance_info,
            security=security_info,
            compliance=compliance_info,
        )
        return json.dumps(asdict(log_entry), default=str, ensure_ascii=False)


class SecurityLogger:
    """Specialized logger for security events"""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def log_authentication_attempt(
        self,
        user_id: Optional[str],
        success: bool,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Log authentication attempt"""
        self.logger.info(
            f"Authentication {('successful' if success else 'failed')} for user {user_id or 'unknown'}",
            extra={
                "event_type": EventType.AUTHENTICATION.value,
                "security_user_id": user_id,
                "security_success": success,
                "security_reason": reason,
                **kwargs,
            },
        )

    def log_authorization_check(
        self, user_id: str, resource: str, action: str, granted: bool, **kwargs
    ) -> Any:
        """Log authorization check"""
        self.logger.info(
            f"Authorization {('granted' if granted else 'denied')} for user {user_id} on resource {resource} for action {action}",
            extra={
                "event_type": EventType.AUTHORIZATION.value,
                "security_user_id": user_id,
                "security_resource": resource,
                "security_action": action,
                "security_granted": granted,
                **kwargs,
            },
        )

    def log_security_incident(
        self, incident_type: str, severity: str, description: str, **kwargs
    ) -> Any:
        """Log security incident"""
        self.logger.warning(
            f"Security incident: {incident_type} - {description}",
            extra={
                "event_type": EventType.SECURITY.value,
                "security_incident_type": incident_type,
                "security_severity": severity,
                "security_description": description,
                **kwargs,
            },
        )

    def log_suspicious_activity(
        self,
        activity_type: str,
        user_id: Optional[str],
        details: Dict[str, Any],
        **kwargs,
    ) -> Any:
        """Log suspicious activity"""
        self.logger.warning(
            f"Suspicious activity detected: {activity_type} for user {user_id or 'unknown'}",
            extra={
                "event_type": EventType.SECURITY.value,
                "security_activity_type": activity_type,
                "security_user_id": user_id,
                "security_details": details,
                **kwargs,
            },
        )


class ComplianceLogger:
    """Specialized logger for compliance events"""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def log_data_access(
        self, user_id: str, data_type: str, action: str, record_count: int, **kwargs
    ) -> Any:
        """Log data access for compliance"""
        self.logger.info(
            f"Data access: User {user_id} performed {action} on {record_count} {data_type} records",
            extra={
                "event_type": EventType.COMPLIANCE.value,
                "compliance_user_id": user_id,
                "compliance_data_type": data_type,
                "compliance_action": action,
                "compliance_record_count": record_count,
                **kwargs,
            },
        )

    def log_data_modification(
        self,
        user_id: str,
        data_type: str,
        record_id: str,
        changes: Dict[str, Any],
        **kwargs,
    ) -> Any:
        """Log data modification for audit trail"""
        self.logger.info(
            f"Data modification: User {user_id} modified {data_type} record {record_id}",
            extra={
                "event_type": EventType.AUDIT.value,
                "compliance_user_id": user_id,
                "compliance_data_type": data_type,
                "compliance_record_id": record_id,
                "compliance_changes": changes,
                **kwargs,
            },
        )

    def log_regulatory_event(
        self, regulation: str, event_type: str, details: Dict[str, Any], **kwargs
    ) -> Any:
        """Log regulatory compliance event"""
        self.logger.info(
            f"Regulatory event: {regulation} - {event_type}",
            extra={
                "event_type": EventType.COMPLIANCE.value,
                "compliance_regulation": regulation,
                "compliance_event_type": event_type,
                "compliance_details": details,
                **kwargs,
            },
        )


class PerformanceLogger:
    """Specialized logger for performance events"""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def log_request_performance(
        self, endpoint: str, method: str, duration_ms: float, status_code: int, **kwargs
    ) -> Any:
        """Log request performance"""
        level = logging.WARNING if duration_ms > 2000 else logging.INFO
        self.logger.log(
            level,
            f"Request performance: {method} {endpoint} took {duration_ms:.2f}ms (status: {status_code})",
            extra={
                "event_type": EventType.PERFORMANCE.value,
                "perf_endpoint": endpoint,
                "perf_method": method,
                "perf_duration_ms": duration_ms,
                "perf_status_code": status_code,
                **kwargs,
            },
        )

    def log_database_performance(
        self, query_type: str, duration_ms: float, rows_affected: int, **kwargs
    ) -> Any:
        """Log database performance"""
        level = logging.WARNING if duration_ms > 1000 else logging.INFO
        self.logger.log(
            level,
            f"Database performance: {query_type} took {duration_ms:.2f}ms (rows: {rows_affected})",
            extra={
                "event_type": EventType.PERFORMANCE.value,
                "perf_query_type": query_type,
                "perf_duration_ms": duration_ms,
                "perf_rows_affected": rows_affected,
                **kwargs,
            },
        )


class BusinessLogger:
    """Specialized logger for business events"""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def log_transaction(
        self,
        transaction_id: str,
        user_id: str,
        transaction_type: str,
        amount: float,
        currency: str,
        status: str,
        **kwargs,
    ) -> Any:
        """Log business transaction"""
        self.logger.info(
            f"Transaction {status}: {transaction_id} - {transaction_type} of {amount} {currency} for user {user_id}",
            extra={
                "event_type": EventType.TRANSACTION.value,
                "transaction_id": transaction_id,
                "user_id": user_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency,
                "status": status,
                **kwargs,
            },
        )

    def log_user_action(
        self, user_id: str, action: str, resource: str, result: str, **kwargs
    ) -> Any:
        """Log user business action"""
        self.logger.info(
            f"User action: {user_id} performed {action} on {resource} with result {result}",
            extra={
                "event_type": EventType.BUSINESS.value,
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                **kwargs,
            },
        )


_context_storage = threading.local()


class FluxionLogger:
    """Main logger class for Fluxion backend"""

    def __init__(self, name: str = "fluxion-backend") -> None:
        self.name = name
        self.logger = logging.getLogger(name)
        self.formatter = StructuredFormatter(service_name=name)
        self._setup_handlers()
        log_level = getattr(settings, "LOG_LEVEL", "INFO")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.security = SecurityLogger(self.logger)
        self.compliance = ComplianceLogger(self.logger)
        self.performance = PerformanceLogger(self.logger)
        self.business = BusinessLogger(self.logger)

    def _setup_handlers(self) -> Any:
        """Set up log handlers"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "fluxion-backend.log", maxBytes=100 * 1024 * 1024, backupCount=10
        )
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
        security_handler = logging.handlers.RotatingFileHandler(
            log_dir / "security.log", maxBytes=50 * 1024 * 1024, backupCount=20
        )
        security_handler.setFormatter(self.formatter)
        security_handler.addFilter(
            lambda record: getattr(record, "event_type", "")
            in [
                EventType.AUTHENTICATION.value,
                EventType.AUTHORIZATION.value,
                EventType.SECURITY.value,
            ]
        )
        self.logger.addHandler(security_handler)
        compliance_handler = logging.handlers.RotatingFileHandler(
            log_dir / "compliance.log", maxBytes=50 * 1024 * 1024, backupCount=50
        )
        compliance_handler.setFormatter(self.formatter)
        compliance_handler.addFilter(
            lambda record: getattr(record, "event_type", "")
            in [EventType.COMPLIANCE.value, EventType.AUDIT.value]
        )
        self.logger.addHandler(compliance_handler)
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log", maxBytes=50 * 1024 * 1024, backupCount=10
        )
        error_handler.setFormatter(self.formatter)
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)

    @contextmanager
    def context(self, **context_data) -> Any:
        """Context manager for adding context to logs"""
        current_context = getattr(_context_storage, "context", LogContext())
        new_context = LogContext(
            request_id=context_data.get("request_id", current_context.request_id),
            user_id=context_data.get("user_id", current_context.user_id),
            session_id=context_data.get("session_id", current_context.session_id),
            trace_id=context_data.get("trace_id", current_context.trace_id),
            span_id=context_data.get("span_id", current_context.span_id),
            ip_address=context_data.get("ip_address", current_context.ip_address),
            user_agent=context_data.get("user_agent", current_context.user_agent),
            endpoint=context_data.get("endpoint", current_context.endpoint),
            method=context_data.get("method", current_context.method),
        )
        old_context = getattr(_context_storage, "context", None)
        _context_storage.context = new_context
        try:
            yield self
        finally:
            if old_context:
                _context_storage.context = old_context
            elif hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def debug(self, message: str, **kwargs) -> Any:
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> Any:
        """Log info message"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> Any:
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> Any:
        """Log error message"""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> Any:
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs) -> Any:
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)


fluxion_logger = FluxionLogger()


def get_logger(name: str = "fluxion-backend") -> FluxionLogger:
    """Get logger instance"""
    if name == "fluxion-backend":
        return fluxion_logger
    else:
        return FluxionLogger(name)


def set_context(**context_data) -> Any:
    """Set logging context for current thread"""
    context = LogContext(
        request_id=context_data.get("request_id"),
        user_id=context_data.get("user_id"),
        session_id=context_data.get("session_id"),
        trace_id=context_data.get("trace_id"),
        span_id=context_data.get("span_id"),
        ip_address=context_data.get("ip_address"),
        user_agent=context_data.get("user_agent"),
        endpoint=context_data.get("endpoint"),
        method=context_data.get("method"),
    )
    _context_storage.context = context


def clear_context() -> Any:
    """Clear logging context for current thread"""
    if hasattr(_context_storage, "context"):
        delattr(_context_storage, "context")


def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:16]}"


def generate_trace_id() -> str:
    """Generate unique trace ID"""
    return f"trace_{uuid.uuid4().hex[:16]}"


def log_request(func: Any) -> Any:
    """Decorator to automatically log request start/end"""

    def wrapper(*args, **kwargs):
        request_id = generate_request_id()
        with fluxion_logger.context(request_id=request_id):
            fluxion_logger.info(f"Request started: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                fluxion_logger.info(f"Request completed: {func.__name__}")
                return result
            except Exception as e:
                fluxion_logger.error(f"Request failed: {func.__name__} - {str(e)}")
                raise

    return wrapper
