"""
Comprehensive Audit Middleware for Fluxion Backend
Implements enterprise-grade audit logging with immutable trails,
compliance reporting, and forensic analysis capabilities.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Request, Response
from services.audit.audit_service import AuditService
from services.security.encryption_service import EncryptionService
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types for categorization"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    TRANSACTION = "transaction"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"


class AuditSeverity(Enum):
    """Audit event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Comprehensive audit event structure"""

    event_id: str
    timestamp: str
    event_type: str
    severity: str
    user_id: Optional[str]
    session_id: Optional[str]
    client_ip: str
    user_agent: str
    request_method: str
    request_path: str
    request_params: Dict[str, Any]
    request_headers: Dict[str, str]
    response_status: int
    response_size: int
    processing_time: float
    outcome: str
    details: Dict[str, Any]
    risk_score: float
    compliance_tags: List[str]
    data_classification: str
    geographic_location: Optional[str]
    device_fingerprint: Optional[str]
    business_context: Dict[str, Any]
    integrity_hash: str


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive audit middleware that captures all system interactions
    and creates immutable audit trails for compliance and forensic analysis.
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.audit_service = AuditService()
        self.encryption_service = EncryptionService()
        self.sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
        }
        self.sensitive_params = {
            "password",
            "token",
            "secret",
            "key",
            "pin",
            "ssn",
            "credit_card",
        }
        self.compliance_endpoints = {
            "/api/v1/transactions": ["PCI_DSS", "SOX", "AML"],
            "/api/v1/users": ["GDPR", "CCPA", "KYC"],
            "/api/v1/compliance": ["SOX", "AML", "CFTC"],
            "/api/v1/reports": ["SOX", "SEC", "FINRA"],
        }
        self.risk_factors = {
            "high_value_transaction": 3.0,
            "admin_operation": 2.5,
            "data_export": 2.0,
            "configuration_change": 2.0,
            "failed_authentication": 1.5,
            "suspicious_ip": 1.5,
            "off_hours_access": 1.2,
        }

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        start_time = time.time()
        event_id = self._generate_event_id()
        request_data = await self._capture_request_data(request, event_id)
        try:
            response = await call_next(request)
            response_data = self._capture_response_data(response)
            audit_event = await self._create_audit_event(
                request, response, request_data, response_data, start_time, event_id
            )
            asyncio.create_task(self._log_audit_event(audit_event))
            response.headers["X-Audit-Event-ID"] = event_id
            response.headers["X-Audit-Timestamp"] = audit_event.timestamp
            return response
        except Exception as e:
            error_event = await self._create_error_audit_event(
                request, request_data, str(e), start_time, event_id
            )
            asyncio.create_task(self._log_audit_event(error_event))
            raise

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = str(int(time.time() * 1000000))
        random_part = hashlib.sha256(f"{timestamp}{time.time()}".encode()).hexdigest()[
            :8
        ]
        return f"AUD-{timestamp}-{random_part}"

    async def _capture_request_data(
        self, request: Request, event_id: str
    ) -> Dict[str, Any]:
        """Capture comprehensive request data"""
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "content_type": request.headers.get("content-type", ""),
            "content_length": request.headers.get("content-length", "0"),
        }
        try:
            if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                body = await self._capture_request_body(request)
                request_data["body"] = self._mask_sensitive_data(body)
        except Exception as e:
            logger.warning(f"Failed to capture request body for audit: {e}")
            request_data["body"] = "Failed to capture"
        request_data["user_context"] = await self._extract_user_context(request)
        request_data["device_fingerprint"] = self._generate_device_fingerprint(request)
        request_data["geographic_info"] = await self._get_geographic_info(
            request_data["client_ip"]
        )
        return request_data

    async def _capture_request_body(self, request: Request) -> Dict[str, Any]:
        """Safely capture request body"""
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.body()
                if body:
                    return json.loads(body.decode("utf-8"))
            elif "application/x-www-form-urlencoded" in content_type:
                form_data = await request.form()
                return dict(form_data)
            elif "multipart/form-data" in content_type:
                form_data = await request.form()
                result = {}
                for key, value in form_data.items():
                    if hasattr(value, "filename"):
                        result[key] = {
                            "filename": value.filename,
                            "content_type": getattr(value, "content_type", "unknown"),
                            "size": (
                                len(await value.read())
                                if hasattr(value, "read")
                                else "unknown"
                            ),
                        }
                    else:
                        result[key] = str(value)
                return result
            else:
                body = await request.body()
                return {"size": len(body), "type": content_type}
        except Exception as e:
            logger.warning(f"Error capturing request body: {e}")
            return {"error": "Failed to capture body"}
        return {}

    def _capture_response_data(self, response: Response) -> Dict[str, Any]:
        """Capture response data for audit"""
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type", ""),
            "content_length": response.headers.get("content-length", "0"),
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def _extract_user_context(self, request: Request) -> Dict[str, Any]:
        """Extract user context from request"""
        context = {
            "user_id": None,
            "session_id": None,
            "roles": [],
            "permissions": [],
            "authentication_method": None,
        }
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                context["authentication_method"] = "jwt"
                context["user_id"] = "authenticated_user"
            session_id = request.headers.get("x-session-id")
            if not session_id:
                cookies = request.headers.get("cookie", "")
                for cookie in cookies.split(";"):
                    if "session_id=" in cookie:
                        session_id = cookie.split("session_id=")[1].split(";")[0]
                        break
            context["session_id"] = session_id
        except Exception as e:
            logger.warning(f"Error extracting user context: {e}")
        return context

    def _generate_device_fingerprint(self, request: Request) -> str:
        """Generate device fingerprint for tracking"""
        fingerprint_data = {
            "user_agent": request.headers.get("user-agent", ""),
            "accept": request.headers.get("accept", ""),
            "accept_language": request.headers.get("accept-language", ""),
            "accept_encoding": request.headers.get("accept-encoding", ""),
            "connection": request.headers.get("connection", ""),
            "upgrade_insecure_requests": request.headers.get(
                "upgrade-insecure-requests", ""
            ),
        }
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    async def _get_geographic_info(self, ip_address: str) -> Optional[Dict[str, str]]:
        """Get geographic information for IP address"""
        if ip_address and ip_address != "unknown":
            return {
                "country": "Unknown",
                "region": "Unknown",
                "city": "Unknown",
                "timezone": "Unknown",
            }
        return None

    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive data in request/response"""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if any(
                    (sensitive in key.lower() for sensitive in self.sensitive_params)
                ):
                    masked_data[key] = self._mask_value(str(value))
                else:
                    masked_data[key] = self._mask_sensitive_data(value)
            return masked_data
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        else:
            return data

    def _mask_value(self, value: str) -> str:
        """Mask sensitive value"""
        if len(value) <= 4:
            return "*" * len(value)
        else:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]

    async def _create_audit_event(
        self,
        request: Request,
        response: Response,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        start_time: float,
        event_id: str,
    ) -> AuditEvent:
        """Create comprehensive audit event"""
        processing_time = time.time() - start_time
        timestamp = datetime.now(timezone.utc).isoformat()
        event_type = self._determine_event_type(request, response)
        severity = self._determine_severity(request, response, processing_time)
        risk_score = await self._calculate_risk_score(request, response, request_data)
        compliance_tags = self._get_compliance_tags(request.url.path)
        data_classification = self._classify_data_sensitivity(request.url.path)
        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type.value,
            severity=severity.value,
            user_id=request_data["user_context"].get("user_id"),
            session_id=request_data["user_context"].get("session_id"),
            client_ip=request_data["client_ip"],
            user_agent=request_data["user_agent"],
            request_method=request.method,
            request_path=request.url.path,
            request_params=self._mask_sensitive_data(dict(request.query_params)),
            request_headers=self._mask_sensitive_headers(request_data["headers"]),
            response_status=response.status_code,
            response_size=int(response_data.get("content_length", 0)),
            processing_time=processing_time,
            outcome=self._determine_outcome(response.status_code),
            details={
                "request_body": request_data.get("body", {}),
                "response_headers": response_data["headers"],
                "device_fingerprint": request_data.get("device_fingerprint"),
                "geographic_info": request_data.get("geographic_info"),
                "authentication_method": request_data["user_context"].get(
                    "authentication_method"
                ),
            },
            risk_score=risk_score,
            compliance_tags=compliance_tags,
            data_classification=data_classification,
            geographic_location=self._format_geographic_location(
                request_data.get("geographic_info")
            ),
            device_fingerprint=request_data.get("device_fingerprint"),
            business_context=await self._extract_business_context(request, response),
            integrity_hash="",
        )
        audit_event.integrity_hash = self._calculate_integrity_hash(audit_event)
        return audit_event

    def _determine_event_type(
        self, request: Request, response: Response
    ) -> AuditEventType:
        """Determine audit event type based on request/response"""
        path = request.url.path.lower()
        method = request.method.upper()
        if "/auth/" in path:
            return AuditEventType.AUTHENTICATION
        elif "/transactions/" in path:
            return AuditEventType.TRANSACTION
        elif method in ["POST", "PUT", "PATCH", "DELETE"]:
            return AuditEventType.DATA_MODIFICATION
        elif "/compliance/" in path:
            return AuditEventType.COMPLIANCE_EVENT
        elif "/admin/" in path or "/config/" in path:
            return AuditEventType.CONFIGURATION_CHANGE
        elif response.status_code >= 400:
            return AuditEventType.SECURITY_EVENT
        else:
            return AuditEventType.DATA_ACCESS

    def _determine_severity(
        self, request: Request, response: Response, processing_time: float
    ) -> AuditSeverity:
        """Determine event severity"""
        if response.status_code >= 500:
            return AuditSeverity.CRITICAL
        elif response.status_code >= 400:
            return AuditSeverity.HIGH
        elif "/admin/" in request.url.path or "/transactions/" in request.url.path:
            return AuditSeverity.MEDIUM
        elif processing_time > 5.0:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW

    async def _calculate_risk_score(
        self, request: Request, response: Response, request_data: Dict[str, Any]
    ) -> float:
        """Calculate risk score for the event"""
        base_score = 1.0
        if "/transactions/" in request.url.path and request.method in ["POST", "PUT"]:
            base_score *= self.risk_factors["high_value_transaction"]
        if "/admin/" in request.url.path:
            base_score *= self.risk_factors["admin_operation"]
        if "export" in request.url.path or "download" in request.url.path:
            base_score *= self.risk_factors["data_export"]
        if "/config/" in request.url.path and request.method in [
            "POST",
            "PUT",
            "DELETE",
        ]:
            base_score *= self.risk_factors["configuration_change"]
        if response.status_code == 401:
            base_score *= self.risk_factors["failed_authentication"]
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            base_score *= self.risk_factors["off_hours_access"]
        client_ip = request_data.get("client_ip", "")
        if self._is_suspicious_ip(client_ip):
            base_score *= self.risk_factors["suspicious_ip"]
        return min(base_score, 10.0)

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious"""
        return False

    def _get_compliance_tags(self, path: str) -> List[str]:
        """Get compliance tags for the endpoint"""
        tags = []
        for endpoint_pattern, compliance_reqs in self.compliance_endpoints.items():
            if endpoint_pattern in path:
                tags.extend(compliance_reqs)
        return list(set(tags))

    def _classify_data_sensitivity(self, path: str) -> str:
        """Classify data sensitivity level"""
        if "/transactions/" in path or "/payments/" in path:
            return "HIGHLY_SENSITIVE"
        elif "/users/" in path or "/profiles/" in path:
            return "SENSITIVE"
        elif "/public/" in path or "/health/" in path:
            return "PUBLIC"
        else:
            return "INTERNAL"

    def _mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive headers"""
        masked_headers = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                masked_headers[key] = self._mask_value(value)
            else:
                masked_headers[key] = value
        return masked_headers

    def _determine_outcome(self, status_code: int) -> str:
        """Determine operation outcome"""
        if 200 <= status_code < 300:
            return "SUCCESS"
        elif 300 <= status_code < 400:
            return "REDIRECT"
        elif 400 <= status_code < 500:
            return "CLIENT_ERROR"
        elif 500 <= status_code < 600:
            return "SERVER_ERROR"
        else:
            return "UNKNOWN"

    def _format_geographic_location(
        self, geo_info: Optional[Dict[str, str]]
    ) -> Optional[str]:
        """Format geographic location string"""
        if geo_info:
            return f"{geo_info.get('city', 'Unknown')}, {geo_info.get('region', 'Unknown')}, {geo_info.get('country', 'Unknown')}"
        return None

    async def _extract_business_context(
        self, request: Request, response: Response
    ) -> Dict[str, Any]:
        """Extract business context from request/response"""
        context = {}
        if "/transactions/" in request.url.path:
            context["transaction_type"] = "financial"
        context["user_tier"] = "standard"
        return context

    def _calculate_integrity_hash(self, audit_event: AuditEvent) -> str:
        """Calculate integrity hash for audit event"""
        event_dict = asdict(audit_event)
        event_dict.pop("integrity_hash", None)
        event_json = json.dumps(event_dict, sort_keys=True, default=str)
        return hashlib.sha256(event_json.encode()).hexdigest()

    async def _create_error_audit_event(
        self,
        request: Request,
        request_data: Dict[str, Any],
        error: str,
        start_time: float,
        event_id: str,
    ) -> AuditEvent:
        """Create audit event for errors"""
        processing_time = time.time() - start_time
        timestamp = datetime.now(timezone.utc).isoformat()
        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=AuditEventType.SYSTEM_EVENT.value,
            severity=AuditSeverity.CRITICAL.value,
            user_id=request_data["user_context"].get("user_id"),
            session_id=request_data["user_context"].get("session_id"),
            client_ip=request_data["client_ip"],
            user_agent=request_data["user_agent"],
            request_method=request.method,
            request_path=request.url.path,
            request_params=self._mask_sensitive_data(dict(request.query_params)),
            request_headers=self._mask_sensitive_headers(request_data["headers"]),
            response_status=500,
            response_size=0,
            processing_time=processing_time,
            outcome="ERROR",
            details={
                "error": error,
                "request_body": request_data.get("body", {}),
                "device_fingerprint": request_data.get("device_fingerprint"),
                "geographic_info": request_data.get("geographic_info"),
            },
            risk_score=5.0,
            compliance_tags=self._get_compliance_tags(request.url.path),
            data_classification=self._classify_data_sensitivity(request.url.path),
            geographic_location=self._format_geographic_location(
                request_data.get("geographic_info")
            ),
            device_fingerprint=request_data.get("device_fingerprint"),
            business_context={},
            integrity_hash="",
        )
        audit_event.integrity_hash = self._calculate_integrity_hash(audit_event)
        return audit_event

    async def _log_audit_event(self, audit_event: AuditEvent):
        """Log audit event asynchronously"""
        try:
            await self.audit_service.log_event(audit_event)
        except Exception as e:
            logger.error(f"Failed to log audit event {audit_event.event_id}: {e}")
            logger.info(f"AUDIT_EVENT: {json.dumps(asdict(audit_event), default=str)}")

    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        return await self.audit_service.get_statistics()

    async def search_audit_events(self, criteria: Dict[str, Any]) -> List[AuditEvent]:
        """Search audit events based on criteria"""
        return await self.audit_service.search_events(criteria)
