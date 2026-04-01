"""
JWT Service for Fluxion Backend
Implements advanced JWT token management with security features including
token rotation, blacklisting, device binding, and multi-factor authentication support.
"""

import hashlib
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import jwt
import redis.asyncio as redis
from config.settings import settings
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from services.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of JWT tokens"""

    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"
    MFA = "mfa"
    API_KEY = "api_key"


class TokenStatus(Enum):
    """Token validation status"""

    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    BLACKLISTED = "blacklisted"
    REVOKED = "revoked"


@dataclass
class TokenClaims:
    """JWT token claims structure"""

    user_id: str
    session_id: str
    token_type: TokenType
    roles: List[str]
    permissions: List[str]
    device_id: Optional[str]
    ip_address: Optional[str]
    mfa_verified: bool
    issued_at: datetime
    expires_at: datetime
    not_before: Optional[datetime]
    issuer: str
    audience: str
    jti: str
    custom_claims: Dict[str, Any]


@dataclass
class TokenValidationResult:
    """Token validation result"""

    status: TokenStatus
    claims: Optional[TokenClaims]
    error_message: Optional[str]
    remaining_ttl: Optional[int]
    requires_refresh: bool


@dataclass
class DeviceInfo:
    """Device information for token binding"""

    ip_address: str
    user_agent: str
    device_id: Optional[str] = None
    device_type: str = "unknown"
    fingerprint: str = ""
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    trusted: bool = False


class JWTService:
    """
    JWT service providing:
    - Secure token generation and validation
    - Token rotation and refresh
    - Token blacklisting and revocation
    - Device binding and tracking
    - Multi-factor authentication support
    - Session management
    - Audit logging
    """

    def __init__(self) -> None:
        self.encryption_service = EncryptionService()
        self.algorithm = settings.security.ALGORITHM
        self.secret_key = settings.security.SECRET_KEY
        self.issuer = settings.app.APP_NAME
        self.audience = settings.app.APP_NAME
        self.access_token_ttl = timedelta(
            minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self.refresh_token_ttl = timedelta(
            days=settings.security.REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.reset_token_ttl = timedelta(hours=1)
        self.verification_token_ttl = timedelta(hours=24)
        self.mfa_token_ttl = timedelta(minutes=5)
        self.max_refresh_count = 10
        self.device_binding_enabled = True
        self.ip_binding_enabled = False
        self.blacklisted_tokens: Set[str] = set()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.device_registry: Dict[str, DeviceInfo] = {}
        self.refresh_token_usage: Dict[str, int] = {}
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()

    def _initialize_redis(self) -> Any:
        """Initialize Redis connection for distributed token management"""
        try:
            if hasattr(settings, "redis") and settings.redis.REDIS_URL:
                self.redis_client = redis.from_url(
                    str(settings.redis.REDIS_URL),
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20,
                )
                logger.info("Redis client initialized for JWT service")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for JWT service: {e}")
            self.redis_client = None

    async def create_token_pair(
        self,
        user_id: str,
        roles: List[str],
        permissions: List[str],
        device_info: Optional[DeviceInfo] = None,
        mfa_verified: bool = False,
        custom_claims: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Create access and refresh token pair"""
        session_id = self._generate_session_id()
        current_time = datetime.now(timezone.utc)
        if device_info:
            await self._register_device(user_id, device_info)
        access_claims = TokenClaims(
            user_id=user_id,
            session_id=session_id,
            token_type=TokenType.ACCESS,
            roles=roles,
            permissions=permissions,
            device_id=device_info.device_id if device_info else None,
            ip_address=device_info.ip_address if device_info else None,
            mfa_verified=mfa_verified,
            issued_at=current_time,
            expires_at=current_time + self.access_token_ttl,
            not_before=current_time,
            issuer=self.issuer,
            audience=self.audience,
            jti=self._generate_jti(),
            custom_claims=custom_claims or {},
        )
        refresh_claims = TokenClaims(
            user_id=user_id,
            session_id=session_id,
            token_type=TokenType.REFRESH,
            roles=roles,
            permissions=permissions,
            device_id=device_info.device_id if device_info else None,
            ip_address=device_info.ip_address if device_info else None,
            mfa_verified=mfa_verified,
            issued_at=current_time,
            expires_at=current_time + self.refresh_token_ttl,
            not_before=current_time,
            issuer=self.issuer,
            audience=self.audience,
            jti=self._generate_jti(),
            custom_claims=custom_claims or {},
        )
        access_token = await self._generate_token(access_claims)
        refresh_token = await self._generate_token(refresh_claims)
        await self._store_session(
            session_id,
            {
                "user_id": user_id,
                "access_token_jti": access_claims.jti,
                "refresh_token_jti": refresh_claims.jti,
                "device_id": device_info.device_id if device_info else None,
                "created_at": current_time.isoformat(),
                "last_activity": current_time.isoformat(),
                "mfa_verified": mfa_verified,
            },
        )
        self.refresh_token_usage[refresh_claims.jti] = 0
        logger.info(f"Created token pair for user {user_id}, session {session_id}")
        return (access_token, refresh_token)

    async def validate_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None,
        device_info: Optional[DeviceInfo] = None,
    ) -> TokenValidationResult:
        """Validate JWT token with comprehensive security checks"""
        try:
            if await self._is_token_blacklisted(token):
                return TokenValidationResult(
                    status=TokenStatus.BLACKLISTED,
                    claims=None,
                    error_message="Token has been revoked",
                    remaining_ttl=None,
                    requires_refresh=False,
                )
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "require": ["exp", "iat", "jti", "sub"],
                },
            )
            claims = self._parse_token_claims(payload)
            if expected_type and claims.token_type != expected_type:
                return TokenValidationResult(
                    status=TokenStatus.INVALID,
                    claims=None,
                    error_message=f"Expected {expected_type.value} token, got {claims.token_type.value}",
                    remaining_ttl=None,
                    requires_refresh=False,
                )
            session_valid = await self._validate_session(claims.session_id, claims.jti)
            if not session_valid:
                return TokenValidationResult(
                    status=TokenStatus.REVOKED,
                    claims=None,
                    error_message="Session has been revoked",
                    remaining_ttl=None,
                    requires_refresh=False,
                )
            if self.device_binding_enabled and device_info:
                device_valid = await self._validate_device_binding(claims, device_info)
                if not device_valid:
                    return TokenValidationResult(
                        status=TokenStatus.INVALID,
                        claims=None,
                        error_message="Device binding validation failed",
                        remaining_ttl=None,
                        requires_refresh=False,
                    )
            if self.ip_binding_enabled and device_info and claims.ip_address:
                if claims.ip_address != device_info.ip_address:
                    return TokenValidationResult(
                        status=TokenStatus.INVALID,
                        claims=None,
                        error_message="IP address mismatch",
                        remaining_ttl=None,
                        requires_refresh=False,
                    )
            remaining_ttl = int(
                (claims.expires_at - datetime.now(timezone.utc)).total_seconds()
            )
            requires_refresh = remaining_ttl < 300
            await self._update_session_activity(claims.session_id)
            return TokenValidationResult(
                status=TokenStatus.VALID,
                claims=claims,
                error_message=None,
                remaining_ttl=remaining_ttl,
                requires_refresh=requires_refresh,
            )
        except ExpiredSignatureError:
            return TokenValidationResult(
                status=TokenStatus.EXPIRED,
                claims=None,
                error_message="Token has expired",
                remaining_ttl=0,
                requires_refresh=True,
            )
        except InvalidTokenError as e:
            return TokenValidationResult(
                status=TokenStatus.INVALID,
                claims=None,
                error_message=f"Invalid token: {str(e)}",
                remaining_ttl=None,
                requires_refresh=False,
            )
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}", exc_info=True)
            return TokenValidationResult(
                status=TokenStatus.INVALID,
                claims=None,
                error_message="Token validation failed",
                remaining_ttl=None,
                requires_refresh=False,
            )

    async def refresh_token(
        self, refresh_token: str, device_info: Optional[DeviceInfo] = None
    ) -> Tuple[str, str]:
        """Refresh access token using refresh token"""
        validation_result = await self.validate_token(
            refresh_token, TokenType.REFRESH, device_info
        )
        if validation_result.status != TokenStatus.VALID:
            raise ValueError(
                f"Invalid refresh token: {validation_result.error_message}"
            )
        claims = validation_result.claims
        usage_count = self.refresh_token_usage.get(claims.jti, 0)
        if usage_count >= self.max_refresh_count:
            await self._revoke_session(claims.session_id, "Excessive refresh attempts")
            raise ValueError("Refresh token usage limit exceeded")
        self.refresh_token_usage[claims.jti] = usage_count + 1
        new_access_token, new_refresh_token = await self.create_token_pair(
            user_id=claims.user_id,
            roles=claims.roles,
            permissions=claims.permissions,
            device_info=device_info,
            mfa_verified=claims.mfa_verified,
            custom_claims=claims.custom_claims,
        )
        await self._blacklist_token(refresh_token, "Token refreshed")
        logger.info(
            f"Refreshed token for user {claims.user_id}, session {claims.session_id}"
        )
        return (new_access_token, new_refresh_token)

    async def revoke_token(self, token: str, reason: str = "Manual revocation"):
        """Revoke a specific token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_signature": True},
            )
            claims = self._parse_token_claims(payload)
            await self._blacklist_token(token, reason)
            if claims.token_type == TokenType.REFRESH:
                await self._revoke_session(claims.session_id, reason)
            logger.info(
                f"Revoked token {claims.jti} for user {claims.user_id}: {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            await self._blacklist_token(token, f"Revocation error: {reason}")

    async def revoke_user_sessions(self, user_id: str, reason: str = "User logout"):
        """Revoke all sessions for a user"""
        sessions_to_revoke = []
        for session_id, session_data in self.active_sessions.items():
            if session_data.get("user_id") == user_id:
                sessions_to_revoke.append(session_id)
        for session_id in sessions_to_revoke:
            await self._revoke_session(session_id, reason)
        logger.info(
            f"Revoked {len(sessions_to_revoke)} sessions for user {user_id}: {reason}"
        )

    async def create_special_token(
        self,
        token_type: TokenType,
        user_id: str,
        custom_claims: Optional[Dict[str, Any]] = None,
        ttl: Optional[timedelta] = None,
    ) -> str:
        """Create special-purpose tokens (password reset, email verification, etc.)"""
        current_time = datetime.now(timezone.utc)
        if ttl is None:
            ttl_map = {
                TokenType.RESET_PASSWORD: self.reset_token_ttl,
                TokenType.EMAIL_VERIFICATION: self.verification_token_ttl,
                TokenType.MFA: self.mfa_token_ttl,
            }
            ttl = ttl_map.get(token_type, timedelta(hours=1))
        claims = TokenClaims(
            user_id=user_id,
            session_id=self._generate_session_id(),
            token_type=token_type,
            roles=[],
            permissions=[],
            device_id=None,
            ip_address=None,
            mfa_verified=False,
            issued_at=current_time,
            expires_at=current_time + ttl,
            not_before=current_time,
            issuer=self.issuer,
            audience=self.audience,
            jti=self._generate_jti(),
            custom_claims=custom_claims or {},
        )
        token = await self._generate_token(claims)
        logger.info(f"Created {token_type.value} token for user {user_id}")
        return token

    async def _generate_token(self, claims: TokenClaims) -> str:
        """Generate JWT token from claims"""
        payload = {
            "sub": claims.user_id,
            "sid": claims.session_id,
            "typ": claims.token_type.value,
            "roles": claims.roles,
            "permissions": claims.permissions,
            "device_id": claims.device_id,
            "ip": claims.ip_address,
            "mfa": claims.mfa_verified,
            "iat": int(claims.issued_at.timestamp()),
            "exp": int(claims.expires_at.timestamp()),
            "nbf": int(claims.not_before.timestamp()) if claims.not_before else None,
            "iss": claims.issuer,
            "aud": claims.audience,
            "jti": claims.jti,
        }
        payload.update(claims.custom_claims)
        payload = {k: v for k, v in payload.items() if v is not None}
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        if claims.token_type in [
            TokenType.RESET_PASSWORD,
            TokenType.EMAIL_VERIFICATION,
        ]:
            encrypted_token = self.encryption_service.encrypt_token(
                {"token": token},
                expires_in=int((claims.expires_at - claims.issued_at).total_seconds()),
            )
            return encrypted_token
        return token

    def _parse_token_claims(self, payload: Dict[str, Any]) -> TokenClaims:
        """Parse JWT payload into TokenClaims object"""
        return TokenClaims(
            user_id=payload["sub"],
            session_id=payload.get("sid", ""),
            token_type=TokenType(payload.get("typ", "access")),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            device_id=payload.get("device_id"),
            ip_address=payload.get("ip"),
            mfa_verified=payload.get("mfa", False),
            issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            not_before=(
                datetime.fromtimestamp(payload["nbf"], tz=timezone.utc)
                if payload.get("nbf")
                else None
            ),
            issuer=payload["iss"],
            audience=payload["aud"],
            jti=payload["jti"],
            custom_claims={
                k: v
                for k, v in payload.items()
                if k
                not in [
                    "sub",
                    "sid",
                    "typ",
                    "roles",
                    "permissions",
                    "device_id",
                    "ip",
                    "mfa",
                    "iat",
                    "exp",
                    "nbf",
                    "iss",
                    "aud",
                    "jti",
                ]
            },
        )

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"sess_{secrets.token_urlsafe(32)}"

    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return f"jwt_{secrets.token_urlsafe(16)}"

    async def _register_device(self, user_id: str, device_info: DeviceInfo):
        """Register device for user"""
        self.device_registry[device_info.device_id] = device_info
        logger.info(f"Registered device {device_info.device_id} for user {user_id}")

    async def _validate_device_binding(
        self, claims: TokenClaims, device_info: DeviceInfo
    ) -> bool:
        """Validate device binding"""
        if not claims.device_id:
            return True
        if claims.device_id != device_info.device_id:
            logger.warning(
                f"Device ID mismatch: expected {claims.device_id}, got {device_info.device_id}"
            )
            return False
        registered_device = self.device_registry.get(device_info.device_id)
        if not registered_device:
            logger.warning(f"Device {device_info.device_id} not registered")
            return False
        if not registered_device.trusted:
            logger.warning(f"Device {device_info.device_id} not trusted")
            return False
        return True

    async def _store_session(self, session_id: str, session_data: Dict[str, Any]):
        """Store session information"""
        self.active_sessions[session_id] = session_data
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"session:{session_id}",
                    int(self.refresh_token_ttl.total_seconds()),
                    json.dumps(session_data, default=str),
                )
            except Exception as e:
                logger.warning(f"Failed to store session in Redis: {e}")

    async def _validate_session(self, session_id: str, token_jti: str) -> bool:
        """Validate session exists and token belongs to it"""
        session_data = self.active_sessions.get(session_id)
        if not session_data:
            if self.redis_client:
                try:
                    session_json = await self.redis_client.get(f"session:{session_id}")
                    if session_json:
                        session_data = json.loads(session_json)
                        self.active_sessions[session_id] = session_data
                except Exception as e:
                    logger.warning(f"Failed to load session from Redis: {e}")
        if not session_data:
            return False
        return token_jti == session_data.get(
            "access_token_jti"
        ) or token_jti == session_data.get("refresh_token_jti")

    async def _update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now(
                timezone.utc
            ).isoformat()
            if self.redis_client:
                try:
                    await self.redis_client.setex(
                        f"session:{session_id}",
                        int(self.refresh_token_ttl.total_seconds()),
                        json.dumps(self.active_sessions[session_id], default=str),
                    )
                except Exception as e:
                    logger.warning(f"Failed to update session in Redis: {e}")

    async def _revoke_session(self, session_id: str, reason: str):
        """Revoke entire session"""
        session_data = self.active_sessions.get(session_id)
        if session_data:
            if "access_token_jti" in session_data:
                await self._blacklist_token_by_jti(
                    session_data["access_token_jti"], reason
                )
            if "refresh_token_jti" in session_data:
                await self._blacklist_token_by_jti(
                    session_data["refresh_token_jti"], reason
                )
            del self.active_sessions[session_id]
            if self.redis_client:
                try:
                    await self.redis_client.delete(f"session:{session_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete session from Redis: {e}")
        logger.info(f"Revoked session {session_id}: {reason}")

    async def _blacklist_token(self, token: str, reason: str):
        """Blacklist a token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.blacklisted_tokens.add(token_hash)
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"blacklist:{token_hash}",
                    int(self.refresh_token_ttl.total_seconds()),
                    reason,
                )
            except Exception as e:
                logger.warning(f"Failed to blacklist token in Redis: {e}")

    async def _blacklist_token_by_jti(self, jti: str, reason: str):
        """Blacklist token by JWT ID"""
        self.blacklisted_tokens.add(jti)
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"blacklist:jti:{jti}",
                    int(self.refresh_token_ttl.total_seconds()),
                    reason,
                )
            except Exception as e:
                logger.warning(f"Failed to blacklist token JTI in Redis: {e}")

    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in self.blacklisted_tokens:
            return True
        if self.redis_client:
            try:
                result = await self.redis_client.exists(f"blacklist:{token_hash}")
                if result:
                    return True
                try:
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.algorithm],
                        options={"verify_exp": False, "verify_signature": True},
                    )
                    jti = payload.get("jti")
                    if jti:
                        jti_result = await self.redis_client.exists(
                            f"blacklist:jti:{jti}"
                        )
                        return bool(jti_result)
                except Exception:
                    logger.debug("Skipping expired token cleanup")
            except Exception as e:
                logger.warning(f"Failed to check token blacklist in Redis: {e}")
        return False

    def get_token_statistics(self) -> Dict[str, Any]:
        """Get JWT service statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "blacklisted_tokens": len(self.blacklisted_tokens),
            "registered_devices": len(self.device_registry),
            "refresh_token_usage": len(self.refresh_token_usage),
            "redis_connected": self.redis_client is not None,
        }

    async def cleanup_expired_data(self):
        """Clean up expired sessions and blacklisted tokens"""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        for session_id, session_data in self.active_sessions.items():
            created_at = datetime.fromisoformat(
                session_data["created_at"].replace("Z", "+00:00")
            )
            if current_time - created_at > self.refresh_token_ttl:
                expired_sessions.append(session_id)
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token and return claims (for backward compatibility)"""
        validation_result = await self.validate_token(token)
        if validation_result.status != TokenStatus.VALID:
            raise ValueError(validation_result.error_message)
        return asdict(validation_result.claims)


# Backward compatibility alias
JWTService = JWTService
