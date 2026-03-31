"""
Comprehensive Security Middleware for Fluxion Backend
Implements enterprise-grade security controls including CSRF protection,
XSS prevention, security headers, and threat detection.
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from typing import Any, Optional, Set

from config.settings import settings
from fastapi import HTTPException, Request, Response
from services.auth.jwt_service import JWTService
from services.security.encryption_service import EncryptionService
from services.security.threat_detection_service import ThreatDetectionService
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware implementing multiple security controls:
    - Security headers (HSTS, CSP, X-Frame-Options, etc.)
    - CSRF protection
    - XSS prevention
    - Rate limiting integration
    - IP whitelisting/blacklisting
    - Threat detection
    - Request/response sanitization
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.jwt_service = JWTService()
        self.threat_detection = ThreatDetectionService()
        self.encryption_service = EncryptionService()
        self.csrf_token_expiry = timedelta(hours=1)
        self.max_request_size = 10 * 1024 * 1024
        self.blocked_ips: Set[str] = set()
        self.allowed_ips: Set[str] = set()
        self.suspicious_patterns = [
            "<script[^>]*>.*?</script>",
            "javascript:",
            "vbscript:",
            "onload\\s*=",
            "onerror\\s*=",
            "eval\\s*\\(",
            "document\\.cookie",
            "union\\s+select",
            "drop\\s+table",
            "insert\\s+into",
            "delete\\s+from",
        ]
        self._load_ip_configurations()
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": self._build_csp_header(),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
        }

    def _load_ip_configurations(self) -> None:
        """Load IP whitelist and blacklist from configuration"""
        # Load from environment variables or configuration file
        # Example: Load from settings.security.BLOCKED_IPS and settings.security.ALLOWED_IPS
        # For now, initialize as empty sets - can be populated from config

    def _build_csp_header(self) -> str:
        """Build Content Security Policy header"""
        if settings.app.ENVIRONMENT == "development":
            return "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:; connect-src 'self' ws: wss:"
        else:
            return "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self'; object-src 'none'; media-src 'self'; frame-src 'none';"

    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        start_time = time.time()
        try:
            await self._pre_request_security_checks(request)
            response = await call_next(request)
            await self._post_request_security_enhancements(request, response)
            self._add_security_headers(response)
            self._log_security_metrics(request, response, time.time() - start_time)
            return response
        except HTTPException as e:
            logger.warning(f"Security middleware blocked request: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "error_code": "SECURITY_VIOLATION"},
            )
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal security error",
                    "error_code": "SECURITY_ERROR",
                },
            )

    async def _pre_request_security_checks(self, request: Request):
        """Perform pre-request security validations"""
        if hasattr(request, "content_length") and request.content_length:
            if request.content_length > self.max_request_size:
                raise HTTPException(status_code=413, detail="Request too large")
        client_ip = self._get_client_ip(request)
        if client_ip:
            await self._check_ip_access(client_ip)
        await self._check_suspicious_patterns(request)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            await self._validate_csrf_token(request)
        await self._detect_threats(request)

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client:
            return request.client.host
        return None

    async def _check_ip_access(self, client_ip: str):
        """Check IP-based access control"""
        try:
            ip_addr = ip_address(client_ip)
            if client_ip in self.blocked_ips:
                logger.warning(f"Blocked IP attempted access: {client_ip}")
                raise HTTPException(status_code=403, detail="Access denied")
            if self.allowed_ips and client_ip not in self.allowed_ips:
                allowed = False
                for allowed_ip in self.allowed_ips:
                    try:
                        if ip_addr in ip_network(allowed_ip, strict=False):
                            allowed = True
                            break
                    except ValueError:
                        if client_ip == allowed_ip:
                            allowed = True
                            break
                if not allowed:
                    logger.warning(f"Non-whitelisted IP attempted access: {client_ip}")
                    raise HTTPException(status_code=403, detail="Access denied")
        except ValueError:
            logger.error(f"Invalid IP address format: {client_ip}")
            raise HTTPException(status_code=400, detail="Invalid request")

    async def _check_suspicious_patterns(self, request: Request):
        """Check for suspicious patterns in request"""
        import re

        url_path = str(request.url.path)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url_path, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in URL: {pattern}")
                await self.threat_detection.log_threat(
                    request, "suspicious_pattern", f"Pattern: {pattern}"
                )
                raise HTTPException(status_code=400, detail="Invalid request")
        for header_name, header_value in request.headers.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, header_value, re.IGNORECASE):
                    logger.warning(
                        f"Suspicious pattern detected in header {header_name}: {pattern}"
                    )
                    await self.threat_detection.log_threat(
                        request,
                        "suspicious_header",
                        f"Header: {header_name}, Pattern: {pattern}",
                    )
                    raise HTTPException(status_code=400, detail="Invalid request")

    async def _validate_csrf_token(self, request: Request):
        """Validate CSRF token for state-changing operations"""
        if request.url.path.startswith("/api/"):
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header.split(" ")[1]
                    await self.jwt_service.verify_token(token)
                    return
                except Exception:
                    pass
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            if request.headers.get("content-type", "").startswith(
                "application/x-www-form-urlencoded"
            ):
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
        if not csrf_token:
            logger.warning("Missing CSRF token for state-changing operation")
            raise HTTPException(status_code=403, detail="CSRF token required")
        if not await self._verify_csrf_token(csrf_token, request):
            logger.warning("Invalid CSRF token")
            raise HTTPException(status_code=403, detail="Invalid CSRF token")

    async def _verify_csrf_token(self, token: str, request: Request) -> bool:
        """Verify CSRF token validity"""
        try:
            expected_token = self._generate_csrf_token(request)
            return secrets.compare_digest(token, expected_token)
        except Exception as e:
            logger.error(f"CSRF token verification error: {str(e)}")
            return False

    def _generate_csrf_token(self, request: Request) -> str:
        """Generate CSRF token for the session"""
        session_id = request.headers.get("X-Session-ID", "anonymous")
        timestamp = str(int(time.time() // 3600))
        token_data = f"{session_id}:{timestamp}:{settings.security.SECRET_KEY}"
        return hashlib.sha256(token_data.encode()).hexdigest()

    async def _detect_threats(self, request: Request):
        """Detect potential security threats"""
        user_agent = request.headers.get("User-Agent", "")
        suspicious_user_agents = [
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "zap",
            "burp",
            "acunetix",
            "nessus",
            "openvas",
            "w3af",
        ]
        for suspicious_ua in suspicious_user_agents:
            if suspicious_ua.lower() in user_agent.lower():
                logger.warning(f"Suspicious user agent detected: {user_agent}")
                await self.threat_detection.log_threat(
                    request, "suspicious_user_agent", f"User-Agent: {user_agent}"
                )
                raise HTTPException(status_code=403, detail="Access denied")
        client_ip = self._get_client_ip(request)
        if client_ip:
            await self.threat_detection.check_request_frequency(client_ip, request)

    async def _post_request_security_enhancements(
        self, request: Request, response: Response
    ):
        """Apply post-request security enhancements"""
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            request_id = secrets.token_hex(16)
            request.state.request_id = request_id
        response.headers["X-Request-ID"] = request_id
        sensitive_headers = ["Server", "X-Powered-By", "X-AspNet-Version"]
        for header in sensitive_headers:
            if header in response.headers:
                del response.headers[header]

    def _add_security_headers(self, response: Response) -> Any:
        """Add security headers to response"""
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        if hasattr(response, "url") and "/api/" in str(response.url):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _log_security_metrics(
        self, request: Request, response: Response, duration: float
    ) -> Any:
        """Log security-related metrics"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        security_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "user_agent": user_agent,
            "duration": duration,
            "request_id": getattr(request.state, "request_id", None),
        }
        logger.info(f"Security metrics: {security_log}")

    async def block_ip(self, ip_address: str, reason: str = "Security violation"):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"IP {ip_address} blocked: {reason}")
        await self.threat_detection.log_ip_block(ip_address, reason)

    async def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        logger.info(f"IP {ip_address} unblocked")

    def get_csrf_token(self, request: Request) -> str:
        """Generate CSRF token for client"""
        return self._generate_csrf_token(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Lightweight security headers middleware for cases where full SecurityMiddleware is not needed
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        return response
