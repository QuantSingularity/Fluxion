"""
Comprehensive Transaction Processing Service for Fluxion Backend
Implements advanced transaction management, processing, validation, and monitoring
for financial services with enterprise-grade reliability and compliance.
"""

import asyncio
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from services.compliance.kyc_service import KYCService
from services.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Types of transactions"""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    FEE = "fee"
    INTEREST = "interest"
    DIVIDEND = "dividend"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class TransactionStatus(Enum):
    """Transaction processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    REVERSED = "reversed"
    ON_HOLD = "on_hold"


class PaymentMethod(Enum):
    """Payment methods"""

    BANK_TRANSFER = "bank_transfer"
    WIRE_TRANSFER = "wire_transfer"
    ACH = "ach"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CRYPTO = "crypto"
    INTERNAL = "internal"


class Currency(Enum):
    """Supported currencies"""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    BTC = "BTC"
    ETH = "ETH"


@dataclass
class TransactionDetails:
    """Transaction details and metadata"""

    description: str
    reference_id: Optional[str]
    external_id: Optional[str]
    counterparty: Optional[str]
    payment_method: PaymentMethod
    routing_info: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class Transaction:
    """Complete transaction entity"""

    transaction_id: str
    user_id: str
    transaction_type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: Currency
    fee_amount: Decimal
    net_amount: Decimal
    details: TransactionDetails
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    settlement_date: Optional[datetime]
    confirmation_number: Optional[str]
    risk_score: float
    compliance_checks: Dict[str, Any]
    audit_trail: List[Dict[str, Any]]


@dataclass
class Balance:
    """Account balance information"""

    user_id: str
    currency: Currency
    available_balance: Decimal
    pending_balance: Decimal
    total_balance: Decimal
    reserved_balance: Decimal
    last_updated: datetime


@dataclass
class TransactionLimit:
    """Transaction limits for users"""

    user_id: str
    transaction_type: TransactionType
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal
    single_transaction_limit: Decimal
    currency: Currency
    effective_date: datetime
    expiry_date: Optional[datetime]


class TransactionService:
    """
    Comprehensive transaction processing service providing:
    - Transaction creation and validation
    - Balance management and tracking
    - Payment processing integration
    - Transaction limits and controls
    - Risk assessment and monitoring
    - Compliance checking and reporting
    - Settlement and reconciliation
    - Audit trail and reporting
    """

    def __init__(self) -> None:
        self.encryption_service = EncryptionService()
        self.kyc_service = KYCService()
        self.default_transaction_limits = {
            TransactionType.DEPOSIT: {
                "daily_limit": Decimal("50000.00"),
                "weekly_limit": Decimal("200000.00"),
                "monthly_limit": Decimal("500000.00"),
                "single_transaction_limit": Decimal("25000.00"),
            },
            TransactionType.WITHDRAWAL: {
                "daily_limit": Decimal("25000.00"),
                "weekly_limit": Decimal("100000.00"),
                "monthly_limit": Decimal("250000.00"),
                "single_transaction_limit": Decimal("10000.00"),
            },
            TransactionType.TRANSFER: {
                "daily_limit": Decimal("100000.00"),
                "weekly_limit": Decimal("500000.00"),
                "monthly_limit": Decimal("1000000.00"),
                "single_transaction_limit": Decimal("50000.00"),
            },
        }
        self.risk_thresholds = {
            "high_amount": Decimal("10000.00"),
            "suspicious_velocity": 5,
            "round_amount_threshold": Decimal("1000.00"),
            "unusual_time_hours": [0, 1, 2, 3, 4, 5],
        }
        self.fee_structure = {
            TransactionType.DEPOSIT: {
                PaymentMethod.BANK_TRANSFER: Decimal("0.00"),
                PaymentMethod.WIRE_TRANSFER: Decimal("25.00"),
                PaymentMethod.CREDIT_CARD: Decimal("0.029"),
                PaymentMethod.DEBIT_CARD: Decimal("0.015"),
            },
            TransactionType.WITHDRAWAL: {
                PaymentMethod.BANK_TRANSFER: Decimal("5.00"),
                PaymentMethod.WIRE_TRANSFER: Decimal("30.00"),
                PaymentMethod.ACH: Decimal("2.00"),
            },
            TransactionType.TRANSFER: {PaymentMethod.INTERNAL: Decimal("0.00")},
        }
        self.transactions: Dict[str, Transaction] = {}
        self.balances: Dict[Tuple[str, Currency], Balance] = {}
        self.transaction_limits: Dict[str, List[TransactionLimit]] = {}
        self.pending_transactions: Dict[str, Transaction] = {}
        self.processing_queue: List[str] = []
        self.settlement_queue: List[str] = []
        self._initialize_default_configurations()

    def _initialize_default_configurations(self) -> Any:
        """Initialize default configurations"""

    async def create_transaction(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: Currency,
        payment_method: PaymentMethod,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new transaction"""
        kyc_status = await self.kyc_service.get_kyc_status(user_id)
        if not kyc_status["verified"] and transaction_type in [
            TransactionType.WITHDRAWAL,
            TransactionType.TRANSFER,
        ]:
            raise ValueError("KYC verification required for this transaction type")
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        limit_check = await self._check_transaction_limits(
            user_id, transaction_type, amount, currency
        )
        if not limit_check["allowed"]:
            raise ValueError(f"Transaction exceeds limits: {limit_check['reason']}")
        fee_amount = await self._calculate_fee(transaction_type, amount, payment_method)
        net_amount = (
            amount - fee_amount
            if transaction_type == TransactionType.WITHDRAWAL
            else amount
        )
        if transaction_type in [TransactionType.WITHDRAWAL, TransactionType.TRANSFER]:
            balance_check = await self._check_balance_availability(
                user_id, currency, amount + fee_amount
            )
            if not balance_check["sufficient"]:
                raise ValueError("Insufficient balance for transaction")
        transaction_id = self._generate_transaction_id()
        transaction_details = TransactionDetails(
            description=details.get(
                "description", f"{transaction_type.value.title()} transaction"
            ),
            reference_id=details.get("reference_id"),
            external_id=details.get("external_id"),
            counterparty=details.get("counterparty"),
            payment_method=payment_method,
            routing_info=details.get("routing_info", {}),
            metadata=details.get("metadata", {}),
        )
        risk_assessment = await self._assess_transaction_risk(
            user_id, transaction_type, amount, currency, transaction_details
        )
        compliance_checks = await self._perform_compliance_checks(
            user_id, transaction_type, amount, currency, transaction_details
        )
        initial_status = self._determine_initial_status(
            risk_assessment, compliance_checks
        )
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            transaction_type=transaction_type,
            status=initial_status,
            amount=amount,
            currency=currency,
            fee_amount=fee_amount,
            net_amount=net_amount,
            details=transaction_details,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            processed_at=None,
            settlement_date=None,
            confirmation_number=None,
            risk_score=risk_assessment["risk_score"],
            compliance_checks=compliance_checks,
            audit_trail=[],
        )
        await self._add_audit_entry(
            transaction,
            "transaction_created",
            {
                "created_by": user_id,
                "initial_status": initial_status.value,
                "risk_score": risk_assessment["risk_score"],
            },
        )
        self.transactions[transaction_id] = transaction
        if transaction_type in [TransactionType.WITHDRAWAL, TransactionType.TRANSFER]:
            await self._reserve_balance(user_id, currency, amount + fee_amount)
        if initial_status != TransactionStatus.ON_HOLD:
            self.processing_queue.append(transaction_id)
            asyncio.create_task(self._process_transaction_async(transaction_id))
        logger.info(f"Transaction created: {transaction_id} for user {user_id}")
        return {
            "transaction_id": transaction_id,
            "status": transaction.status.value,
            "amount": str(transaction.amount),
            "currency": transaction.currency.value,
            "fee_amount": str(transaction.fee_amount),
            "net_amount": str(transaction.net_amount),
            "estimated_completion": self._estimate_completion_time(transaction),
            "risk_score": transaction.risk_score,
            "requires_review": initial_status == TransactionStatus.ON_HOLD,
        }

    async def get_transaction(
        self, transaction_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transaction details"""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        if user_id and transaction.user_id != user_id:
            raise ValueError("Unauthorized access to transaction")
        return {
            "transaction_id": transaction.transaction_id,
            "user_id": transaction.user_id,
            "type": transaction.transaction_type.value,
            "status": transaction.status.value,
            "amount": str(transaction.amount),
            "currency": transaction.currency.value,
            "fee_amount": str(transaction.fee_amount),
            "net_amount": str(transaction.net_amount),
            "description": transaction.details.description,
            "payment_method": transaction.details.payment_method.value,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "processed_at": (
                transaction.processed_at.isoformat()
                if transaction.processed_at
                else None
            ),
            "settlement_date": (
                transaction.settlement_date.isoformat()
                if transaction.settlement_date
                else None
            ),
            "confirmation_number": transaction.confirmation_number,
            "risk_score": transaction.risk_score,
            "metadata": transaction.details.metadata,
        }

    async def get_user_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        transaction_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get user's transaction history"""
        user_transactions = [
            tx for tx in self.transactions.values() if tx.user_id == user_id
        ]
        if status:
            user_transactions = [
                tx for tx in user_transactions if tx.status.value == status
            ]
        if transaction_type:
            user_transactions = [
                tx
                for tx in user_transactions
                if tx.transaction_type.value == transaction_type
            ]
        user_transactions.sort(key=lambda x: x.created_at, reverse=True)
        total_count = len(user_transactions)
        paginated_transactions = user_transactions[offset : offset + limit]
        formatted_transactions = []
        for tx in paginated_transactions:
            formatted_transactions.append(
                {
                    "transaction_id": tx.transaction_id,
                    "type": tx.transaction_type.value,
                    "status": tx.status.value,
                    "amount": str(tx.amount),
                    "currency": tx.currency.value,
                    "fee_amount": str(tx.fee_amount),
                    "net_amount": str(tx.net_amount),
                    "description": tx.details.description,
                    "created_at": tx.created_at.isoformat(),
                    "processed_at": (
                        tx.processed_at.isoformat() if tx.processed_at else None
                    ),
                }
            )
        return {
            "transactions": formatted_transactions,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    async def get_user_balance(
        self, user_id: str, currency: Currency
    ) -> Dict[str, Any]:
        """Get user's balance for specific currency"""
        balance_key = (user_id, currency)
        balance = self.balances.get(balance_key)
        if not balance:
            balance = Balance(
                user_id=user_id,
                currency=currency,
                available_balance=Decimal("0.00"),
                pending_balance=Decimal("0.00"),
                total_balance=Decimal("0.00"),
                reserved_balance=Decimal("0.00"),
                last_updated=datetime.now(timezone.utc),
            )
            self.balances[balance_key] = balance
        return {
            "user_id": balance.user_id,
            "currency": balance.currency.value,
            "available_balance": str(balance.available_balance),
            "pending_balance": str(balance.pending_balance),
            "total_balance": str(balance.total_balance),
            "reserved_balance": str(balance.reserved_balance),
            "last_updated": balance.last_updated.isoformat(),
        }

    async def get_user_balances(self, user_id: str) -> Dict[str, Any]:
        """Get all user balances"""
        user_balances = {}
        for (uid, currency), balance in self.balances.items():
            if uid == user_id:
                user_balances[currency.value] = {
                    "available_balance": str(balance.available_balance),
                    "pending_balance": str(balance.pending_balance),
                    "total_balance": str(balance.total_balance),
                    "reserved_balance": str(balance.reserved_balance),
                    "last_updated": balance.last_updated.isoformat(),
                }
        return {"user_id": user_id, "balances": user_balances}

    async def cancel_transaction(
        self, transaction_id: str, user_id: str, reason: str
    ) -> Dict[str, Any]:
        """Cancel a pending transaction"""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        if transaction.user_id != user_id:
            raise ValueError("Unauthorized access to transaction")
        if transaction.status not in [
            TransactionStatus.PENDING,
            TransactionStatus.ON_HOLD,
        ]:
            raise ValueError(
                f"Cannot cancel transaction with status: {transaction.status.value}"
            )
        transaction.status = TransactionStatus.CANCELLED
        transaction.updated_at = datetime.now(timezone.utc)
        if transaction.transaction_type in [
            TransactionType.WITHDRAWAL,
            TransactionType.TRANSFER,
        ]:
            await self._release_reserved_balance(
                user_id,
                transaction.currency,
                transaction.amount + transaction.fee_amount,
            )
        await self._add_audit_entry(
            transaction,
            "transaction_cancelled",
            {"cancelled_by": user_id, "reason": reason},
        )
        if transaction_id in self.processing_queue:
            self.processing_queue.remove(transaction_id)
        logger.info(f"Transaction cancelled: {transaction_id} by user {user_id}")
        return {
            "transaction_id": transaction_id,
            "status": transaction.status.value,
            "message": "Transaction cancelled successfully",
        }

    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"txn_{uuid.uuid4().hex[:16]}"

    async def _check_transaction_limits(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: Currency,
    ) -> Dict[str, Any]:
        """Check if transaction is within limits"""
        user_limits = self.transaction_limits.get(user_id, [])
        applicable_limit = None
        for limit in user_limits:
            if (
                limit.transaction_type == transaction_type
                and limit.currency == currency
                and (limit.effective_date <= datetime.now(timezone.utc))
                and (
                    not limit.expiry_date
                    or limit.expiry_date > datetime.now(timezone.utc)
                )
            ):
                applicable_limit = limit
                break
        if not applicable_limit:
            default_limits = self.default_transaction_limits.get(transaction_type, {})
            applicable_limit = TransactionLimit(
                user_id=user_id,
                transaction_type=transaction_type,
                daily_limit=default_limits.get("daily_limit", Decimal("10000.00")),
                weekly_limit=default_limits.get("weekly_limit", Decimal("50000.00")),
                monthly_limit=default_limits.get("monthly_limit", Decimal("100000.00")),
                single_transaction_limit=default_limits.get(
                    "single_transaction_limit", Decimal("5000.00")
                ),
                currency=currency,
                effective_date=datetime.now(timezone.utc),
                expiry_date=None,
            )
        if amount > applicable_limit.single_transaction_limit:
            return {
                "allowed": False,
                "reason": f"Amount exceeds single transaction limit of {applicable_limit.single_transaction_limit}",
            }
        current_usage = await self._calculate_current_usage(
            user_id, transaction_type, currency
        )
        if current_usage["daily"] + amount > applicable_limit.daily_limit:
            return {
                "allowed": False,
                "reason": f"Amount exceeds daily limit of {applicable_limit.daily_limit}",
            }
        if current_usage["weekly"] + amount > applicable_limit.weekly_limit:
            return {
                "allowed": False,
                "reason": f"Amount exceeds weekly limit of {applicable_limit.weekly_limit}",
            }
        if current_usage["monthly"] + amount > applicable_limit.monthly_limit:
            return {
                "allowed": False,
                "reason": f"Amount exceeds monthly limit of {applicable_limit.monthly_limit}",
            }
        return {"allowed": True}

    async def _calculate_current_usage(
        self, user_id: str, transaction_type: TransactionType, currency: Currency
    ) -> Dict[str, Decimal]:
        """Calculate current transaction usage for limits"""
        now = datetime.now(timezone.utc)
        daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekly_start = daily_start - timedelta(days=now.weekday())
        monthly_start = daily_start.replace(day=1)
        usage = {"daily": Decimal("0"), "weekly": Decimal("0"), "monthly": Decimal("0")}
        for tx in self.transactions.values():
            if (
                tx.user_id == user_id
                and tx.transaction_type == transaction_type
                and (tx.currency == currency)
                and (
                    tx.status
                    in [TransactionStatus.COMPLETED, TransactionStatus.PROCESSING]
                )
            ):
                if tx.created_at >= daily_start:
                    usage["daily"] += tx.amount
                if tx.created_at >= weekly_start:
                    usage["weekly"] += tx.amount
                if tx.created_at >= monthly_start:
                    usage["monthly"] += tx.amount
        return usage

    async def _calculate_fee(
        self,
        transaction_type: TransactionType,
        amount: Decimal,
        payment_method: PaymentMethod,
    ) -> Decimal:
        """Calculate transaction fee"""
        fee_config = self.fee_structure.get(transaction_type, {}).get(
            payment_method, Decimal("0")
        )
        if fee_config < 1:
            return (amount * fee_config).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            return fee_config

    async def _check_balance_availability(
        self, user_id: str, currency: Currency, required_amount: Decimal
    ) -> Dict[str, Any]:
        """Check if user has sufficient balance"""
        balance_key = (user_id, currency)
        balance = self.balances.get(balance_key)
        if not balance:
            return {"sufficient": False, "available": Decimal("0")}
        available = balance.available_balance - balance.reserved_balance
        return {
            "sufficient": available >= required_amount,
            "available": available,
            "required": required_amount,
        }

    async def _assess_transaction_risk(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: Currency,
        details: TransactionDetails,
    ) -> Dict[str, Any]:
        """Assess transaction risk score"""
        risk_score = 0.0
        risk_factors = []
        if amount >= self.risk_thresholds["high_amount"]:
            risk_score += 3.0
            risk_factors.append("high_amount")
        if amount % self.risk_thresholds["round_amount_threshold"] == 0:
            risk_score += 1.0
            risk_factors.append("round_amount")
        current_hour = datetime.now(timezone.utc).hour
        if current_hour in self.risk_thresholds["unusual_time_hours"]:
            risk_score += 1.5
            risk_factors.append("unusual_time")
        recent_transactions = await self._get_recent_transaction_count(user_id, hours=1)
        if recent_transactions >= self.risk_thresholds["suspicious_velocity"]:
            risk_score += 2.0
            risk_factors.append("high_velocity")
        if details.payment_method in [PaymentMethod.CRYPTO]:
            risk_score += 1.0
            risk_factors.append("high_risk_payment_method")
        if details.counterparty and await self._is_high_risk_counterparty(
            details.counterparty
        ):
            risk_score += 2.5
            risk_factors.append("high_risk_counterparty")
        return {
            "risk_score": min(risk_score, 10.0),
            "risk_factors": risk_factors,
            "risk_level": (
                "high" if risk_score >= 7 else "medium" if risk_score >= 4 else "low"
            ),
        }

    async def _perform_compliance_checks(
        self,
        user_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: Currency,
        details: TransactionDetails,
    ) -> Dict[str, Any]:
        """Perform compliance checks"""
        checks = {
            "kyc_verified": False,
            "sanctions_clear": True,
            "aml_clear": True,
            "ctr_required": False,
            "sar_required": False,
        }
        kyc_status = await self.kyc_service.get_kyc_status(user_id)
        checks["kyc_verified"] = kyc_status["verified"]
        if amount >= Decimal("10000.00"):
            checks["ctr_required"] = True
        if (
            amount >= Decimal("5000.00")
            and details.payment_method == PaymentMethod.CRYPTO
        ):
            checks["sar_required"] = True
        return checks

    def _determine_initial_status(
        self, risk_assessment: Dict[str, Any], compliance_checks: Dict[str, Any]
    ) -> TransactionStatus:
        """Determine initial transaction status"""
        if risk_assessment["risk_score"] >= 7.0:
            return TransactionStatus.ON_HOLD
        if not compliance_checks["kyc_verified"]:
            return TransactionStatus.ON_HOLD
        if compliance_checks["ctr_required"] or compliance_checks["sar_required"]:
            return TransactionStatus.ON_HOLD
        return TransactionStatus.PENDING

    async def _process_transaction_async(self, transaction_id: str):
        """Asynchronously process transaction"""
        try:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                return
            transaction.status = TransactionStatus.PROCESSING
            transaction.updated_at = datetime.now(timezone.utc)
            await self._add_audit_entry(transaction, "processing_started", {})
            await asyncio.sleep(2)
            if transaction.transaction_type == TransactionType.DEPOSIT:
                await self._process_deposit(transaction)
            elif transaction.transaction_type == TransactionType.WITHDRAWAL:
                await self._process_withdrawal(transaction)
            elif transaction.transaction_type == TransactionType.TRANSFER:
                await self._process_transfer(transaction)
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = datetime.now(timezone.utc)
            transaction.settlement_date = datetime.now(timezone.utc) + timedelta(days=1)
            transaction.confirmation_number = self._generate_confirmation_number()
            transaction.updated_at = datetime.now(timezone.utc)
            await self._add_audit_entry(
                transaction,
                "processing_completed",
                {"confirmation_number": transaction.confirmation_number},
            )
            logger.info(f"Transaction processed successfully: {transaction_id}")
        except Exception as e:
            transaction = self.transactions.get(transaction_id)
            if transaction:
                transaction.status = TransactionStatus.FAILED
                transaction.updated_at = datetime.now(timezone.utc)
                await self._add_audit_entry(
                    transaction, "processing_failed", {"error": str(e)}
                )
                if transaction.transaction_type in [
                    TransactionType.WITHDRAWAL,
                    TransactionType.TRANSFER,
                ]:
                    await self._release_reserved_balance(
                        transaction.user_id,
                        transaction.currency,
                        transaction.amount + transaction.fee_amount,
                    )
            logger.error(f"Transaction processing failed: {transaction_id} - {str(e)}")

    async def _process_deposit(self, transaction: Transaction):
        """Process deposit transaction"""
        await self._update_balance(
            transaction.user_id, transaction.currency, transaction.net_amount, "credit"
        )

    async def _process_withdrawal(self, transaction: Transaction):
        """Process withdrawal transaction"""
        await self._update_balance(
            transaction.user_id,
            transaction.currency,
            -(transaction.amount + transaction.fee_amount),
            "debit",
        )
        await self._release_reserved_balance(
            transaction.user_id,
            transaction.currency,
            transaction.amount + transaction.fee_amount,
        )

    async def _process_transfer(self, transaction: Transaction):
        """Process transfer transaction"""
        await self._update_balance(
            transaction.user_id,
            transaction.currency,
            -(transaction.amount + transaction.fee_amount),
            "debit",
        )
        await self._release_reserved_balance(
            transaction.user_id,
            transaction.currency,
            transaction.amount + transaction.fee_amount,
        )

    async def _update_balance(
        self, user_id: str, currency: Currency, amount: Decimal, operation: str
    ):
        """Update user balance"""
        balance_key = (user_id, currency)
        balance = self.balances.get(balance_key)
        if not balance:
            balance = Balance(
                user_id=user_id,
                currency=currency,
                available_balance=Decimal("0.00"),
                pending_balance=Decimal("0.00"),
                total_balance=Decimal("0.00"),
                reserved_balance=Decimal("0.00"),
                last_updated=datetime.now(timezone.utc),
            )
            self.balances[balance_key] = balance
        if operation == "credit":
            balance.available_balance += amount
            balance.total_balance += amount
        elif operation == "debit":
            balance.available_balance += amount
            balance.total_balance += amount
        balance.last_updated = datetime.now(timezone.utc)

    async def _reserve_balance(self, user_id: str, currency: Currency, amount: Decimal):
        """Reserve balance for pending transaction"""
        balance_key = (user_id, currency)
        balance = self.balances.get(balance_key)
        if balance:
            balance.reserved_balance += amount
            balance.available_balance -= amount
            balance.last_updated = datetime.now(timezone.utc)

    async def _release_reserved_balance(
        self, user_id: str, currency: Currency, amount: Decimal
    ):
        """Release reserved balance"""
        balance_key = (user_id, currency)
        balance = self.balances.get(balance_key)
        if balance:
            balance.reserved_balance -= amount
            balance.last_updated = datetime.now(timezone.utc)

    async def _add_audit_entry(
        self, transaction: Transaction, action: str, details: Dict[str, Any]
    ):
        """Add entry to transaction audit trail"""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "system_info": {"version": "1.0.0", "node": "primary"},
        }
        transaction.audit_trail.append(audit_entry)

    async def _get_recent_transaction_count(self, user_id: str, hours: int = 1) -> int:
        """Get count of recent transactions for velocity check"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        count = 0
        for tx in self.transactions.values():
            if (
                tx.user_id == user_id
                and tx.created_at >= cutoff_time
                and (tx.status != TransactionStatus.CANCELLED)
            ):
                count += 1
        return count

    async def _is_high_risk_counterparty(self, counterparty: str) -> bool:
        """Check if counterparty is high risk"""
        high_risk_patterns = ["suspicious", "blocked", "sanctioned"]
        return any((pattern in counterparty.lower() for pattern in high_risk_patterns))

    def _generate_confirmation_number(self) -> str:
        """Generate transaction confirmation number"""
        return f"CONF{secrets.token_hex(8).upper()}"

    def _estimate_completion_time(self, transaction: Transaction) -> str:
        """Estimate transaction completion time"""
        if transaction.details.payment_method == PaymentMethod.INTERNAL:
            return "Immediate"
        elif transaction.details.payment_method in [
            PaymentMethod.ACH,
            PaymentMethod.BANK_TRANSFER,
        ]:
            return "1-3 business days"
        elif transaction.details.payment_method == PaymentMethod.WIRE_TRANSFER:
            return "Same day"
        else:
            return "1-2 business days"

    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Get transaction service statistics"""
        status_counts = {}
        type_counts = {}
        total_volume = Decimal("0")
        for tx in self.transactions.values():
            status_counts[tx.status.value] = status_counts.get(tx.status.value, 0) + 1
            type_counts[tx.transaction_type.value] = (
                type_counts.get(tx.transaction_type.value, 0) + 1
            )
            if tx.status == TransactionStatus.COMPLETED:
                total_volume += tx.amount
        return {
            "total_transactions": len(self.transactions),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "total_volume": str(total_volume),
            "processing_queue_size": len(self.processing_queue),
            "settlement_queue_size": len(self.settlement_queue),
        }
