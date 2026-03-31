"""
Portfolio models for Fluxion backend
"""

import enum
from decimal import Decimal
from typing import List, Optional

from models.base import AuditMixin, BaseModel, ComplianceMixin, TimestampMixin
from sqlalchemy import (
    DECIMAL,
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


class AssetType(enum.Enum):
    """Asset types"""

    CRYPTOCURRENCY = "cryptocurrency"
    TOKEN = "token"
    NFT = "nft"
    SYNTHETIC = "synthetic"
    LIQUIDITY_POOL = "liquidity_pool"
    STAKED_ASSET = "staked_asset"
    SUPPLY_CHAIN_ASSET = "supply_chain_asset"
    GOVERNANCE_TOKEN = "governance_token"


class AssetStatus(enum.Enum):
    """Asset status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    STAKED = "staked"
    PENDING = "pending"
    DEPRECATED = "deprecated"


class PortfolioStatus(enum.Enum):
    """Portfolio status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    FROZEN = "frozen"
    UNDER_REVIEW = "under_review"


class Portfolio(BaseModel, TimestampMixin, AuditMixin, ComplianceMixin):
    """User portfolio model"""

    __tablename__ = "portfolios"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )

    # Portfolio details
    name = Column(String(100), nullable=False, comment="Portfolio name")
    description = Column(Text, nullable=True, comment="Portfolio description")
    status = Column(
        Enum(PortfolioStatus),
        default=PortfolioStatus.ACTIVE,
        nullable=False,
        comment="Portfolio status",
    )

    # Portfolio type and strategy
    portfolio_type = Column(
        String(50), default="default", nullable=False, comment="Portfolio type"
    )
    investment_strategy = Column(
        String(100), nullable=True, comment="Investment strategy"
    )
    risk_level = Column(String(20), nullable=True, comment="Risk level")

    # Financial metrics
    total_value_usd = Column(
        DECIMAL(20, 8),
        default=0,
        nullable=False,
        comment="Total portfolio value in USD",
    )
    total_cost_basis_usd = Column(
        DECIMAL(20, 8), default=0, nullable=False, comment="Total cost basis in USD"
    )
    unrealized_pnl_usd = Column(
        DECIMAL(20, 8), default=0, nullable=False, comment="Unrealized P&L in USD"
    )
    realized_pnl_usd = Column(
        DECIMAL(20, 8), default=0, nullable=False, comment="Realized P&L in USD"
    )

    # Performance metrics
    daily_return = Column(Float, nullable=True, comment="Daily return percentage")
    weekly_return = Column(Float, nullable=True, comment="Weekly return percentage")
    monthly_return = Column(Float, nullable=True, comment="Monthly return percentage")
    yearly_return = Column(Float, nullable=True, comment="Yearly return percentage")
    all_time_return = Column(Float, nullable=True, comment="All-time return percentage")

    # Risk metrics
    volatility = Column(Float, nullable=True, comment="Portfolio volatility")
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe ratio")
    max_drawdown = Column(Float, nullable=True, comment="Maximum drawdown")
    value_at_risk = Column(DECIMAL(20, 8), nullable=True, comment="Value at Risk (VaR)")

    # Diversification
    asset_count = Column(
        Integer, default=0, nullable=False, comment="Number of different assets"
    )
    network_count = Column(
        Integer, default=0, nullable=False, comment="Number of different networks"
    )

    # Timestamps
    last_updated_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last portfolio update"
    )
    last_rebalanced_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last rebalancing"
    )

    # Settings
    auto_rebalance = Column(
        Boolean, default=False, nullable=False, comment="Auto-rebalancing enabled"
    )
    rebalance_threshold = Column(
        Float, default=5.0, nullable=False, comment="Rebalancing threshold percentage"
    )

    # Relationships
    user = relationship("User", back_populates="portfolios")
    assets = relationship(
        "PortfolioAsset", back_populates="portfolio", cascade="all, delete-orphan"
    )
    holdings = relationship(
        "AssetHolding", back_populates="portfolio", cascade="all, delete-orphan"
    )

    def calculate_total_value(self) -> Decimal:
        """Calculate total portfolio value"""
        total = Decimal("0")
        for holding in self.holdings:
            if holding.current_value_usd:
                total += holding.current_value_usd
        return total

    def calculate_allocation_percentage(self, asset_symbol: str) -> float:
        """Calculate asset allocation percentage"""
        if self.total_value_usd == 0:
            return 0.0

        asset_value = Decimal("0")
        for holding in self.holdings:
            if holding.asset_symbol == asset_symbol and holding.current_value_usd:
                asset_value += holding.current_value_usd

        return float((asset_value / self.total_value_usd) * 100)

    def get_top_holdings(self, limit: int = 10) -> List["AssetHolding"]:
        """Get top holdings by value"""
        return sorted(
            [h for h in self.holdings if h.current_value_usd],
            key=lambda x: x.current_value_usd,
            reverse=True,
        )[:limit]

    def needs_rebalancing(self) -> bool:
        """Check if portfolio needs rebalancing"""
        if not self.auto_rebalance:
            return False

        # Check if any asset allocation deviates from target by threshold
        for asset in self.assets:
            if asset.target_allocation:
                current_allocation = self.calculate_allocation_percentage(
                    asset.asset_symbol
                )
                deviation = abs(current_allocation - asset.target_allocation)
                if deviation > self.rebalance_threshold:
                    return True

        return False


class PortfolioAsset(BaseModel, TimestampMixin, AuditMixin):
    """Portfolio asset configuration"""

    __tablename__ = "portfolio_assets"

    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=False,
        comment="Portfolio ID",
    )

    # Asset identification
    asset_symbol = Column(String(20), nullable=False, comment="Asset symbol")
    asset_name = Column(String(100), nullable=True, comment="Asset name")
    asset_type = Column(Enum(AssetType), nullable=False, comment="Asset type")
    contract_address = Column(String(42), nullable=True, comment="Contract address")
    network = Column(String(50), nullable=True, comment="Blockchain network")

    # Portfolio allocation
    target_allocation = Column(
        Float, nullable=True, comment="Target allocation percentage"
    )
    min_allocation = Column(
        Float, nullable=True, comment="Minimum allocation percentage"
    )
    max_allocation = Column(
        Float, nullable=True, comment="Maximum allocation percentage"
    )

    # Asset status
    status = Column(
        Enum(AssetStatus),
        default=AssetStatus.ACTIVE,
        nullable=False,
        comment="Asset status",
    )
    is_tracked = Column(
        Boolean, default=True, nullable=False, comment="Asset tracking enabled"
    )

    # Relationships
    portfolio = relationship("Portfolio", back_populates="assets")

    # Unique constraint
    __table_args__ = (
        Index(
            "idx_portfolio_assets_unique",
            "portfolio_id",
            "asset_symbol",
            "contract_address",
            unique=True,
        ),
    )


class AssetHolding(BaseModel, TimestampMixin, AuditMixin):
    """Asset holding details"""

    __tablename__ = "asset_holdings"

    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=False,
        comment="Portfolio ID",
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )

    # Asset identification
    asset_symbol = Column(String(20), nullable=False, comment="Asset symbol")
    asset_name = Column(String(100), nullable=True, comment="Asset name")
    asset_type = Column(Enum(AssetType), nullable=False, comment="Asset type")
    contract_address = Column(String(42), nullable=True, comment="Contract address")
    network = Column(String(50), nullable=False, comment="Blockchain network")

    # Holding quantities
    quantity = Column(DECIMAL(36, 18), nullable=False, comment="Quantity held")
    available_quantity = Column(
        DECIMAL(36, 18), nullable=False, comment="Available quantity"
    )
    locked_quantity = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Locked quantity"
    )
    staked_quantity = Column(
        DECIMAL(36, 18), default=0, nullable=False, comment="Staked quantity"
    )

    # Cost basis and valuation
    average_cost_price = Column(
        DECIMAL(36, 18), nullable=True, comment="Average cost price"
    )
    total_cost_basis = Column(DECIMAL(20, 8), nullable=True, comment="Total cost basis")
    current_price = Column(DECIMAL(36, 18), nullable=True, comment="Current price")
    current_value_usd = Column(
        DECIMAL(20, 8), nullable=True, comment="Current value in USD"
    )

    # P&L calculations
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True, comment="Unrealized P&L")
    unrealized_pnl_percentage = Column(
        Float, nullable=True, comment="Unrealized P&L percentage"
    )
    realized_pnl = Column(
        DECIMAL(20, 8), default=0, nullable=False, comment="Realized P&L"
    )

    # Wallet and location
    wallet_address = Column(String(42), nullable=True, comment="Wallet address")
    wallet_type = Column(String(50), nullable=True, comment="Wallet type")

    # Metadata
    last_price_update = Column(
        DateTime(timezone=True), nullable=True, comment="Last price update"
    )
    price_source = Column(String(50), nullable=True, comment="Price data source")

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    user = relationship("User")

    def calculate_unrealized_pnl(self) -> Optional[Decimal]:
        """Calculate unrealized P&L"""
        if self.current_value_usd and self.total_cost_basis:
            return self.current_value_usd - self.total_cost_basis
        return None

    def calculate_unrealized_pnl_percentage(self) -> Optional[float]:
        """Calculate unrealized P&L percentage"""
        if self.total_cost_basis and self.total_cost_basis > 0:
            pnl = self.calculate_unrealized_pnl()
            if pnl is not None:
                return float((pnl / self.total_cost_basis) * 100)
        return None

    def get_allocation_percentage(self) -> float:
        """Get allocation percentage within portfolio"""
        if (
            self.portfolio
            and self.portfolio.total_value_usd > 0
            and self.current_value_usd
        ):
            return float(
                (self.current_value_usd / self.portfolio.total_value_usd) * 100
            )
        return 0.0

    # Indexes for performance
    __table_args__ = (
        Index("idx_asset_holdings_portfolio_asset", "portfolio_id", "asset_symbol"),
        Index("idx_asset_holdings_user_asset", "user_id", "asset_symbol"),
        Index("idx_asset_holdings_network", "network"),
        Index("idx_asset_holdings_wallet", "wallet_address"),
    )


class PortfolioSnapshot(BaseModel, TimestampMixin):
    """Portfolio performance snapshots"""

    __tablename__ = "portfolio_snapshots"

    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=False,
        comment="Portfolio ID",
    )

    # Snapshot details
    snapshot_date = Column(
        DateTime(timezone=True), nullable=False, comment="Snapshot date"
    )
    snapshot_type = Column(
        String(20), nullable=False, comment="Snapshot type (daily, weekly, monthly)"
    )

    # Financial metrics
    total_value_usd = Column(
        DECIMAL(20, 8), nullable=False, comment="Total value in USD"
    )
    total_cost_basis_usd = Column(
        DECIMAL(20, 8), nullable=False, comment="Total cost basis in USD"
    )
    unrealized_pnl_usd = Column(
        DECIMAL(20, 8), nullable=False, comment="Unrealized P&L in USD"
    )
    realized_pnl_usd = Column(
        DECIMAL(20, 8), nullable=False, comment="Realized P&L in USD"
    )

    # Performance metrics
    daily_return = Column(Float, nullable=True, comment="Daily return")
    cumulative_return = Column(Float, nullable=True, comment="Cumulative return")

    # Risk metrics
    volatility = Column(Float, nullable=True, comment="Volatility")
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe ratio")

    # Asset allocation
    asset_allocation = Column(JSON, nullable=True, comment="Asset allocation breakdown")
    top_holdings = Column(JSON, nullable=True, comment="Top holdings")

    # Relationships
    portfolio = relationship("Portfolio")

    # Indexes
    __table_args__ = (
        Index("idx_portfolio_snapshots_date", "portfolio_id", "snapshot_date"),
        Index("idx_portfolio_snapshots_type", "snapshot_type"),
    )


class AssetPrice(BaseModel, TimestampMixin):
    """Asset price tracking"""

    __tablename__ = "asset_prices"

    # Asset identification
    asset_symbol = Column(String(20), nullable=False, comment="Asset symbol")
    contract_address = Column(String(42), nullable=True, comment="Contract address")
    network = Column(String(50), nullable=False, comment="Blockchain network")

    # Price data
    price_usd = Column(DECIMAL(36, 18), nullable=False, comment="Price in USD")
    price_btc = Column(DECIMAL(36, 18), nullable=True, comment="Price in BTC")
    price_eth = Column(DECIMAL(36, 18), nullable=True, comment="Price in ETH")

    # Market data
    market_cap = Column(DECIMAL(20, 8), nullable=True, comment="Market capitalization")
    volume_24h = Column(DECIMAL(20, 8), nullable=True, comment="24-hour trading volume")

    # Price changes
    change_1h = Column(Float, nullable=True, comment="1-hour price change percentage")
    change_24h = Column(Float, nullable=True, comment="24-hour price change percentage")
    change_7d = Column(Float, nullable=True, comment="7-day price change percentage")

    # Data source
    source = Column(String(50), nullable=False, comment="Price data source")
    source_timestamp = Column(
        DateTime(timezone=True), nullable=True, comment="Source timestamp"
    )

    # Indexes
    __table_args__ = (
        Index("idx_asset_prices_symbol_time", "asset_symbol", "created_at"),
        Index("idx_asset_prices_contract_time", "contract_address", "created_at"),
        Index("idx_asset_prices_source", "source"),
    )
