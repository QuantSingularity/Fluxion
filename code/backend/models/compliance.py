"""
Compliance models for Fluxion backend
"""

import enum
from datetime import datetime
from typing import Optional

from models.base import AuditMixin, BaseModel, EncryptedMixin, TimestampMixin
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


class KYCStatus(enum.Enum):
    """KYC verification status"""

    NOT_STARTED = "not_started"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REQUIRES_UPDATE = "requires_update"


class KYCTier(enum.Enum):
    """KYC verification tiers"""

    TIER_0 = "tier_0"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class DocumentType(enum.Enum):
    """KYC document types"""

    GOVERNMENT_ID = "government_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    PROOF_OF_ADDRESS = "proof_of_address"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    TAX_RETURN = "tax_return"
    BUSINESS_REGISTRATION = "business_registration"
    OTHER = "other"


class AMLRiskLevel(enum.Enum):
    """AML risk levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    PROHIBITED = "prohibited"


class ComplianceAlertType(enum.Enum):
    """Compliance alert types"""

    SUSPICIOUS_TRANSACTION = "suspicious_transaction"
    HIGH_RISK_CUSTOMER = "high_risk_customer"
    SANCTIONS_MATCH = "sanctions_match"
    UNUSUAL_ACTIVITY = "unusual_activity"
    THRESHOLD_BREACH = "threshold_breach"
    KYC_EXPIRY = "kyc_expiry"
    REGULATORY_CHANGE = "regulatory_change"


class ComplianceAlertStatus(enum.Enum):
    """Compliance alert status"""

    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class AuditLogLevel(enum.Enum):
    """Audit log levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class KYCRecord(BaseModel, TimestampMixin, AuditMixin, EncryptedMixin):
    """KYC record model"""

    __tablename__ = "kyc_records"
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        comment="User ID",
    )
    status = Column(
        Enum(KYCStatus),
        default=KYCStatus.NOT_STARTED,
        nullable=False,
        comment="KYC status",
    )
    tier = Column(
        Enum(KYCTier), default=KYCTier.TIER_0, nullable=False, comment="KYC tier"
    )
    provider = Column(String(50), nullable=True, comment="KYC provider")
    provider_reference = Column(
        String(100), nullable=True, comment="Provider reference ID"
    )
    first_name = Column(String(255), nullable=True, comment="First name (encrypted)")
    last_name = Column(String(255), nullable=True, comment="Last name (encrypted)")
    middle_name = Column(String(255), nullable=True, comment="Middle name (encrypted)")
    date_of_birth = Column(
        String(255), nullable=True, comment="Date of birth (encrypted)"
    )
    nationality = Column(String(255), nullable=True, comment="Nationality (encrypted)")
    document_type = Column(String(50), nullable=True, comment="Document type")
    document_number = Column(
        String(255), nullable=True, comment="Document number (encrypted)"
    )
    document_issuer = Column(
        String(255), nullable=True, comment="Document issuer (encrypted)"
    )
    document_expiry = Column(
        String(255), nullable=True, comment="Document expiry (encrypted)"
    )
    address_line1 = Column(
        String(255), nullable=True, comment="Address line 1 (encrypted)"
    )
    address_line2 = Column(
        String(255), nullable=True, comment="Address line 2 (encrypted)"
    )
    city = Column(String(255), nullable=True, comment="City (encrypted)")
    state = Column(String(255), nullable=True, comment="State (encrypted)")
    postal_code = Column(String(255), nullable=True, comment="Postal code (encrypted)")
    country = Column(String(255), nullable=True, comment="Country (encrypted)")
    verification_method = Column(
        String(50), nullable=True, comment="Verification method"
    )
    verification_score = Column(Float, nullable=True, comment="Verification score")
    liveness_check = Column(
        Boolean, default=False, nullable=False, comment="Liveness check passed"
    )
    document_verification = Column(
        Boolean, default=False, nullable=False, comment="Document verification passed"
    )
    address_verification = Column(
        Boolean, default=False, nullable=False, comment="Address verification passed"
    )
    submitted_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC submission timestamp"
    )
    reviewed_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC review timestamp"
    )
    approved_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC approval timestamp"
    )
    expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="KYC expiry timestamp"
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Reviewer user ID",
    )
    review_notes = Column(Text, nullable=True, comment="Review notes")
    rejection_reason = Column(Text, nullable=True, comment="Rejection reason")
    risk_score = Column(Float, nullable=True, comment="Risk score")
    risk_factors = Column(JSON, nullable=True, comment="Risk factors")
    document_urls = Column(JSON, nullable=True, comment="Document URLs (encrypted)")
    user = relationship("User", foreign_keys=[user_id], back_populates="kyc_records")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def is_expired(self) -> bool:
        """Check if KYC is expired"""
        return self.expires_at and self.expires_at < datetime.utcnow()

    def is_valid(self) -> bool:
        """Check if KYC is valid"""
        return self.status == KYCStatus.APPROVED and (not self.is_expired())

    def days_until_expiry(self) -> Optional[int]:
        """Get days until KYC expiry"""
        if self.expires_at:
            delta = self.expires_at - datetime.utcnow()
            return max(0, delta.days)
        return None


class AMLCheck(BaseModel, TimestampMixin, AuditMixin):
    """AML check model"""

    __tablename__ = "aml_checks"
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
        comment="Transaction ID",
    )
    check_type = Column(String(50), nullable=False, comment="AML check type")
    provider = Column(String(50), nullable=False, comment="AML provider")
    provider_reference = Column(
        String(100), nullable=True, comment="Provider reference"
    )
    subject_type = Column(
        String(20), nullable=False, comment="Subject type (user, transaction, address)"
    )
    subject_id = Column(String(100), nullable=False, comment="Subject identifier")
    risk_level = Column(Enum(AMLRiskLevel), nullable=False, comment="Risk level")
    risk_score = Column(Float, nullable=True, comment="Risk score")
    confidence_score = Column(Float, nullable=True, comment="Confidence score")
    sanctions_match = Column(
        Boolean, default=False, nullable=False, comment="Sanctions list match"
    )
    pep_match = Column(Boolean, default=False, nullable=False, comment="PEP list match")
    adverse_media = Column(
        Boolean, default=False, nullable=False, comment="Adverse media found"
    )
    matches = Column(JSON, nullable=True, comment="Detailed match results")
    alerts = Column(JSON, nullable=True, comment="Alert details")
    status = Column(
        String(20), default="completed", nullable=False, comment="Check status"
    )
    user = relationship("User")
    transaction = relationship("Transaction")

    def is_high_risk(self) -> bool:
        """Check if result indicates high risk"""
        return self.risk_level in [
            AMLRiskLevel.HIGH,
            AMLRiskLevel.VERY_HIGH,
            AMLRiskLevel.PROHIBITED,
        ]

    def has_matches(self) -> bool:
        """Check if there are any matches"""
        return self.sanctions_match or self.pep_match or self.adverse_media

    __table_args__ = (
        Index("idx_aml_checks_user_created", "user_id", "created_at"),
        Index("idx_aml_checks_risk_level", "risk_level"),
        Index("idx_aml_checks_matches", "sanctions_match", "pep_match"),
    )


class ComplianceAlert(BaseModel, TimestampMixin, AuditMixin):
    """Compliance alert model"""

    __tablename__ = "compliance_alerts"
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="User ID"
    )
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
        comment="Transaction ID",
    )
    alert_type = Column(Enum(ComplianceAlertType), nullable=False, comment="Alert type")
    severity = Column(String(20), nullable=False, comment="Alert severity")
    status = Column(
        Enum(ComplianceAlertStatus),
        default=ComplianceAlertStatus.OPEN,
        nullable=False,
        comment="Alert status",
    )
    title = Column(String(200), nullable=False, comment="Alert title")
    description = Column(Text, nullable=False, comment="Alert description")
    details = Column(JSON, nullable=True, comment="Alert details")
    risk_score = Column(Float, nullable=True, comment="Risk score")
    risk_factors = Column(JSON, nullable=True, comment="Risk factors")
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Assigned investigator",
    )
    investigation_notes = Column(Text, nullable=True, comment="Investigation notes")
    resolution_notes = Column(Text, nullable=True, comment="Resolution notes")
    triggered_at = Column(
        DateTime(timezone=True), nullable=False, comment="Alert trigger timestamp"
    )
    assigned_at = Column(
        DateTime(timezone=True), nullable=True, comment="Assignment timestamp"
    )
    resolved_at = Column(
        DateTime(timezone=True), nullable=True, comment="Resolution timestamp"
    )
    escalated = Column(Boolean, default=False, nullable=False, comment="Escalated flag")
    escalated_at = Column(
        DateTime(timezone=True), nullable=True, comment="Escalation timestamp"
    )
    escalated_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Escalated to user",
    )
    user = relationship("User", foreign_keys=[user_id])
    transaction = relationship("Transaction")
    assignee = relationship("User", foreign_keys=[assigned_to])
    escalated_user = relationship("User", foreign_keys=[escalated_to])

    def is_open(self) -> bool:
        """Check if alert is open"""
        return self.status in [
            ComplianceAlertStatus.OPEN,
            ComplianceAlertStatus.UNDER_INVESTIGATION,
        ]

    def is_overdue(self, hours: int = 24) -> bool:
        """Check if alert is overdue"""
        if self.is_open():
            delta = datetime.utcnow() - self.triggered_at
            return delta.total_seconds() > hours * 3600
        return False

    __table_args__ = (
        Index("idx_compliance_alerts_status_type", "status", "alert_type"),
        Index("idx_compliance_alerts_user_triggered", "user_id", "triggered_at"),
        Index("idx_compliance_alerts_assigned", "assigned_to"),
        Index("idx_compliance_alerts_severity", "severity"),
    )


class AuditLog(BaseModel, TimestampMixin):
    """Audit log model"""

    __tablename__ = "audit_logs"
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="User ID"
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id"),
        nullable=True,
        comment="Session ID",
    )
    event_type = Column(String(50), nullable=False, comment="Event type")
    event_category = Column(String(50), nullable=False, comment="Event category")
    level = Column(
        Enum(AuditLogLevel),
        default=AuditLogLevel.INFO,
        nullable=False,
        comment="Log level",
    )
    title = Column(String(200), nullable=False, comment="Event title")
    description = Column(Text, nullable=True, comment="Event description")
    resource_type = Column(String(50), nullable=True, comment="Resource type")
    resource_id = Column(String(100), nullable=True, comment="Resource ID")
    action = Column(String(50), nullable=True, comment="Action performed")
    endpoint = Column(String(255), nullable=True, comment="API endpoint")
    method = Column(String(10), nullable=True, comment="HTTP method")
    ip_address = Column(String(45), nullable=True, comment="IP address")
    user_agent = Column(Text, nullable=True, comment="User agent")
    old_values = Column(JSON, nullable=True, comment="Old values")
    new_values = Column(JSON, nullable=True, comment="New values")
    extra_metadata = Column(JSON, nullable=True, comment="Additional metadata")
    retention_period = Column(
        Integer, nullable=True, comment="Retention period in days"
    )
    is_sensitive = Column(
        Boolean, default=False, nullable=False, comment="Contains sensitive data"
    )
    user = relationship("User", foreign_keys=[user_id], back_populates="audit_logs")

    def is_expired(self) -> bool:
        """Check if audit log is expired"""
        if self.retention_period:
            expiry_date = self.created_at + timedelta(days=self.retention_period)
            return datetime.utcnow() > expiry_date
        return False

    __table_args__ = (
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_category_level", "event_category", "level"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_sensitive", "is_sensitive"),
    )


class RegulatoryReport(BaseModel, TimestampMixin, AuditMixin):
    """Regulatory report model"""

    __tablename__ = "regulatory_reports"
    report_type = Column(String(50), nullable=False, comment="Report type")
    report_period = Column(String(20), nullable=False, comment="Report period")
    jurisdiction = Column(String(50), nullable=False, comment="Jurisdiction")
    title = Column(String(200), nullable=False, comment="Report title")
    description = Column(Text, nullable=True, comment="Report description")
    data = Column(JSON, nullable=False, comment="Report data")
    status = Column(
        String(20), default="draft", nullable=False, comment="Report status"
    )
    generated_at = Column(
        DateTime(timezone=True), nullable=True, comment="Generation timestamp"
    )
    submitted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Submission timestamp"
    )
    file_path = Column(String(500), nullable=True, comment="Report file path")
    file_hash = Column(String(64), nullable=True, comment="Report file hash")
    regulatory_reference = Column(
        String(100), nullable=True, comment="Regulatory reference"
    )
    __table_args__ = (
        Index("idx_regulatory_reports_type_period", "report_type", "report_period"),
        Index("idx_regulatory_reports_jurisdiction", "jurisdiction"),
        Index("idx_regulatory_reports_status", "status"),
    )
