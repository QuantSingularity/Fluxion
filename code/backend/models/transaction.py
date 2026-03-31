"""
Transaction models for Fluxion backend
"""

import enum
from decimal import Decimal
from typing import Any, Dict, Optional

from models.base import AuditMixin, BaseModel, ComplianceMixin, TimestampMixin
from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class TransactionType(enum.Enum):
    """Transaction types"""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    SWAP = "swap"
    STAKE = "stake"
    UNSTAKE = "unstake"
    LIQUIDITY_ADD = "liquidity_add"
    LIQUIDITY_REMOVE = "liquidity_remove"
    ASSET_CREATION = "asset_creation"
    ASSET_TRANSFER = "asset_transfer"
    SYNTHETIC_MINT = "synthetic_mint"
    SYNTHETIC_BURN = "synthetic_burn"
    GOVERNANCE_VOTE = "governance_vote"
    REWARD_CLAIM = "reward_claim"


class TransactionStatus(enum.Enum):
    """Transaction status"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNDER_REVIEW = "under_review"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class TransactionPriority(enum.Enum):
    """Transaction priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Transaction(BaseModel, TimestampMixin, AuditMixin, ComplianceMixin):
    """Transaction model for all blockchain and off-chain transactions"""

    __tablename__ = "transactions"

    # User and session
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id"),
        nullable=True,
        comment="Session ID",
    )

    # Transaction identification
    transaction_hash = Column(
        String(66), nullable=True, index=True, comment="Blockchain transaction hash"
    )
    internal_reference = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Internal reference ID",
    )
    external_reference = Column(
        String(100), nullable=True, comment="External system reference"
    )

    # Transaction details
    transaction_type = Column(
        Enum(TransactionType), nullable=False, comment="Transaction type"
    )
    status = Column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
        comment="Transaction status",
    )
    priority = Column(
        Enum(TransactionPriority),
        default=TransactionPriority.MEDIUM,
        nullable=False,
        comment="Transaction priority",
    )

    # Financial details
    amount = Column(DECIMAL(36, 18), nullable=False, comment="Transaction amount")
    currency = Column(String(10), nullable=False, comment="Currency/Token symbol")
    usd_value = Column(
        DECIMAL(20, 8), nullable=True, comment="USD value at time of transaction"
    )

    # Addresses and accounts
    from_address = Column(String(42), nullable=True, comment="Source address")
    to_address = Column(String(42), nullable=True, comment="Destination address")
    contract_address = Column(
        String(42), nullable=True, comment="Smart contract address"
    )

    # Blockchain details
    network = Column(String(50), nullable=True, comment="Blockchain network")
    chain_id = Column(Integer, nullable=True, comment="Chain ID")
    block_number = Column(Integer, nullable=True, comment="Block number")
    block_hash = Column(String(66), nullable=True, comment="Block hash")
    transaction_index = Column(
        Integer, nullable=True, comment="Transaction index in block"
    )

    # Gas and fees
    gas_limit = Column(Integer, nullable=True, comment="Gas limit")
    gas_used = Column(Integer, nullable=True, comment="Gas used")
    gas_price = Column(DECIMAL(36, 18), nullable=True, comment="Gas price in wei")
    transaction_fee = Column(DECIMAL(36, 18), nullable=True, comment="Transaction fee")

    # Timing
    submitted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Transaction submission time"
    )
    confirmed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Transaction confirmation time"
    )
    failed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Transaction failure time"
    )

    # Additional data
    input_data = Column(Text, nullable=True, comment="Transaction input data")
    logs = Column(JSON, nullable=True, comment="Transaction logs/events")
    extra_metadata = Column(JSON, nullable=True, comment="Additional metadata")

    # Error handling
    error_message = Column(Text, nullable=True, comment="Error message if failed")
    retry_count = Column(
        Integer, default=0, nullable=False, comment="Number of retry attempts"
    )
    max_retries = Column(
        Integer, default=3, nullable=False, comment="Maximum retry attempts"
    )

    # Compliance and risk
    is_suspicious = Column(
        Boolean, default=False, nullable=False, comment="Flagged as suspicious"
    )
    aml_check_status = Column(String(50), nullable=True, comment="AML check status")
    aml_risk_score = Column(DECIMAL(5, 2), nullable=True, comment="AML risk score")

    # Relationships
    user = relationship("User", back_populates="transactions")

    def is_pending(self) -> bool:
        """Check if transaction is pending"""
        return self.status == TransactionStatus.PENDING

    def is_confirmed(self) -> bool:
        """Check if transaction is confirmed"""
        return self.status == TransactionStatus.CONFIRMED

    def is_failed(self) -> bool:
        """Check if transaction is failed"""
        return self.status in [
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
            TransactionStatus.REJECTED,
        ]

    def can_retry(self) -> bool:
        """Check if transaction can be retried"""
        return self.is_failed() and self.retry_count < self.max_retries

    def get_confirmation_time(self) -> Optional[int]:
        """Get confirmation time in seconds"""
        if self.submitted_at and self.confirmed_at:
            return int((self.confirmed_at - self.submitted_at).total_seconds())
        return None

    def calculate_effective_gas_price(self) -> Optional[Decimal]:
        """Calculate effective gas price"""
        if self.gas_used and self.transaction_fee:
            return self.transaction_fee / self.gas_used
        return None

    def to_dict_safe(self) -> Dict[str, Any]:
        """Convert to dictionary with sensitive data removed"""
        data = self.to_dict()
        # Remove sensitive fields
        sensitive_fields = ["input_data", "logs", "metadata"]
        for field in sensitive_fields:
            if field in data:
                data[field] = "[REDACTED]"
        return data

    # Indexes for performance
    __table_args__ = (
        Index("idx_transactions_user_created", "user_id", "created_at"),
        Index("idx_transactions_hash", "transaction_hash"),
        Index("idx_transactions_status_type", "status", "transaction_type"),
        Index("idx_transactions_network_block", "network", "block_number"),
        Index("idx_transactions_suspicious", "is_suspicious"),
        Index("idx_transactions_amount_currency", "amount", "currency"),
    )


class TransactionBatch(BaseModel, TimestampMixin, AuditMixin):
    """Batch transaction processing"""

    __tablename__ = "transaction_batches"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )

    # Batch details
    batch_reference = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Batch reference ID",
    )
    batch_type = Column(String(50), nullable=False, comment="Batch type")
    total_transactions = Column(
        Integer, nullable=False, comment="Total transactions in batch"
    )
    completed_transactions = Column(
        Integer, default=0, nullable=False, comment="Completed transactions"
    )
    failed_transactions = Column(
        Integer, default=0, nullable=False, comment="Failed transactions"
    )

    # Status
    status = Column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
        comment="Batch status",
    )

    # Financial summary
    total_amount = Column(DECIMAL(36, 18), nullable=False, comment="Total batch amount")
    total_fees = Column(DECIMAL(36, 18), nullable=True, comment="Total batch fees")

    # Timing
    started_at = Column(
        DateTime(timezone=True), nullable=True, comment="Batch start time"
    )
    completed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Batch completion time"
    )

    # Error handling
    error_message = Column(Text, nullable=True, comment="Batch error message")

    # Relationships
    user = relationship("User")

    def get_completion_percentage(self) -> float:
        """Get batch completion percentage"""
        if self.total_transactions == 0:
            return 0.0
        return (self.completed_transactions / self.total_transactions) * 100

    def is_complete(self) -> bool:
        """Check if batch is complete"""
        return (
            self.completed_transactions + self.failed_transactions
            >= self.total_transactions
        )


class TransactionFee(BaseModel, TimestampMixin):
    """Transaction fee tracking"""

    __tablename__ = "transaction_fees"

    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
        comment="Transaction ID",
    )

    # Fee details
    fee_type = Column(
        String(50), nullable=False, comment="Fee type (gas, platform, etc.)"
    )
    amount = Column(DECIMAL(36, 18), nullable=False, comment="Fee amount")
    currency = Column(String(10), nullable=False, comment="Fee currency")
    usd_value = Column(DECIMAL(20, 8), nullable=True, comment="USD value of fee")

    # Fee calculation
    base_fee = Column(DECIMAL(36, 18), nullable=True, comment="Base fee")
    priority_fee = Column(DECIMAL(36, 18), nullable=True, comment="Priority fee")

    # Relationships
    transaction = relationship("Transaction")


class TransactionEvent(BaseModel, TimestampMixin):
    """Transaction event logging"""

    __tablename__ = "transaction_events"

    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
        comment="Transaction ID",
    )

    # Event details
    event_type = Column(String(50), nullable=False, comment="Event type")
    event_data = Column(JSON, nullable=True, comment="Event data")
    block_number = Column(Integer, nullable=True, comment="Block number")
    log_index = Column(Integer, nullable=True, comment="Log index")

    # Decoded event data
    decoded_data = Column(JSON, nullable=True, comment="Decoded event data")

    # Relationships
    transaction = relationship("Transaction")

    # Indexes
    __table_args__ = (
        Index("idx_transaction_events_tx_type", "transaction_id", "event_type"),
        Index("idx_transaction_events_block", "block_number"),
    )
