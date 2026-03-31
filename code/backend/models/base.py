"""
Base model classes for Fluxion backend
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from config.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func


class BaseModel(Base):
    """Base model class with common fields"""

    __abstract__ = True
    __allow_unmapped__ = True
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key UUID",
    )

    @declared_attr
    def __tablename__(cls: Any) -> Any:
        """Generate table name from class name"""
        return cls.__name__.lower() + "s"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class TimestampMixin:
    """Mixin for timestamp fields"""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    deleted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Soft delete timestamp"
    )
    is_deleted = Column(
        Boolean, default=False, nullable=False, index=True, comment="Soft delete flag"
    )

    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """Mixin for audit trail fields"""

    created_by = Column(
        UUID(as_uuid=True), nullable=True, comment="User who created the record"
    )
    updated_by = Column(
        UUID(as_uuid=True), nullable=True, comment="User who last updated the record"
    )
    version = Column(
        String(50), nullable=True, comment="Record version for optimistic locking"
    )


class EncryptedMixin:
    """Mixin for encrypted fields"""

    @declared_attr
    def encrypted_fields(cls):
        """Define which fields should be encrypted"""
        return []

    def encrypt_sensitive_data(self, encryption_service: Any) -> None:
        """Encrypt sensitive fields"""
        for field_name in self.encrypted_fields:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if value is not None:
                    encrypted_value = encryption_service.encrypt(str(value))
                    setattr(self, field_name, encrypted_value)

    def decrypt_sensitive_data(self, encryption_service: Any) -> None:
        """Decrypt sensitive fields"""
        for field_name in self.encrypted_fields:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if value is not None:
                    try:
                        decrypted_value = encryption_service.decrypt(value)
                        setattr(self, field_name, decrypted_value)
                    except Exception:
                        pass


class MetadataMixin:
    """Mixin for metadata fields"""

    extra_metadata = Column(
        JSON, nullable=True, comment="Additional metadata in JSON format"
    )
    tags = Column(JSON, nullable=True, comment="Tags for categorization")
    notes = Column(Text, nullable=True, comment="Additional notes")

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata key-value pair"""
        if self.extra_metadata is None:
            self.extra_metadata = {}
        self.extra_metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key"""
        if self.extra_metadata is None:
            return default
        return self.extra_metadata.get(key, default)

    def add_tag(self, tag: str) -> None:
        """Add a tag"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if record has a specific tag"""
        return self.tags is not None and tag in self.tags


class ComplianceMixin:
    """Mixin for compliance-related fields"""

    compliance_status = Column(String(50), nullable=True, comment="Compliance status")
    compliance_checked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last compliance check timestamp",
    )
    compliance_notes = Column(Text, nullable=True, comment="Compliance notes")
    risk_score = Column(String(20), nullable=True, comment="Risk score (encrypted)")

    def update_compliance_status(
        self, status: str, notes: Optional[str] = None
    ) -> None:
        """Update compliance status"""
        self.compliance_status = status
        self.compliance_checked_at = datetime.utcnow()
        if notes:
            self.compliance_notes = notes
