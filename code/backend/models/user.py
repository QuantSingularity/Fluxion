"""
User models for Fluxion backend
"""

import enum
from datetime import datetime, timezone

from models.base import (
    AuditMixin,
    BaseModel,
    ComplianceMixin,
    EncryptedMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class UserStatus(enum.Enum):
    """User account status"""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DEACTIVATED = "deactivated"


class UserRole(enum.Enum):
    """User roles"""

    USER = "user"
    PREMIUM_USER = "premium_user"
    ADMIN = "admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    RISK_MANAGER = "risk_manager"
    SUPER_ADMIN = "super_admin"


class KYCStatus(enum.Enum):
    """KYC verification status"""

    NOT_STARTED = "not_started"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(
    BaseModel,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    EncryptedMixin,
    ComplianceMixin,
):
    """User model with enhanced security and compliance features"""

    __tablename__ = "users"
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address",
    )
    username = Column(
        String(100), unique=True, nullable=True, index=True, comment="Username"
    )
    hashed_password = Column(String(128), nullable=False, comment="Hashed password")
    first_name = Column(String(255), nullable=True, comment="First name (encrypted)")
    last_name = Column(String(255), nullable=True, comment="Last name (encrypted)")
    phone_number = Column(
        String(255), nullable=True, comment="Phone number (encrypted)"
    )
    date_of_birth = Column(
        String(255), nullable=True, comment="Date of birth (encrypted)"
    )
    address_line1 = Column(
        String(255), nullable=True, comment="Address line 1 (encrypted)"
    )
    address_line2 = Column(
        String(255), nullable=True, comment="Address line 2 (encrypted)"
    )
    city = Column(String(100), nullable=True, comment="City (encrypted)")
    state = Column(String(100), nullable=True, comment="State/Province (encrypted)")
    postal_code = Column(String(20), nullable=True, comment="Postal code (encrypted)")
    country = Column(String(100), nullable=True, comment="Country (encrypted)")
    status = Column(
        Enum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
        comment="Account status",
    )
    role = Column(
        Enum(UserRole), default=UserRole.USER, nullable=False, comment="User role"
    )
    is_email_verified = Column(
        Boolean, default=False, nullable=False, comment="Email verification status"
    )
    is_phone_verified = Column(
        Boolean, default=False, nullable=False, comment="Phone verification status"
    )
    mfa_enabled = Column(
        Boolean, default=False, nullable=False, comment="MFA enabled flag"
    )
    mfa_secret = Column(String(255), nullable=True, comment="MFA secret (encrypted)")
    backup_codes = Column(JSON, nullable=True, comment="MFA backup codes (encrypted)")
    failed_login_attempts = Column(
        Integer, default=0, nullable=False, comment="Failed login attempts count"
    )
    locked_until = Column(
        DateTime(timezone=True), nullable=True, comment="Account lock expiry"
    )
    last_login_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last login timestamp"
    )
    last_login_ip = Column(String(45), nullable=True, comment="Last login IP address")
    password_changed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Password change timestamp"
    )
    kyc_status = Column(
        Enum(KYCStatus),
        default=KYCStatus.NOT_STARTED,
        nullable=False,
        comment="KYC status",
    )
    kyc_completed_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC completion timestamp"
    )
    kyc_expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC expiry timestamp"
    )
    primary_wallet_address = Column(
        String(42), nullable=True, index=True, comment="Primary wallet address"
    )
    wallet_addresses = Column(
        JSON, nullable=True, comment="Additional wallet addresses"
    )
    timezone = Column(
        String(50), default="UTC", nullable=False, comment="User timezone"
    )
    language = Column(
        String(10), default="en", nullable=False, comment="Preferred language"
    )
    currency = Column(
        String(10), default="USD", nullable=False, comment="Preferred currency"
    )
    email_notifications = Column(
        Boolean, default=True, nullable=False, comment="Email notifications enabled"
    )
    sms_notifications = Column(
        Boolean, default=False, nullable=False, comment="SMS notifications enabled"
    )
    push_notifications = Column(
        Boolean, default=True, nullable=False, comment="Push notifications enabled"
    )
    terms_accepted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Terms acceptance timestamp"
    )
    privacy_accepted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Privacy policy acceptance timestamp",
    )
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    activities = relationship(
        "UserActivity", back_populates="user", cascade="all, delete-orphan"
    )
    portfolios = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    kyc_records = relationship(
        "KYCRecord", back_populates="user", cascade="all, delete-orphan"
    )
    risk_profiles = relationship(
        "RiskProfile", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", foreign_keys="AuditLog.user_id", cascade="all, delete-orphan"
    )

    @property
    def encrypted_fields(self):
        return [
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "mfa_secret",
            "backup_codes",
        ]

    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE and (not self.is_deleted)

    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.status == UserStatus.LOCKED:
            return True
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return True
        return False

    def can_login(self) -> bool:
        """Check if user can login"""
        return self.is_active() and (not self.is_locked()) and self.is_email_verified

    def add_wallet_address(self, address: str) -> None:
        """Add a wallet address"""
        if self.wallet_addresses is None:
            self.wallet_addresses = []
        if address not in self.wallet_addresses:
            self.wallet_addresses.append(address)

    def remove_wallet_address(self, address: str) -> None:
        """Remove a wallet address"""
        if self.wallet_addresses and address in self.wallet_addresses:
            self.wallet_addresses.remove(address)

    def get_full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, status={self.status.value})>"


class UserProfile(BaseModel, TimestampMixin, AuditMixin):
    """Extended user profile information"""

    __tablename__ = "user_profiles"
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        comment="User ID",
    )
    occupation = Column(String(100), nullable=True, comment="User occupation")
    employer = Column(String(100), nullable=True, comment="Employer name")
    annual_income = Column(
        String(255), nullable=True, comment="Annual income (encrypted)"
    )
    net_worth = Column(String(255), nullable=True, comment="Net worth (encrypted)")
    investment_experience = Column(
        String(50), nullable=True, comment="Investment experience level"
    )
    risk_tolerance = Column(String(50), nullable=True, comment="Risk tolerance level")
    investment_goals = Column(JSON, nullable=True, comment="Investment goals")
    referral_code = Column(
        String(20), unique=True, nullable=True, comment="User's referral code"
    )
    referred_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Referring user ID",
    )
    profile_completion_percentage = Column(
        Integer, default=0, nullable=False, comment="Profile completion percentage"
    )
    user = relationship("User", back_populates="profile")

    def calculate_completion_percentage(self) -> int:
        """Calculate profile completion percentage"""
        fields = [
            self.occupation,
            self.annual_income,
            self.investment_experience,
            self.risk_tolerance,
            self.user.first_name,
            self.user.last_name,
            self.user.phone_number,
            self.user.address_line1,
            self.user.city,
            self.user.country,
        ]
        completed = sum((1 for field in fields if field is not None))
        return int(completed / len(fields) * 100)


class UserSession(BaseModel, TimestampMixin):
    """User session tracking"""

    __tablename__ = "user_sessions"
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    session_token = Column(
        String(255), unique=True, nullable=False, index=True, comment="Session token"
    )
    refresh_token = Column(
        String(255), unique=True, nullable=True, index=True, comment="Refresh token"
    )
    ip_address = Column(String(45), nullable=True, comment="IP address")
    user_agent = Column(Text, nullable=True, comment="User agent string")
    device_info = Column(JSON, nullable=True, comment="Device information")
    location = Column(JSON, nullable=True, comment="Geolocation data")
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Session active status"
    )
    expires_at = Column(
        DateTime(timezone=True), nullable=False, comment="Session expiry"
    )
    last_activity_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last activity timestamp"
    )
    is_suspicious = Column(
        Boolean, default=False, nullable=False, comment="Suspicious activity flag"
    )
    user = relationship("User", back_populates="sessions")

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid"""
        return self.is_active and (not self.is_expired())


class UserActivity(BaseModel, TimestampMixin):
    """User activity logging"""

    __tablename__ = "user_activities"
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id"),
        nullable=True,
        comment="Session ID",
    )
    activity_type = Column(String(50), nullable=False, comment="Activity type")
    description = Column(Text, nullable=True, comment="Activity description")
    endpoint = Column(String(255), nullable=True, comment="API endpoint")
    method = Column(String(10), nullable=True, comment="HTTP method")
    request_data = Column(JSON, nullable=True, comment="Request data (sanitized)")
    response_status = Column(Integer, nullable=True, comment="Response status code")
    ip_address = Column(String(45), nullable=True, comment="IP address")
    user_agent = Column(Text, nullable=True, comment="User agent")
    risk_score = Column(Float, nullable=True, comment="Activity risk score")
    is_flagged = Column(
        Boolean, default=False, nullable=False, comment="Flagged for review"
    )
    user = relationship("User", back_populates="activities")
    __table_args__ = (
        Index("idx_user_activities_user_created", "user_id", "created_at"),
        Index("idx_user_activities_type_created", "activity_type", "created_at"),
        Index("idx_user_activities_flagged", "is_flagged"),
    )
