"""
Blockchain models for Fluxion backend
"""

import enum
from decimal import Decimal
from typing import Any, Dict, List, Optional

from models.base import AuditMixin, BaseModel, TimestampMixin
from sqlalchemy import (
    DECIMAL,
    JSON,
    BigInteger,
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


class NetworkStatus(enum.Enum):
    """Blockchain network status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class ContractStatus(enum.Enum):
    """Smart contract status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    UPGRADED = "upgraded"


class EventStatus(enum.Enum):
    """Contract event processing status"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class AssetStatus(enum.Enum):
    """Supply chain asset status"""

    CREATED = "created"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class BlockchainNetwork(BaseModel, TimestampMixin, AuditMixin):
    """Blockchain network configuration"""

    __tablename__ = "blockchain_networks"

    # Network identification
    name = Column(String(50), unique=True, nullable=False, comment="Network name")
    chain_id = Column(Integer, unique=True, nullable=False, comment="Chain ID")
    symbol = Column(String(10), nullable=False, comment="Native token symbol")

    # Network details
    network_type = Column(
        String(20), nullable=False, comment="Network type (mainnet, testnet)"
    )
    consensus_mechanism = Column(
        String(20), nullable=True, comment="Consensus mechanism"
    )
    block_time = Column(Integer, nullable=True, comment="Average block time in seconds")

    # RPC configuration
    rpc_url = Column(String(500), nullable=False, comment="Primary RPC URL")
    backup_rpc_urls = Column(JSON, nullable=True, comment="Backup RPC URLs")
    websocket_url = Column(String(500), nullable=True, comment="WebSocket URL")

    # Explorer and APIs
    explorer_url = Column(String(500), nullable=True, comment="Block explorer URL")
    api_key = Column(String(100), nullable=True, comment="API key for explorer")

    # Network status
    status = Column(
        Enum(NetworkStatus),
        default=NetworkStatus.ACTIVE,
        nullable=False,
        comment="Network status",
    )
    is_supported = Column(
        Boolean, default=True, nullable=False, comment="Network support status"
    )

    # Performance metrics
    current_block_number = Column(
        BigInteger, nullable=True, comment="Current block number"
    )
    last_block_time = Column(
        DateTime(timezone=True), nullable=True, comment="Last block timestamp"
    )
    average_gas_price = Column(
        DECIMAL(36, 18), nullable=True, comment="Average gas price"
    )

    # Configuration
    gas_limit_multiplier = Column(
        DECIMAL(5, 2), default=1.2, nullable=False, comment="Gas limit multiplier"
    )
    max_gas_price = Column(DECIMAL(36, 18), nullable=True, comment="Maximum gas price")
    confirmation_blocks = Column(
        Integer, default=12, nullable=False, comment="Required confirmation blocks"
    )

    # Relationships
    contracts = relationship(
        "SmartContract", back_populates="network", cascade="all, delete-orphan"
    )

    def is_active(self) -> bool:
        """Check if network is active"""
        return self.status == NetworkStatus.ACTIVE and self.is_supported

    def get_explorer_tx_url(self, tx_hash: str) -> Optional[str]:
        """Get transaction URL on block explorer"""
        if self.explorer_url:
            return f"{self.explorer_url}/tx/{tx_hash}"
        return None

    def get_explorer_address_url(self, address: str) -> Optional[str]:
        """Get address URL on block explorer"""
        if self.explorer_url:
            return f"{self.explorer_url}/address/{address}"
        return None


class SmartContract(BaseModel, TimestampMixin, AuditMixin):
    """Smart contract configuration"""

    __tablename__ = "smart_contracts"

    network_id = Column(
        UUID(as_uuid=True),
        ForeignKey("blockchain_networks.id"),
        nullable=False,
        comment="Network ID",
    )

    # Contract identification
    name = Column(String(100), nullable=False, comment="Contract name")
    address = Column(String(42), nullable=False, comment="Contract address")
    contract_type = Column(String(50), nullable=False, comment="Contract type")

    # Contract details
    abi = Column(JSON, nullable=False, comment="Contract ABI")
    bytecode = Column(Text, nullable=True, comment="Contract bytecode")
    source_code = Column(Text, nullable=True, comment="Contract source code")

    # Deployment information
    deployed_at_block = Column(
        BigInteger, nullable=True, comment="Deployment block number"
    )
    deployed_at_tx = Column(
        String(66), nullable=True, comment="Deployment transaction hash"
    )
    deployer_address = Column(String(42), nullable=True, comment="Deployer address")

    # Contract status
    status = Column(
        Enum(ContractStatus),
        default=ContractStatus.ACTIVE,
        nullable=False,
        comment="Contract status",
    )
    is_verified = Column(
        Boolean, default=False, nullable=False, comment="Source code verified"
    )
    is_proxy = Column(
        Boolean, default=False, nullable=False, comment="Is proxy contract"
    )
    implementation_address = Column(
        String(42), nullable=True, comment="Implementation contract address"
    )

    # Monitoring configuration
    monitor_events = Column(
        Boolean, default=True, nullable=False, comment="Monitor contract events"
    )
    event_filters = Column(JSON, nullable=True, comment="Event monitoring filters")
    last_processed_block = Column(
        BigInteger, nullable=True, comment="Last processed block"
    )

    # Version information
    version = Column(String(20), nullable=True, comment="Contract version")
    upgrade_history = Column(JSON, nullable=True, comment="Upgrade history")

    # Relationships
    network = relationship("BlockchainNetwork", back_populates="contracts")
    events = relationship(
        "ContractEvent", back_populates="contract", cascade="all, delete-orphan"
    )

    def is_active(self) -> bool:
        """Check if contract is active"""
        return self.status == ContractStatus.ACTIVE

    def get_function_abi(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get ABI for specific function"""
        if self.abi:
            for item in self.abi:
                if item.get("type") == "function" and item.get("name") == function_name:
                    return item
        return None

    def get_event_abi(self, event_name: str) -> Optional[Dict[str, Any]]:
        """Get ABI for specific event"""
        if self.abi:
            for item in self.abi:
                if item.get("type") == "event" and item.get("name") == event_name:
                    return item
        return None

    # Indexes
    __table_args__ = (
        Index(
            "idx_smart_contracts_network_address", "network_id", "address", unique=True
        ),
        Index("idx_smart_contracts_type", "contract_type"),
        Index("idx_smart_contracts_status", "status"),
    )


class ContractEvent(BaseModel, TimestampMixin):
    """Contract event model"""

    __tablename__ = "contract_events"

    contract_id = Column(
        UUID(as_uuid=True),
        ForeignKey("smart_contracts.id"),
        nullable=False,
        comment="Contract ID",
    )

    # Event identification
    event_name = Column(String(100), nullable=False, comment="Event name")
    event_signature = Column(String(66), nullable=True, comment="Event signature hash")

    # Transaction details
    transaction_hash = Column(String(66), nullable=False, comment="Transaction hash")
    block_number = Column(BigInteger, nullable=False, comment="Block number")
    block_hash = Column(String(66), nullable=True, comment="Block hash")
    log_index = Column(Integer, nullable=False, comment="Log index in transaction")
    transaction_index = Column(
        Integer, nullable=True, comment="Transaction index in block"
    )

    # Event data
    raw_data = Column(Text, nullable=True, comment="Raw event data")
    decoded_data = Column(JSON, nullable=True, comment="Decoded event data")
    topics = Column(JSON, nullable=True, comment="Event topics")

    # Processing status
    status = Column(
        Enum(EventStatus),
        default=EventStatus.PENDING,
        nullable=False,
        comment="Processing status",
    )
    processed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Processing timestamp"
    )
    error_message = Column(
        Text, nullable=True, comment="Error message if processing failed"
    )

    # Business logic
    business_event_type = Column(
        String(50), nullable=True, comment="Business event type"
    )
    related_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Related user ID",
    )
    related_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
        comment="Related transaction ID",
    )

    # Relationships
    contract = relationship("SmartContract", back_populates="events")
    user = relationship("User")
    transaction = relationship("Transaction")

    def is_processed(self) -> bool:
        """Check if event is processed"""
        return self.status == EventStatus.PROCESSED

    def get_decoded_param(self, param_name: str) -> Any:
        """Get decoded parameter value"""
        if self.decoded_data and isinstance(self.decoded_data, dict):
            return self.decoded_data.get(param_name)
        return None

    # Indexes
    __table_args__ = (
        Index("idx_contract_events_contract_block", "contract_id", "block_number"),
        Index("idx_contract_events_tx_hash", "transaction_hash"),
        Index("idx_contract_events_event_name", "event_name"),
        Index("idx_contract_events_status", "status"),
        Index("idx_contract_events_user", "related_user_id"),
    )


class SupplyChainAsset(BaseModel, TimestampMixin, AuditMixin):
    """Supply chain asset model"""

    __tablename__ = "supply_chain_assets"

    # Asset identification
    asset_id = Column(
        BigInteger, unique=True, nullable=False, comment="On-chain asset ID"
    )
    asset_metadata = Column(Text, nullable=False, comment="Asset metadata")

    # Current state
    current_custodian = Column(
        String(42), nullable=False, comment="Current custodian address"
    )
    status = Column(
        Enum(AssetStatus),
        default=AssetStatus.CREATED,
        nullable=False,
        comment="Asset status",
    )
    location = Column(String(200), nullable=True, comment="Current location")

    # Creation details
    creator_address = Column(
        String(42), nullable=False, comment="Asset creator address"
    )
    creation_tx_hash = Column(
        String(66), nullable=False, comment="Creation transaction hash"
    )
    creation_block = Column(BigInteger, nullable=False, comment="Creation block number")

    # Transfer tracking
    transfer_count = Column(
        Integer, default=0, nullable=False, comment="Number of transfers"
    )
    last_transfer_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last transfer timestamp"
    )

    # Verification and compliance
    is_verified = Column(
        Boolean, default=False, nullable=False, comment="Asset verification status"
    )
    verification_score = Column(Float, nullable=True, comment="Verification score")
    compliance_flags = Column(JSON, nullable=True, comment="Compliance flags")

    # Additional data
    properties = Column(JSON, nullable=True, comment="Asset properties")
    documents = Column(JSON, nullable=True, comment="Related documents")

    # Relationships
    transfers = relationship(
        "AssetTransfer", back_populates="asset", cascade="all, delete-orphan"
    )

    def get_transfer_history(self) -> List["AssetTransfer"]:
        """Get asset transfer history"""
        return sorted(self.transfers, key=lambda x: x.transfer_timestamp)

    def get_current_location_info(self) -> Dict[str, Any]:
        """Get current location information"""
        return {
            "custodian": self.current_custodian,
            "location": self.location,
            "status": self.status.value,
            "last_update": self.updated_at,
        }

    # Indexes
    __table_args__ = (
        Index("idx_supply_chain_assets_custodian", "current_custodian"),
        Index("idx_supply_chain_assets_status", "status"),
        Index("idx_supply_chain_assets_creator", "creator_address"),
    )


class AssetTransfer(BaseModel, TimestampMixin):
    """Asset transfer model"""

    __tablename__ = "asset_transfers"

    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("supply_chain_assets.id"),
        nullable=False,
        comment="Asset ID",
    )

    # Transfer details
    from_address = Column(String(42), nullable=False, comment="Source address")
    to_address = Column(String(42), nullable=False, comment="Destination address")
    transfer_timestamp = Column(
        DateTime(timezone=True), nullable=False, comment="Transfer timestamp"
    )

    # Location information
    from_location = Column(String(200), nullable=True, comment="Source location")
    to_location = Column(String(200), nullable=True, comment="Destination location")

    # Blockchain details
    transaction_hash = Column(
        String(66), nullable=False, comment="Transfer transaction hash"
    )
    block_number = Column(BigInteger, nullable=False, comment="Block number")

    # Proof and verification
    proof_hash = Column(String(66), nullable=True, comment="Transfer proof hash")
    is_verified = Column(
        Boolean, default=False, nullable=False, comment="Transfer verification status"
    )
    verification_notes = Column(Text, nullable=True, comment="Verification notes")

    # Relationships
    asset = relationship("SupplyChainAsset", back_populates="transfers")

    # Indexes
    __table_args__ = (
        Index("idx_asset_transfers_asset_timestamp", "asset_id", "transfer_timestamp"),
        Index("idx_asset_transfers_from_address", "from_address"),
        Index("idx_asset_transfers_to_address", "to_address"),
        Index("idx_asset_transfers_tx_hash", "transaction_hash"),
    )


class LiquidityPool(BaseModel, TimestampMixin, AuditMixin):
    """Liquidity pool model"""

    __tablename__ = "liquidity_pools"

    # Pool identification
    pool_id = Column(
        BigInteger, unique=True, nullable=False, comment="On-chain pool ID"
    )
    name = Column(String(100), nullable=False, comment="Pool name")

    # Pool configuration
    assets = Column(JSON, nullable=False, comment="Pool assets")
    weights = Column(JSON, nullable=False, comment="Asset weights")
    fee = Column(DECIMAL(10, 8), nullable=False, comment="Pool fee")
    amplification = Column(Integer, nullable=True, comment="Amplification parameter")

    # Pool status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Pool active status"
    )
    is_paused = Column(
        Boolean, default=False, nullable=False, comment="Pool paused status"
    )

    # Liquidity metrics
    total_liquidity = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Total liquidity"
    )
    total_volume = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Total trading volume"
    )
    total_fees = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Total fees collected"
    )

    # Performance metrics
    apy = Column(Float, nullable=True, comment="Annual percentage yield")
    daily_volume = Column(
        DECIMAL(36, 18), nullable=True, comment="Daily trading volume"
    )
    weekly_volume = Column(
        DECIMAL(36, 18), nullable=True, comment="Weekly trading volume"
    )

    # Oracle configuration
    oracles = Column(JSON, nullable=True, comment="Price oracles")
    oracle_heartbeats = Column(
        JSON, nullable=True, comment="Oracle heartbeat intervals"
    )

    # Creation details
    creator_address = Column(String(42), nullable=False, comment="Pool creator address")
    creation_tx_hash = Column(
        String(66), nullable=False, comment="Creation transaction hash"
    )
    creation_block = Column(BigInteger, nullable=False, comment="Creation block number")

    def calculate_pool_share(self, user_liquidity: Decimal) -> float:
        """Calculate user's share of the pool"""
        if self.total_liquidity > 0:
            return float((user_liquidity / self.total_liquidity) * 100)
        return 0.0

    def get_asset_allocation(self) -> Dict[str, float]:
        """Get current asset allocation"""
        if self.assets and self.weights:
            return dict(zip(self.assets, self.weights))
        return {}

    # Indexes
    __table_args__ = (
        Index("idx_liquidity_pools_active", "is_active"),
        Index("idx_liquidity_pools_creator", "creator_address"),
    )


class SyntheticAsset(BaseModel, TimestampMixin, AuditMixin):
    """Synthetic asset model"""

    __tablename__ = "synthetic_assets"

    # Asset identification
    asset_id = Column(String(66), unique=True, nullable=False, comment="Asset ID hash")
    name = Column(String(100), nullable=False, comment="Asset name")
    symbol = Column(String(20), nullable=False, comment="Asset symbol")

    # Underlying asset
    underlying_asset = Column(String(100), nullable=False, comment="Underlying asset")
    collateral_ratio = Column(
        DECIMAL(10, 8), nullable=False, comment="Collateral ratio"
    )

    # Supply information
    total_supply = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Total supply"
    )
    circulating_supply = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Circulating supply"
    )

    # Price information
    current_price = Column(DECIMAL(36, 18), nullable=True, comment="Current price")
    target_price = Column(DECIMAL(36, 18), nullable=True, comment="Target price")
    price_deviation = Column(Float, nullable=True, comment="Price deviation percentage")

    # Oracle configuration
    oracle_address = Column(String(42), nullable=False, comment="Price oracle address")
    oracle_job_id = Column(String(66), nullable=False, comment="Oracle job ID")
    oracle_fee = Column(DECIMAL(36, 18), nullable=False, comment="Oracle fee")

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Asset active status"
    )
    is_paused = Column(
        Boolean, default=False, nullable=False, comment="Asset paused status"
    )

    # Creation details
    creator_address = Column(
        String(42), nullable=False, comment="Asset creator address"
    )
    creation_tx_hash = Column(
        String(66), nullable=False, comment="Creation transaction hash"
    )
    creation_block = Column(BigInteger, nullable=False, comment="Creation block number")

    def calculate_collateral_value(self) -> Optional[Decimal]:
        """Calculate required collateral value"""
        if self.current_price and self.total_supply:
            return self.current_price * self.total_supply * self.collateral_ratio
        return None

    def is_properly_collateralized(self, actual_collateral: Decimal) -> bool:
        """Check if asset is properly collateralized"""
        required_collateral = self.calculate_collateral_value()
        if required_collateral:
            return actual_collateral >= required_collateral
        return False

    # Indexes
    __table_args__ = (
        Index("idx_synthetic_assets_symbol", "symbol"),
        Index("idx_synthetic_assets_active", "is_active"),
        Index("idx_synthetic_assets_creator", "creator_address"),
    )
