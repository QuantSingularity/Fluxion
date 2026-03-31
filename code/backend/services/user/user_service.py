"""
Comprehensive User Management Service for Fluxion Backend
Implements advanced user lifecycle management, profile management, preferences,
and user-related business logic for financial services platform.
"""

import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from services.auth.jwt_service import DeviceInfo, JWTService
from services.compliance.kyc_service import KYCService
from services.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class UserStatus(Enum):
    """User account status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    CLOSED = "closed"


class UserType(Enum):
    """Types of users"""

    INDIVIDUAL = "individual"
    BUSINESS = "business"
    INSTITUTIONAL = "institutional"
    ADMIN = "admin"


class NotificationPreference(Enum):
    """Notification preferences"""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


@dataclass
class UserProfile:
    """User profile information"""

    user_id: str
    email: str
    username: Optional[str]
    first_name: str
    last_name: str
    phone_number: Optional[str]
    date_of_birth: Optional[str]
    nationality: Optional[str]
    country_of_residence: str
    timezone: str
    language: str
    profile_picture_url: Optional[str]
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class UserPreferences:
    """User preferences and settings"""

    user_id: str
    notification_preferences: Dict[str, List[str]]
    privacy_settings: Dict[str, bool]
    trading_preferences: Dict[str, Any]
    display_preferences: Dict[str, Any]
    security_preferences: Dict[str, Any]
    updated_at: datetime


@dataclass
class UserSecurity:
    """User security information"""

    user_id: str
    password_hash: str
    password_salt: str
    mfa_enabled: bool
    mfa_secret: Optional[str]
    backup_codes: List[str]
    failed_login_attempts: int
    last_failed_login: Optional[datetime]
    account_locked_until: Optional[datetime]
    password_changed_at: datetime
    security_questions: List[Dict[str, str]]
    trusted_devices: List[str]
    login_history: List[Dict[str, Any]]


@dataclass
class User:
    """Complete user entity"""

    user_id: str
    email: str
    user_type: UserType
    status: UserStatus
    profile: UserProfile
    preferences: UserPreferences
    security: UserSecurity
    kyc_status: str
    risk_level: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    metadata: Dict[str, Any]


class UserService:
    """
    Comprehensive user management service providing:
    - User registration and authentication
    - Profile management and updates
    - Preference and settings management
    - Security and MFA management
    - User lifecycle management
    - Account verification and KYC integration
    - User analytics and reporting
    """

    def __init__(self) -> None:
        self.encryption_service = EncryptionService()
        self.jwt_service = JWTService()
        self.kyc_service = KYCService()
        self.password_min_length = 12
        self.password_complexity_required = True
        self.max_failed_login_attempts = 5
        self.account_lockout_duration = timedelta(hours=1)
        self.password_expiry_days = 90
        self.session_timeout_minutes = 30
        self.users: Dict[str, User] = {}
        self.email_to_user_id: Dict[str, str] = {}
        self.username_to_user_id: Dict[str, str] = {}
        self.default_preferences = {
            "notification_preferences": {
                "account_updates": ["email", "in_app"],
                "security_alerts": ["email", "sms", "in_app"],
                "transaction_notifications": ["email", "in_app"],
                "marketing": [],
                "system_maintenance": ["email"],
            },
            "privacy_settings": {
                "profile_visibility": False,
                "activity_tracking": True,
                "data_sharing": False,
                "marketing_communications": False,
            },
            "trading_preferences": {
                "default_currency": "USD",
                "risk_tolerance": "medium",
                "auto_rebalancing": False,
                "confirmation_required": True,
            },
            "display_preferences": {
                "theme": "light",
                "dashboard_layout": "default",
                "chart_type": "candlestick",
                "time_format": "24h",
            },
            "security_preferences": {
                "session_timeout": 30,
                "require_mfa_for_trades": True,
                "require_mfa_for_withdrawals": True,
                "login_notifications": True,
            },
        }

    async def register_user(
        self,
        email: str,
        password: str,
        user_type: UserType = UserType.INDIVIDUAL,
        profile_data: Optional[Dict[str, Any]] = None,
        device_info: Optional[DeviceInfo] = None,
    ) -> Dict[str, Any]:
        """Register a new user"""
        if email.lower() in self.email_to_user_id:
            raise ValueError("Email address already registered")
        password_validation = self._validate_password(password)
        if not password_validation["valid"]:
            raise ValueError(
                f"Password validation failed: {', '.join(password_validation['errors'])}"
            )
        user_id = self._generate_user_id()
        password_hash, password_salt = self.encryption_service.hash_password(password)
        profile = UserProfile(
            user_id=user_id,
            email=email.lower(),
            username=profile_data.get("username") if profile_data else None,
            first_name=profile_data.get("first_name", "") if profile_data else "",
            last_name=profile_data.get("last_name", "") if profile_data else "",
            phone_number=profile_data.get("phone_number") if profile_data else None,
            date_of_birth=profile_data.get("date_of_birth") if profile_data else None,
            nationality=profile_data.get("nationality") if profile_data else None,
            country_of_residence=(
                profile_data.get("country_of_residence", "US") if profile_data else "US"
            ),
            timezone=profile_data.get("timezone", "UTC") if profile_data else "UTC",
            language=profile_data.get("language", "en") if profile_data else "en",
            profile_picture_url=None,
            bio=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        preferences = UserPreferences(
            user_id=user_id,
            notification_preferences=self.default_preferences[
                "notification_preferences"
            ].copy(),
            privacy_settings=self.default_preferences["privacy_settings"].copy(),
            trading_preferences=self.default_preferences["trading_preferences"].copy(),
            display_preferences=self.default_preferences["display_preferences"].copy(),
            security_preferences=self.default_preferences[
                "security_preferences"
            ].copy(),
            updated_at=datetime.now(timezone.utc),
        )
        security = UserSecurity(
            user_id=user_id,
            password_hash=password_hash,
            password_salt=password_salt,
            mfa_enabled=False,
            mfa_secret=None,
            backup_codes=[],
            failed_login_attempts=0,
            last_failed_login=None,
            account_locked_until=None,
            password_changed_at=datetime.now(timezone.utc),
            security_questions=[],
            trusted_devices=[],
            login_history=[],
        )
        user = User(
            user_id=user_id,
            email=email.lower(),
            user_type=user_type,
            status=UserStatus.PENDING_VERIFICATION,
            profile=profile,
            preferences=preferences,
            security=security,
            kyc_status="not_initiated",
            risk_level="medium",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_login=None,
            metadata={},
        )
        self.users[user_id] = user
        self.email_to_user_id[email.lower()] = user_id
        if profile.username:
            self.username_to_user_id[profile.username.lower()] = user_id
        await self.kyc_service.initiate_kyc(user_id, user_type.value)
        verification_token = await self.jwt_service.create_special_token(
            token_type=self.jwt_service.TokenType.EMAIL_VERIFICATION,
            user_id=user_id,
            custom_claims={"email": email},
        )
        logger.info(f"User registered: {user_id} ({email})")
        return {
            "user_id": user_id,
            "email": email,
            "status": user.status.value,
            "verification_token": verification_token,
            "message": "User registered successfully. Please verify your email address.",
        }

    async def authenticate_user(
        self, email: str, password: str, device_info: Optional[DeviceInfo] = None
    ) -> Dict[str, Any]:
        """Authenticate user and create session"""
        email = email.lower()
        user_id = self.email_to_user_id.get(email)
        if not user_id:
            raise ValueError("Invalid email or password")
        user = self.users[user_id]
        if user.status == UserStatus.SUSPENDED:
            raise ValueError("Account is suspended")
        elif user.status == UserStatus.CLOSED:
            raise ValueError("Account is closed")
        if (
            user.security.account_locked_until
            and datetime.now(timezone.utc) < user.security.account_locked_until
        ):
            remaining_time = user.security.account_locked_until - datetime.now(
                timezone.utc
            )
            raise ValueError(
                f"Account is locked. Try again in {remaining_time.total_seconds():.0f} seconds"
            )
        password_valid = self.encryption_service.verify_password(
            password, user.security.password_hash, user.security.password_salt
        )
        if not password_valid:
            await self._record_failed_login(user)
            raise ValueError("Invalid email or password")
        user.security.failed_login_attempts = 0
        user.security.last_failed_login = None
        user.security.account_locked_until = None
        mfa_required = user.security.mfa_enabled
        if mfa_required:
            mfa_token = await self.jwt_service.create_special_token(
                token_type=self.jwt_service.TokenType.MFA,
                user_id=user_id,
                custom_claims={"step": "mfa_required"},
            )
            return {
                "mfa_required": True,
                "mfa_token": mfa_token,
                "message": "MFA verification required",
            }
        access_token, refresh_token = await self.jwt_service.create_token_pair(
            user_id=user_id,
            roles=self._get_user_roles(user),
            permissions=self._get_user_permissions(user),
            device_info=device_info,
            mfa_verified=False,
        )
        user.last_login = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        await self._record_login(user, device_info, success=True)
        logger.info(f"User authenticated: {user_id}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": await self._get_user_summary(user),
            "message": "Authentication successful",
        }

    async def verify_email(self, verification_token: str) -> Dict[str, Any]:
        """Verify user email address"""
        try:
            token_claims = self.encryption_service.decrypt_token(verification_token)
            user_id = token_claims.get("sub")
            email = token_claims.get("email")
            if not user_id or not email:
                raise ValueError("Invalid verification token")
            user = self.users.get(user_id)
            if not user:
                raise ValueError("User not found")
            if user.email != email:
                raise ValueError("Email mismatch")
            if user.status == UserStatus.PENDING_VERIFICATION:
                user.status = UserStatus.ACTIVE
                user.updated_at = datetime.now(timezone.utc)
                logger.info(f"Email verified for user: {user_id}")
                return {
                    "success": True,
                    "message": "Email verified successfully",
                    "user_id": user_id,
                }
            else:
                return {
                    "success": True,
                    "message": "Email already verified",
                    "user_id": user_id,
                }
        except Exception as e:
            logger.warning(f"Email verification failed: {str(e)}")
            raise ValueError("Invalid or expired verification token")

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        kyc_status = await self.kyc_service.get_kyc_status(user_id)
        profile_data = asdict(user.profile)
        profile_data.update(
            {
                "user_type": user.user_type.value,
                "status": user.status.value,
                "kyc_status": kyc_status["status"],
                "kyc_verified": kyc_status["verified"],
                "risk_level": user.risk_level,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "mfa_enabled": user.security.mfa_enabled,
            }
        )
        return profile_data

    async def update_user_profile(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user profile information"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        allowed_fields = {
            "first_name",
            "last_name",
            "phone_number",
            "country_of_residence",
            "timezone",
            "language",
            "bio",
        }
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields: {', '.join(invalid_fields)}")
        for field, value in updates.items():
            if hasattr(user.profile, field):
                setattr(user.profile, field, value)
        user.profile.updated_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        logger.info(f"Profile updated for user: {user_id}")
        return await self.get_user_profile(user_id)

    async def update_user_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user preferences"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        if "notification_preferences" in preferences:
            user.preferences.notification_preferences.update(
                preferences["notification_preferences"]
            )
        if "privacy_settings" in preferences:
            user.preferences.privacy_settings.update(preferences["privacy_settings"])
        if "trading_preferences" in preferences:
            user.preferences.trading_preferences.update(
                preferences["trading_preferences"]
            )
        if "display_preferences" in preferences:
            user.preferences.display_preferences.update(
                preferences["display_preferences"]
            )
        if "security_preferences" in preferences:
            user.preferences.security_preferences.update(
                preferences["security_preferences"]
            )
        user.preferences.updated_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        logger.info(f"Preferences updated for user: {user_id}")
        return asdict(user.preferences)

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        """Change user password"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        password_valid = self.encryption_service.verify_password(
            current_password, user.security.password_hash, user.security.password_salt
        )
        if not password_valid:
            raise ValueError("Current password is incorrect")
        password_validation = self._validate_password(new_password)
        if not password_validation["valid"]:
            raise ValueError(
                f"New password validation failed: {', '.join(password_validation['errors'])}"
            )
        new_password_hash, new_password_salt = self.encryption_service.hash_password(
            new_password
        )
        user.security.password_hash = new_password_hash
        user.security.password_salt = new_password_salt
        user.security.password_changed_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        await self.jwt_service.revoke_user_sessions(user_id, "Password changed")
        logger.info(f"Password changed for user: {user_id}")
        return {
            "success": True,
            "message": "Password changed successfully. Please log in again.",
        }

    async def enable_mfa(self, user_id: str) -> Dict[str, Any]:
        """Enable multi-factor authentication"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        if user.security.mfa_enabled:
            return {"success": False, "message": "MFA is already enabled"}
        mfa_secret = secrets.token_urlsafe(32)
        backup_codes = [secrets.token_urlsafe(8) for _ in range(10)]
        user.security.mfa_secret = mfa_secret
        user.security.backup_codes = backup_codes
        user.updated_at = datetime.now(timezone.utc)
        qr_code_data = f"otpauth://totp/{user.email}?secret={mfa_secret}&issuer=Fluxion"
        logger.info(f"MFA setup initiated for user: {user_id}")
        return {
            "success": True,
            "mfa_secret": mfa_secret,
            "qr_code_data": qr_code_data,
            "backup_codes": backup_codes,
            "message": "MFA setup initiated. Please verify with your authenticator app.",
        }

    async def verify_mfa_setup(self, user_id: str, mfa_code: str) -> Dict[str, Any]:
        """Verify MFA setup with authenticator code"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        if not user.security.mfa_secret:
            raise ValueError("MFA setup not initiated")
        if len(mfa_code) == 6 and mfa_code.isdigit():
            user.security.mfa_enabled = True
            user.updated_at = datetime.now(timezone.utc)
            logger.info(f"MFA enabled for user: {user_id}")
            return {"success": True, "message": "MFA enabled successfully"}
        else:
            raise ValueError("Invalid MFA code")

    async def disable_mfa(self, user_id: str, password: str) -> Dict[str, Any]:
        """Disable multi-factor authentication"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        password_valid = self.encryption_service.verify_password(
            password, user.security.password_hash, user.security.password_salt
        )
        if not password_valid:
            raise ValueError("Password is incorrect")
        user.security.mfa_enabled = False
        user.security.mfa_secret = None
        user.security.backup_codes = []
        user.updated_at = datetime.now(timezone.utc)
        logger.info(f"MFA disabled for user: {user_id}")
        return {"success": True, "message": "MFA disabled successfully"}

    async def suspend_user(
        self, user_id: str, reason: str, admin_user_id: str
    ) -> Dict[str, Any]:
        """Suspend user account"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        user.status = UserStatus.SUSPENDED
        user.updated_at = datetime.now(timezone.utc)
        user.metadata["suspension_reason"] = reason
        user.metadata["suspended_by"] = admin_user_id
        user.metadata["suspended_at"] = datetime.now(timezone.utc).isoformat()
        await self.jwt_service.revoke_user_sessions(
            user_id, f"Account suspended: {reason}"
        )
        logger.info(f"User suspended: {user_id} by {admin_user_id} - {reason}")
        return {"success": True, "message": f"User {user_id} suspended successfully"}

    async def reactivate_user(self, user_id: str, admin_user_id: str) -> Dict[str, Any]:
        """Reactivate suspended user account"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status != UserStatus.SUSPENDED:
            raise ValueError("User is not suspended")
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.now(timezone.utc)
        user.metadata["reactivated_by"] = admin_user_id
        user.metadata["reactivated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"User reactivated: {user_id} by {admin_user_id}")
        return {"success": True, "message": f"User {user_id} reactivated successfully"}

    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_urlsafe(16)}"

    def _validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        if len(password) < self.password_min_length:
            errors.append(
                f"Password must be at least {self.password_min_length} characters long"
            )
        if self.password_complexity_required:
            if not any((c.isupper() for c in password)):
                errors.append("Password must contain at least one uppercase letter")
            if not any((c.islower() for c in password)):
                errors.append("Password must contain at least one lowercase letter")
            if not any((c.isdigit() for c in password)):
                errors.append("Password must contain at least one digit")
            if not any((c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)):
                errors.append("Password must contain at least one special character")
        return {"valid": len(errors) == 0, "errors": errors}

    def _get_user_roles(self, user: User) -> List[str]:
        """Get user roles"""
        roles = ["user"]
        if user.user_type == UserType.ADMIN:
            roles.append("admin")
        elif user.user_type == UserType.INSTITUTIONAL:
            roles.append("institutional")
        elif user.user_type == UserType.BUSINESS:
            roles.append("business")
        return roles

    def _get_user_permissions(self, user: User) -> List[str]:
        """Get user permissions"""
        permissions = ["read:profile", "update:profile", "read:transactions"]
        if user.user_type == UserType.ADMIN:
            permissions.extend(["admin:users", "admin:system", "admin:reports"])
        if user.kyc_status == "verified":
            permissions.extend(["create:transactions", "withdraw:funds"])
        return permissions

    async def _record_failed_login(self, user: User):
        """Record failed login attempt"""
        user.security.failed_login_attempts += 1
        user.security.last_failed_login = datetime.now(timezone.utc)
        if user.security.failed_login_attempts >= self.max_failed_login_attempts:
            user.security.account_locked_until = (
                datetime.now(timezone.utc) + self.account_lockout_duration
            )
            logger.warning(
                f"Account locked due to failed login attempts: {user.user_id}"
            )
        user.updated_at = datetime.now(timezone.utc)

    async def _record_login(
        self, user: User, device_info: Optional[DeviceInfo], success: bool
    ):
        """Record login attempt in history"""
        login_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "ip_address": device_info.ip_address if device_info else "unknown",
            "user_agent": device_info.user_agent if device_info else "unknown",
            "device_id": device_info.device_id if device_info else None,
        }
        user.security.login_history.append(login_record)
        if len(user.security.login_history) > 50:
            user.security.login_history = user.security.login_history[-50:]

    async def _get_user_summary(self, user: User) -> Dict[str, Any]:
        """Get user summary for authentication response"""
        return {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.profile.first_name,
            "last_name": user.profile.last_name,
            "user_type": user.user_type.value,
            "status": user.status.value,
            "kyc_status": user.kyc_status,
            "mfa_enabled": user.security.mfa_enabled,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user service statistics"""
        status_counts = {}
        type_counts = {}
        for user in self.users.values():
            status_counts[user.status.value] = (
                status_counts.get(user.status.value, 0) + 1
            )
            type_counts[user.user_type.value] = (
                type_counts.get(user.user_type.value, 0) + 1
            )
        return {
            "total_users": len(self.users),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "mfa_enabled_count": sum(
                (1 for user in self.users.values() if user.security.mfa_enabled)
            ),
        }
