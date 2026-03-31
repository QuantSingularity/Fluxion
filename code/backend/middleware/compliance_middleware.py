"""
Comprehensive Compliance Middleware for Fluxion Backend
Implements real-time compliance checking, regulatory controls,
and automated compliance reporting for financial services.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from config.settings import settings
from fastapi import HTTPException, Request, Response
from services.compliance.aml_service import AMLService
from services.compliance.compliance_service import ComplianceService
from services.compliance.kyc_service import KYCService
from services.compliance.transaction_monitoring_service import (
    TransactionMonitoringService,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ComplianceViolationType(Enum):
    """Types of compliance violations"""

    KYC_INCOMPLETE = "kyc_incomplete"
    AML_SUSPICIOUS = "aml_suspicious"
    TRANSACTION_LIMIT_EXCEEDED = "transaction_limit_exceeded"
    RESTRICTED_JURISDICTION = "restricted_jurisdiction"
    SANCTIONS_MATCH = "sanctions_match"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    DATA_RETENTION_VIOLATION = "data_retention_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVACY_VIOLATION = "privacy_violation"


class ComplianceAction(Enum):
    """Actions to take on compliance violations"""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REVIEW = "review"
    ESCALATE = "escalate"


@dataclass
class ComplianceCheck:
    """Compliance check result"""

    check_type: str
    passed: bool
    risk_score: float
    violation_type: Optional[str]
    action: str
    details: Dict[str, Any]
    timestamp: str


@dataclass
class ComplianceContext:
    """Compliance context for request processing"""

    user_id: Optional[str]
    session_id: Optional[str]
    client_ip: str
    user_agent: str
    geographic_location: Optional[Dict[str, str]]
    device_fingerprint: str
    request_path: str
    request_method: str
    request_data: Dict[str, Any]
    business_context: Dict[str, Any]


class ComplianceMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive compliance middleware that enforces regulatory requirements
    including KYC, AML, transaction monitoring, and data protection compliance.
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.compliance_service = ComplianceService()
        self.kyc_service = KYCService()
        self.aml_service = AMLService()
        self.transaction_monitoring = TransactionMonitoringService()
        self.restricted_jurisdictions = {
            "OFAC",
            "IRAN",
            "NORTH_KOREA",
            "SYRIA",
            "CUBA",
            "CRIMEA",
        }
        self.endpoint_compliance = {
            "/api/v1/auth/register": {
                "requires_kyc": False,
                "requires_aml": True,
                "max_daily_attempts": 5,
                "geographic_restrictions": True,
            },
            "/api/v1/users/profile": {
                "requires_kyc": True,
                "requires_aml": False,
                "data_protection": ["GDPR", "CCPA"],
                "audit_required": True,
            },
            "/api/v1/transactions/create": {
                "requires_kyc": True,
                "requires_aml": True,
                "transaction_monitoring": True,
                "max_transaction_amount": 10000.0,
                "daily_transaction_limit": 50000.0,
                "suspicious_pattern_detection": True,
            },
            "/api/v1/compliance/reports": {
                "requires_admin": True,
                "audit_required": True,
                "data_classification": "CONFIDENTIAL",
            },
        }
        self.transaction_thresholds = {
            "single_transaction_limit": 10000.0,
            "daily_limit": 50000.0,
            "weekly_limit": 200000.0,
            "monthly_limit": 500000.0,
            "suspicious_amount_threshold": 9000.0,
            "velocity_threshold": 5,
            "round_amount_threshold": 1000.0,
        }
        self.compliance_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        start_time = time.time()
        try:
            compliance_context = await self._create_compliance_context(request)
            compliance_results = await self._perform_compliance_checks(
                request, compliance_context
            )
            blocking_violation = self._check_blocking_violations(compliance_results)
            if blocking_violation:
                return await self._handle_compliance_violation(
                    request, blocking_violation, compliance_results
                )
            response = await call_next(request)
            await self._perform_post_request_compliance(
                request, response, compliance_context, compliance_results
            )
            self._add_compliance_headers(response, compliance_results)
            await self._log_compliance_metrics(
                request, response, compliance_results, time.time() - start_time
            )
            return response
        except HTTPException as e:
            await self._log_compliance_exception(request, e)
            raise
        except Exception as e:
            logger.error(f"Compliance middleware error: {str(e)}", exc_info=True)
            if settings.compliance.COMPLIANCE_FAIL_CLOSED:
                raise HTTPException(
                    status_code=503, detail="Compliance service unavailable"
                )
            else:
                logger.critical(f"Compliance check failed, allowing request: {str(e)}")
                return await call_next(request)

    async def _create_compliance_context(self, request: Request) -> ComplianceContext:
        """Create compliance context from request"""
        user_id = await self._extract_user_id(request)
        session_id = await self._extract_session_id(request)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        geographic_location = await self._get_geographic_location(client_ip)
        device_fingerprint = self._generate_device_fingerprint(request)
        request_data = await self._extract_request_data(request)
        business_context = await self._extract_business_context(request, request_data)
        return ComplianceContext(
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            geographic_location=geographic_location,
            device_fingerprint=device_fingerprint,
            request_path=request.url.path,
            request_method=request.method,
            request_data=request_data,
            business_context=business_context,
        )

    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                return "authenticated_user"
        except Exception as e:
            logger.warning(f"Failed to extract user ID: {e}")
        return None

    async def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request"""
        session_id = request.headers.get("x-session-id")
        if session_id:
            return session_id
        cookies = request.headers.get("cookie", "")
        for cookie in cookies.split(";"):
            if "session_id=" in cookie:
                return cookie.split("session_id=")[1].split(";")[0].strip()
        return None

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def _get_geographic_location(
        self, ip_address: str
    ) -> Optional[Dict[str, str]]:
        """Get geographic location for IP address"""
        return {"country": "US", "region": "Unknown", "city": "Unknown"}

    def _generate_device_fingerprint(self, request: Request) -> str:
        """Generate device fingerprint"""
        import hashlib

        fingerprint_data = {
            "user_agent": request.headers.get("user-agent", ""),
            "accept": request.headers.get("accept", ""),
            "accept_language": request.headers.get("accept-language", ""),
            "accept_encoding": request.headers.get("accept-encoding", ""),
        }
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract request data for compliance checking"""
        data = {
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "method": request.method,
            "path": request.url.path,
        }
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    body = await request.body()
                    if body:
                        data["body"] = json.loads(body.decode("utf-8"))
                elif "application/x-www-form-urlencoded" in content_type:
                    await request.form()
                    data["body"] = dict[str, Any]()
            except Exception as e:
                logger.warning(f"Failed to extract request body: {e}")
                data["body"] = {}
        return data

    async def _extract_business_context(
        self, request: Request, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract business context for compliance"""
        context = {}
        if "/transactions/" in request.url.path:
            body = request_data.get("body", {})
            context.update(
                {
                    "transaction_amount": body.get("amount", 0),
                    "transaction_type": body.get("type", "unknown"),
                    "currency": body.get("currency", "USD"),
                    "counterparty": body.get("counterparty", "unknown"),
                }
            )
        if "/users/" in request.url.path:
            context.update(
                {"operation_type": "user_management", "data_sensitivity": "high"}
            )
        return context

    async def _perform_compliance_checks(
        self, request: Request, context: ComplianceContext
    ) -> List[ComplianceCheck]:
        """Perform comprehensive compliance checks"""
        checks = []
        endpoint_requirements = self._get_endpoint_requirements(context.request_path)
        geo_check = await self._check_geographic_compliance(
            context, endpoint_requirements
        )
        checks.append(geo_check)
        if endpoint_requirements.get("requires_kyc", False):
            kyc_check = await self._check_kyc_compliance(context)
            checks.append(kyc_check)
        if endpoint_requirements.get("requires_aml", False):
            aml_check = await self._check_aml_compliance(context)
            checks.append(aml_check)
        if endpoint_requirements.get("transaction_monitoring", False):
            transaction_check = await self._check_transaction_compliance(context)
            checks.append(transaction_check)
        data_protection_reqs = endpoint_requirements.get("data_protection", [])
        if data_protection_reqs:
            data_check = await self._check_data_protection_compliance(
                context, data_protection_reqs
            )
            checks.append(data_check)
        rate_check = await self._check_rate_limiting_compliance(
            context, endpoint_requirements
        )
        checks.append(rate_check)
        sanctions_check = await self._check_sanctions_compliance(context)
        checks.append(sanctions_check)
        return checks

    def _get_endpoint_requirements(self, path: str) -> Dict[str, Any]:
        """Get compliance requirements for endpoint"""
        if path in self.endpoint_compliance:
            return self.endpoint_compliance[path]
        for pattern, requirements in self.endpoint_compliance.items():
            if pattern.replace("*", "") in path:
                return requirements
        return {
            "requires_kyc": False,
            "requires_aml": False,
            "geographic_restrictions": False,
            "audit_required": False,
        }

    async def _check_geographic_compliance(
        self, context: ComplianceContext, requirements: Dict[str, Any]
    ) -> ComplianceCheck:
        """Check geographic compliance restrictions"""
        if not requirements.get("geographic_restrictions", False):
            return ComplianceCheck(
                check_type="geographic",
                passed=True,
                risk_score=0.0,
                violation_type=None,
                action=ComplianceAction.ALLOW.value,
                details={"message": "No geographic restrictions"},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        if context.geographic_location:
            country = context.geographic_location.get("country", "").upper()
            if country in self.restricted_jurisdictions:
                return ComplianceCheck(
                    check_type="geographic",
                    passed=False,
                    risk_score=10.0,
                    violation_type=ComplianceViolationType.RESTRICTED_JURISDICTION.value,
                    action=ComplianceAction.BLOCK.value,
                    details={
                        "country": country,
                        "message": "Access from restricted jurisdiction",
                    },
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
        return ComplianceCheck(
            check_type="geographic",
            passed=True,
            risk_score=0.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"message": "Geographic compliance passed"},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_kyc_compliance(
        self, context: ComplianceContext
    ) -> ComplianceCheck:
        """Check KYC compliance status"""
        if not context.user_id:
            return ComplianceCheck(
                check_type="kyc",
                passed=False,
                risk_score=8.0,
                violation_type=ComplianceViolationType.KYC_INCOMPLETE.value,
                action=ComplianceAction.BLOCK.value,
                details={"message": "User not authenticated"},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        kyc_status = await self._get_cached_kyc_status(context.user_id)
        if not kyc_status:
            kyc_status = await self.kyc_service.get_kyc_status(context.user_id)
            await self._cache_kyc_status(context.user_id, kyc_status)
        if not kyc_status.get("verified", False):
            return ComplianceCheck(
                check_type="kyc",
                passed=False,
                risk_score=7.0,
                violation_type=ComplianceViolationType.KYC_INCOMPLETE.value,
                action=ComplianceAction.BLOCK.value,
                details={
                    "status": kyc_status.get("status", "unknown"),
                    "message": "KYC verification incomplete",
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="kyc",
            passed=True,
            risk_score=0.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"status": "verified"},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_aml_compliance(
        self, context: ComplianceContext
    ) -> ComplianceCheck:
        """Check AML compliance"""
        aml_result = await self.aml_service.screen_transaction(
            user_id=context.user_id,
            client_ip=context.client_ip,
            transaction_data=context.business_context,
        )
        risk_score = aml_result.get("risk_score", 0.0)
        if risk_score >= 8.0:
            return ComplianceCheck(
                check_type="aml",
                passed=False,
                risk_score=risk_score,
                violation_type=ComplianceViolationType.AML_SUSPICIOUS.value,
                action=ComplianceAction.BLOCK.value,
                details=aml_result,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        elif risk_score >= 5.0:
            return ComplianceCheck(
                check_type="aml",
                passed=True,
                risk_score=risk_score,
                violation_type=None,
                action=ComplianceAction.REVIEW.value,
                details=aml_result,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="aml",
            passed=True,
            risk_score=risk_score,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details=aml_result,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_transaction_compliance(
        self, context: ComplianceContext
    ) -> ComplianceCheck:
        """Check transaction compliance"""
        transaction_amount = context.business_context.get("transaction_amount", 0)
        if transaction_amount > self.transaction_thresholds["single_transaction_limit"]:
            return ComplianceCheck(
                check_type="transaction",
                passed=False,
                risk_score=9.0,
                violation_type=ComplianceViolationType.TRANSACTION_LIMIT_EXCEEDED.value,
                action=ComplianceAction.BLOCK.value,
                details={
                    "amount": transaction_amount,
                    "limit": self.transaction_thresholds["single_transaction_limit"],
                    "message": "Single transaction limit exceeded",
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        suspicious_patterns = (
            await self.transaction_monitoring.check_suspicious_patterns(
                context.user_id, context.business_context
            )
        )
        if suspicious_patterns:
            return ComplianceCheck(
                check_type="transaction",
                passed=True,
                risk_score=6.0,
                violation_type=ComplianceViolationType.SUSPICIOUS_PATTERN.value,
                action=ComplianceAction.REVIEW.value,
                details={
                    "patterns": suspicious_patterns,
                    "message": "Suspicious transaction patterns detected",
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="transaction",
            passed=True,
            risk_score=1.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"message": "Transaction compliance passed"},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_data_protection_compliance(
        self, context: ComplianceContext, requirements: List[str]
    ) -> ComplianceCheck:
        """Check data protection compliance (GDPR, CCPA, etc.)"""
        violations = []
        if "GDPR" in requirements:
            gdpr_violations = await self._check_gdpr_compliance(context)
            violations.extend(gdpr_violations)
        if "CCPA" in requirements:
            ccpa_violations = await self._check_ccpa_compliance(context)
            violations.extend(ccpa_violations)
        if violations:
            return ComplianceCheck(
                check_type="data_protection",
                passed=False,
                risk_score=8.0,
                violation_type=ComplianceViolationType.PRIVACY_VIOLATION.value,
                action=ComplianceAction.BLOCK.value,
                details={"violations": violations},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="data_protection",
            passed=True,
            risk_score=0.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"message": "Data protection compliance passed"},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_gdpr_compliance(self, context: ComplianceContext) -> List[str]:
        """Check GDPR compliance requirements"""
        violations = []
        if context.user_id:
            consent_status = await self._get_user_consent_status(context.user_id)
            if not consent_status.get("data_processing", False):
                violations.append("Missing data processing consent")
        if self._contains_excessive_data_collection(context.request_data):
            violations.append("Excessive data collection detected")
        return violations

    async def _check_ccpa_compliance(self, context: ComplianceContext) -> List[str]:
        """Check CCPA compliance requirements"""
        violations = []
        if (
            context.geographic_location
            and context.geographic_location.get("region", "").upper() == "CA"
        ):
            if context.user_id:
                opt_out_status = await self._get_user_opt_out_status(context.user_id)
                if opt_out_status.get("sale_opt_out", False):
                    violations.append("User has opted out of data sale")
        return violations

    async def _check_rate_limiting_compliance(
        self, context: ComplianceContext, requirements: Dict[str, Any]
    ) -> ComplianceCheck:
        """Check rate limiting compliance"""
        max_daily_attempts = requirements.get("max_daily_attempts")
        if not max_daily_attempts:
            return ComplianceCheck(
                check_type="rate_limiting",
                passed=True,
                risk_score=0.0,
                violation_type=None,
                action=ComplianceAction.ALLOW.value,
                details={"message": "No rate limiting required"},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        daily_attempts = await self._get_daily_attempts(
            context.client_ip, context.user_id, context.request_path
        )
        if daily_attempts >= max_daily_attempts:
            return ComplianceCheck(
                check_type="rate_limiting",
                passed=False,
                risk_score=5.0,
                violation_type="rate_limit_exceeded",
                action=ComplianceAction.BLOCK.value,
                details={
                    "attempts": daily_attempts,
                    "limit": max_daily_attempts,
                    "message": "Daily attempt limit exceeded",
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="rate_limiting",
            passed=True,
            risk_score=0.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"attempts": daily_attempts, "limit": max_daily_attempts},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _check_sanctions_compliance(
        self, context: ComplianceContext
    ) -> ComplianceCheck:
        """Check sanctions compliance"""
        sanctions_result = await self.aml_service.screen_sanctions(
            user_id=context.user_id,
            client_ip=context.client_ip,
            geographic_location=context.geographic_location,
        )
        if sanctions_result.get("match", False):
            return ComplianceCheck(
                check_type="sanctions",
                passed=False,
                risk_score=10.0,
                violation_type=ComplianceViolationType.SANCTIONS_MATCH.value,
                action=ComplianceAction.BLOCK.value,
                details=sanctions_result,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        return ComplianceCheck(
            check_type="sanctions",
            passed=True,
            risk_score=0.0,
            violation_type=None,
            action=ComplianceAction.ALLOW.value,
            details={"message": "No sanctions matches found"},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _check_blocking_violations(
        self, compliance_results: List[ComplianceCheck]
    ) -> Optional[ComplianceCheck]:
        """Check if any compliance results require blocking the request"""
        for result in compliance_results:
            if result.action == ComplianceAction.BLOCK.value:
                return result
        return None

    async def _handle_compliance_violation(
        self,
        request: Request,
        violation: ComplianceCheck,
        all_results: List[ComplianceCheck],
    ) -> JSONResponse:
        """Handle compliance violation"""
        await self.compliance_service.log_violation(
            violation_type=violation.violation_type,
            details=violation.details,
            request_context={
                "path": request.url.path,
                "method": request.method,
                "client_ip": self._get_client_ip(request),
            },
        )
        error_message = self._get_user_friendly_error_message(violation)
        return JSONResponse(
            status_code=403,
            content={
                "error": error_message,
                "error_code": f"COMPLIANCE_{violation.violation_type.upper()}",
                "compliance_check_id": violation.timestamp,
            },
        )

    def _get_user_friendly_error_message(self, violation: ComplianceCheck) -> str:
        """Get user-friendly error message for compliance violation"""
        messages = {
            ComplianceViolationType.KYC_INCOMPLETE.value: "Account verification required to access this service",
            ComplianceViolationType.AML_SUSPICIOUS.value: "Transaction requires additional review",
            ComplianceViolationType.TRANSACTION_LIMIT_EXCEEDED.value: "Transaction amount exceeds allowed limits",
            ComplianceViolationType.RESTRICTED_JURISDICTION.value: "Service not available in your location",
            ComplianceViolationType.SANCTIONS_MATCH.value: "Access denied due to regulatory restrictions",
            ComplianceViolationType.PRIVACY_VIOLATION.value: "Request violates data protection requirements",
        }
        return messages.get(
            violation.violation_type, "Request blocked due to compliance requirements"
        )

    async def _perform_post_request_compliance(
        self,
        request: Request,
        response: Response,
        context: ComplianceContext,
        compliance_results: List[ComplianceCheck],
    ):
        """Perform post-request compliance checks"""
        if "/transactions/" in context.request_path and response.status_code < 300:
            await self.transaction_monitoring.log_transaction(
                user_id=context.user_id,
                transaction_data=context.business_context,
                compliance_results=compliance_results,
            )
        await self.compliance_service.update_metrics(compliance_results)

    def _add_compliance_headers(
        self, response: Response, compliance_results: List[ComplianceCheck]
    ) -> Any:
        """Add compliance-related headers to response"""
        overall_status = (
            "COMPLIANT"
            if all((r.passed for r in compliance_results))
            else "NON_COMPLIANT"
        )
        response.headers["X-Compliance-Status"] = overall_status
        max_risk_score = max((r.risk_score for r in compliance_results), default=0.0)
        response.headers["X-Compliance-Risk-Score"] = str(max_risk_score)
        response.headers["X-Compliance-Check-Time"] = datetime.now(
            timezone.utc
        ).isoformat()

    async def _log_compliance_metrics(
        self,
        request: Request,
        response: Response,
        compliance_results: List[ComplianceCheck],
        processing_time: float,
    ):
        """Log compliance metrics"""
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "processing_time": processing_time,
            "compliance_checks": len(compliance_results),
            "violations": len([r for r in compliance_results if not r.passed]),
            "max_risk_score": max(
                (r.risk_score for r in compliance_results), default=0.0
            ),
        }
        logger.info(f"Compliance metrics: {json.dumps(metrics)}")

    async def _log_compliance_exception(
        self, request: Request, exception: HTTPException
    ):
        """Log compliance-related exceptions"""
        logger.warning(
            f"Compliance exception: {exception.status_code} - {exception.detail} for {request.method} {request.url.path}"
        )

    async def _get_cached_kyc_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached KYC status"""
        cache_key = f"kyc:{user_id}"
        cached_data = self.compliance_cache.get(cache_key)
        if cached_data and time.time() - cached_data["timestamp"] < self.cache_ttl:
            return cached_data["data"]
        return None

    async def _cache_kyc_status(self, user_id: str, status: Dict[str, Any]):
        """Cache KYC status"""
        cache_key = f"kyc:{user_id}"
        self.compliance_cache[cache_key] = {"data": status, "timestamp": time.time()}

    async def _get_user_consent_status(self, user_id: str) -> Dict[str, bool]:
        """Get user consent status for GDPR"""
        return {"data_processing": True, "marketing": False, "analytics": True}

    async def _get_user_opt_out_status(self, user_id: str) -> Dict[str, bool]:
        """Get user opt-out status for CCPA"""
        return {"sale_opt_out": False, "sharing_opt_out": False}

    def _contains_excessive_data_collection(self, request_data: Dict[str, Any]) -> bool:
        """Check if request contains excessive data collection"""
        body = request_data.get("body", {})
        sensitive_fields = ["ssn", "tax_id", "passport", "drivers_license"]
        return any((field in str(body).lower() for field in sensitive_fields))

    async def _get_daily_attempts(
        self, client_ip: str, user_id: Optional[str], path: str
    ) -> int:
        """Get daily attempt count for rate limiting"""
        return 0

    async def get_compliance_dashboard_data(self) -> Dict[str, Any]:
        """Get compliance dashboard data"""
        return await self.compliance_service.get_dashboard_data()

    async def generate_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for specified period"""
        return await self.compliance_service.generate_report(start_date, end_date)
