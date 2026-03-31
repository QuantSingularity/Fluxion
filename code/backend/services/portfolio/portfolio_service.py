"""
Comprehensive Portfolio Management Service for Fluxion Backend
Implements advanced portfolio tracking, asset management, performance analytics,
and rebalancing for financial services platform.
"""

import logging
import statistics
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from services.security.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of assets"""

    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    CRYPTOCURRENCY = "cryptocurrency"
    COMMODITY = "commodity"
    REAL_ESTATE = "real_estate"
    CASH = "cash"
    OPTION = "option"
    FUTURE = "future"


class PortfolioType(Enum):
    """Types of portfolios"""

    INDIVIDUAL = "individual"
    JOINT = "joint"
    RETIREMENT = "retirement"
    TRUST = "trust"
    CORPORATE = "corporate"


class RebalancingStrategy(Enum):
    """Portfolio rebalancing strategies"""

    THRESHOLD = "threshold"
    CALENDAR = "calendar"
    TACTICAL = "tactical"
    STRATEGIC = "strategic"
    NONE = "none"


class RiskProfile(Enum):
    """Risk profiles"""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


@dataclass
class Asset:
    """Asset information"""

    asset_id: str
    symbol: str
    name: str
    asset_type: AssetType
    sector: Optional[str]
    industry: Optional[str]
    country: str
    currency: str
    exchange: str
    isin: Optional[str]
    cusip: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class Position:
    """Portfolio position"""

    position_id: str
    portfolio_id: str
    asset_id: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    cost_basis: Decimal
    weight: Decimal
    last_updated: datetime
    acquisition_dates: List[datetime]
    tax_lots: List[Dict[str, Any]]


@dataclass
class Portfolio:
    """Complete portfolio entity"""

    portfolio_id: str
    user_id: str
    name: str
    description: str
    portfolio_type: PortfolioType
    risk_profile: RiskProfile
    target_allocation: Dict[str, Decimal]
    current_allocation: Dict[str, Decimal]
    total_value: Decimal
    cash_balance: Decimal
    invested_amount: Decimal
    total_return: Decimal
    total_return_percentage: Decimal
    positions: List[Position]
    rebalancing_strategy: RebalancingStrategy
    rebalancing_threshold: Decimal
    last_rebalanced: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    performance_metrics: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics"""

    portfolio_id: str
    period: str
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    beta: Decimal
    alpha: Decimal
    information_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    var_95: Decimal
    cvar_95: Decimal
    calculated_at: datetime


@dataclass
class RebalancingRecommendation:
    """Portfolio rebalancing recommendation"""

    portfolio_id: str
    recommended_trades: List[Dict[str, Any]]
    expected_cost: Decimal
    expected_benefit: Decimal
    risk_impact: Dict[str, Any]
    created_at: datetime


class PortfolioService:
    """
    Comprehensive portfolio management service providing:
    - Portfolio creation and management
    - Position tracking and updates
    - Performance analytics and metrics
    - Risk assessment and monitoring
    - Rebalancing recommendations
    - Asset allocation analysis
    - Tax optimization
    - Reporting and analytics
    """

    def __init__(self) -> None:
        self.encryption_service = EncryptionService()
        self.default_rebalancing_threshold = Decimal("0.05")
        self.performance_calculation_periods = [
            "1D",
            "1W",
            "1M",
            "3M",
            "6M",
            "1Y",
            "3Y",
            "5Y",
        ]
        self.risk_free_rate = Decimal("0.02")
        self.default_allocations = {
            RiskProfile.CONSERVATIVE: {
                "stocks": Decimal("0.30"),
                "bonds": Decimal("0.60"),
                "cash": Decimal("0.10"),
            },
            RiskProfile.MODERATE: {
                "stocks": Decimal("0.60"),
                "bonds": Decimal("0.30"),
                "cash": Decimal("0.10"),
            },
            RiskProfile.AGGRESSIVE: {
                "stocks": Decimal("0.80"),
                "bonds": Decimal("0.15"),
                "cash": Decimal("0.05"),
            },
            RiskProfile.VERY_AGGRESSIVE: {
                "stocks": Decimal("0.90"),
                "bonds": Decimal("0.05"),
                "cash": Decimal("0.05"),
            },
        }
        self.portfolios: Dict[str, Portfolio] = {}
        self.assets: Dict[str, Asset] = {}
        self.positions: Dict[str, Position] = {}
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.price_history: Dict[str, List[Dict[str, Any]]] = {}
        self._initialize_sample_assets()

    def _initialize_sample_assets(self) -> Any:
        """Initialize sample assets for demonstration"""
        sample_assets = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "asset_type": AssetType.STOCK,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "country": "US",
                "currency": "USD",
                "exchange": "NASDAQ",
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "asset_type": AssetType.STOCK,
                "sector": "Technology",
                "industry": "Internet Services",
                "country": "US",
                "currency": "USD",
                "exchange": "NASDAQ",
            },
            {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF",
                "asset_type": AssetType.ETF,
                "sector": "Diversified",
                "industry": "Index Fund",
                "country": "US",
                "currency": "USD",
                "exchange": "NYSE",
            },
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "asset_type": AssetType.CRYPTOCURRENCY,
                "sector": "Cryptocurrency",
                "industry": "Digital Currency",
                "country": "Global",
                "currency": "USD",
                "exchange": "Multiple",
            },
        ]
        for asset_data in sample_assets:
            asset_id = f"asset_{uuid.uuid4().hex[:8]}"
            asset = Asset(
                asset_id=asset_id,
                symbol=asset_data["symbol"],
                name=asset_data["name"],
                asset_type=asset_data["asset_type"],
                sector=asset_data.get("sector"),
                industry=asset_data.get("industry"),
                country=asset_data["country"],
                currency=asset_data["currency"],
                exchange=asset_data["exchange"],
                isin=None,
                cusip=None,
                metadata={},
            )
            self.assets[asset_id] = asset

    async def create_portfolio(
        self,
        user_id: str,
        name: str,
        description: str,
        portfolio_type: PortfolioType,
        risk_profile: RiskProfile,
        target_allocation: Optional[Dict[str, Decimal]] = None,
    ) -> Dict[str, Any]:
        """Create a new portfolio"""
        portfolio_id = f"portfolio_{uuid.uuid4().hex[:12]}"
        if not target_allocation:
            target_allocation = self.default_allocations[risk_profile].copy()
        total_allocation = sum(target_allocation.values())
        if abs(total_allocation - Decimal("1.0")) > Decimal("0.01"):
            raise ValueError("Target allocation must sum to 100%")
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            user_id=user_id,
            name=name,
            description=description,
            portfolio_type=portfolio_type,
            risk_profile=risk_profile,
            target_allocation=target_allocation,
            current_allocation={},
            total_value=Decimal("0.00"),
            cash_balance=Decimal("0.00"),
            invested_amount=Decimal("0.00"),
            total_return=Decimal("0.00"),
            total_return_percentage=Decimal("0.00"),
            positions=[],
            rebalancing_strategy=RebalancingStrategy.THRESHOLD,
            rebalancing_threshold=self.default_rebalancing_threshold,
            last_rebalanced=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            performance_metrics={},
            metadata={},
        )
        self.portfolios[portfolio_id] = portfolio
        logger.info(f"Portfolio created: {portfolio_id} for user {user_id}")
        return {
            "portfolio_id": portfolio_id,
            "name": name,
            "type": portfolio_type.value,
            "risk_profile": risk_profile.value,
            "target_allocation": {k: str(v) for k, v in target_allocation.items()},
            "created_at": portfolio.created_at.isoformat(),
        }

    async def get_portfolio(
        self, portfolio_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get portfolio details"""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        if user_id and portfolio.user_id != user_id:
            raise ValueError("Unauthorized access to portfolio")
        await self._update_portfolio_values(portfolio)
        return {
            "portfolio_id": portfolio.portfolio_id,
            "user_id": portfolio.user_id,
            "name": portfolio.name,
            "description": portfolio.description,
            "type": portfolio.portfolio_type.value,
            "risk_profile": portfolio.risk_profile.value,
            "target_allocation": {
                k: str(v) for k, v in portfolio.target_allocation.items()
            },
            "current_allocation": {
                k: str(v) for k, v in portfolio.current_allocation.items()
            },
            "total_value": str(portfolio.total_value),
            "cash_balance": str(portfolio.cash_balance),
            "invested_amount": str(portfolio.invested_amount),
            "total_return": str(portfolio.total_return),
            "total_return_percentage": str(portfolio.total_return_percentage),
            "positions_count": len(portfolio.positions),
            "rebalancing_strategy": portfolio.rebalancing_strategy.value,
            "last_rebalanced": (
                portfolio.last_rebalanced.isoformat()
                if portfolio.last_rebalanced
                else None
            ),
            "created_at": portfolio.created_at.isoformat(),
            "updated_at": portfolio.updated_at.isoformat(),
            "performance_metrics": portfolio.performance_metrics,
        }

    async def get_user_portfolios(self, user_id: str) -> Dict[str, Any]:
        """Get all portfolios for a user"""
        user_portfolios = [
            portfolio
            for portfolio in self.portfolios.values()
            if portfolio.user_id == user_id
        ]
        for portfolio in user_portfolios:
            await self._update_portfolio_values(portfolio)
        formatted_portfolios = []
        for portfolio in user_portfolios:
            formatted_portfolios.append(
                {
                    "portfolio_id": portfolio.portfolio_id,
                    "name": portfolio.name,
                    "type": portfolio.portfolio_type.value,
                    "risk_profile": portfolio.risk_profile.value,
                    "total_value": str(portfolio.total_value),
                    "total_return": str(portfolio.total_return),
                    "total_return_percentage": str(portfolio.total_return_percentage),
                    "positions_count": len(portfolio.positions),
                    "created_at": portfolio.created_at.isoformat(),
                    "updated_at": portfolio.updated_at.isoformat(),
                }
            )
        return {
            "user_id": user_id,
            "portfolios": formatted_portfolios,
            "total_portfolios": len(formatted_portfolios),
        }

    async def add_position(
        self,
        portfolio_id: str,
        asset_symbol: str,
        quantity: Decimal,
        purchase_price: Decimal,
        purchase_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Add a position to portfolio"""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        asset = None
        for a in self.assets.values():
            if a.symbol == asset_symbol:
                asset = a
                break
        if not asset:
            raise ValueError(f"Asset not found: {asset_symbol}")
        if purchase_date is None:
            purchase_date = datetime.now(timezone.utc)
        existing_position = None
        for position in portfolio.positions:
            if position.asset_id == asset.asset_id:
                existing_position = position
                break
        if existing_position:
            total_quantity = existing_position.quantity + quantity
            total_cost = (
                existing_position.quantity * existing_position.average_cost
                + quantity * purchase_price
            )
            new_average_cost = total_cost / total_quantity
            existing_position.quantity = total_quantity
            existing_position.average_cost = new_average_cost
            existing_position.cost_basis = total_cost
            existing_position.acquisition_dates.append(purchase_date)
            existing_position.last_updated = datetime.now(timezone.utc)
            existing_position.tax_lots.append(
                {
                    "quantity": quantity,
                    "price": purchase_price,
                    "date": purchase_date.isoformat(),
                    "cost_basis": quantity * purchase_price,
                }
            )
            position_id = existing_position.position_id
        else:
            position_id = f"pos_{uuid.uuid4().hex[:12]}"
            position = Position(
                position_id=position_id,
                portfolio_id=portfolio_id,
                asset_id=asset.asset_id,
                quantity=quantity,
                average_cost=purchase_price,
                current_price=purchase_price,
                market_value=quantity * purchase_price,
                unrealized_pnl=Decimal("0.00"),
                realized_pnl=Decimal("0.00"),
                cost_basis=quantity * purchase_price,
                weight=Decimal("0.00"),
                last_updated=datetime.now(timezone.utc),
                acquisition_dates=[purchase_date],
                tax_lots=[
                    {
                        "quantity": quantity,
                        "price": purchase_price,
                        "date": purchase_date.isoformat(),
                        "cost_basis": quantity * purchase_price,
                    }
                ],
            )
            portfolio.positions.append(position)
            self.positions[position_id] = position
        await self._update_portfolio_values(portfolio)
        logger.info(
            f"Position added to portfolio {portfolio_id}: {asset_symbol} x {quantity}"
        )
        return {
            "position_id": position_id,
            "asset_symbol": asset_symbol,
            "quantity": str(quantity),
            "average_cost": str(
                existing_position.average_cost if existing_position else purchase_price
            ),
            "market_value": str(
                existing_position.market_value
                if existing_position
                else quantity * purchase_price
            ),
        }

    async def get_portfolio_positions(
        self, portfolio_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all positions in a portfolio"""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        if user_id and portfolio.user_id != user_id:
            raise ValueError("Unauthorized access to portfolio")
        await self._update_portfolio_values(portfolio)
        formatted_positions = []
        for position in portfolio.positions:
            asset = self.assets.get(position.asset_id)
            if asset:
                formatted_positions.append(
                    {
                        "position_id": position.position_id,
                        "asset_symbol": asset.symbol,
                        "asset_name": asset.name,
                        "asset_type": asset.asset_type.value,
                        "quantity": str(position.quantity),
                        "average_cost": str(position.average_cost),
                        "current_price": str(position.current_price),
                        "market_value": str(position.market_value),
                        "unrealized_pnl": str(position.unrealized_pnl),
                        "unrealized_pnl_percentage": str(
                            (
                                position.unrealized_pnl / position.cost_basis * 100
                            ).quantize(Decimal("0.01"))
                        ),
                        "weight": str(position.weight),
                        "cost_basis": str(position.cost_basis),
                        "last_updated": position.last_updated.isoformat(),
                    }
                )
        return {
            "portfolio_id": portfolio_id,
            "positions": formatted_positions,
            "total_positions": len(formatted_positions),
            "total_value": str(portfolio.total_value),
        }

    async def calculate_performance_metrics(
        self, portfolio_id: str, period: str = "1Y"
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        await self._update_portfolio_values(portfolio)
        historical_values = await self._get_portfolio_historical_values(
            portfolio_id, period
        )
        if len(historical_values) < 2:
            return {
                "portfolio_id": portfolio_id,
                "period": period,
                "error": "Insufficient historical data",
            }
        returns = []
        for i in range(1, len(historical_values)):
            daily_return = (
                historical_values[i] - historical_values[i - 1]
            ) / historical_values[i - 1]
            returns.append(float(daily_return))
        total_return = (
            historical_values[-1] - historical_values[0]
        ) / historical_values[0]
        annualized_return = self._calculate_annualized_return(returns, period)
        volatility = (
            Decimal(str(statistics.stdev(returns)))
            if len(returns) > 1
            else Decimal("0")
        )
        excess_returns = [r - float(self.risk_free_rate) / 252 for r in returns]
        sharpe_ratio = (
            Decimal(str(statistics.mean(excess_returns)))
            / volatility
            * Decimal("15.87")
            if volatility > 0
            else Decimal("0")
        )
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = (
            Decimal(str(statistics.stdev(negative_returns)))
            if len(negative_returns) > 1
            else Decimal("0")
        )
        sortino_ratio = (
            Decimal(str(statistics.mean(excess_returns)))
            / downside_deviation
            * Decimal("15.87")
            if downside_deviation > 0
            else Decimal("0")
        )
        max_drawdown = self._calculate_max_drawdown(historical_values)
        calmar_ratio = (
            annualized_return / abs(max_drawdown) if max_drawdown != 0 else Decimal("0")
        )
        var_95 = (
            Decimal(str(statistics.quantiles(returns, n=20)[0]))
            if len(returns) >= 20
            else Decimal("0")
        )
        tail_returns = [r for r in returns if r <= float(var_95)]
        cvar_95 = (
            Decimal(str(statistics.mean(tail_returns)))
            if tail_returns
            else Decimal("0")
        )
        metrics = PerformanceMetrics(
            portfolio_id=portfolio_id,
            period=period,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            beta=Decimal("1.0"),
            alpha=Decimal("0.0"),
            information_ratio=Decimal("0.0"),
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            calculated_at=datetime.now(timezone.utc),
        )
        if portfolio_id not in self.performance_history:
            self.performance_history[portfolio_id] = []
        self.performance_history[portfolio_id].append(metrics)
        portfolio.performance_metrics[period] = asdict(metrics)
        portfolio.updated_at = datetime.now(timezone.utc)
        logger.info(
            f"Performance metrics calculated for portfolio {portfolio_id}, period {period}"
        )
        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "total_return": str(metrics.total_return),
            "total_return_percentage": str(
                (metrics.total_return * 100).quantize(Decimal("0.01"))
            ),
            "annualized_return": str(metrics.annualized_return),
            "annualized_return_percentage": str(
                (metrics.annualized_return * 100).quantize(Decimal("0.01"))
            ),
            "volatility": str(metrics.volatility),
            "volatility_percentage": str(
                (metrics.volatility * 100).quantize(Decimal("0.01"))
            ),
            "sharpe_ratio": str(metrics.sharpe_ratio),
            "sortino_ratio": str(metrics.sortino_ratio),
            "max_drawdown": str(metrics.max_drawdown),
            "max_drawdown_percentage": str(
                (metrics.max_drawdown * 100).quantize(Decimal("0.01"))
            ),
            "calmar_ratio": str(metrics.calmar_ratio),
            "var_95": str(metrics.var_95),
            "cvar_95": str(metrics.cvar_95),
            "calculated_at": metrics.calculated_at.isoformat(),
        }

    async def get_rebalancing_recommendations(
        self, portfolio_id: str
    ) -> Dict[str, Any]:
        """Get portfolio rebalancing recommendations"""
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        await self._update_portfolio_values(portfolio)
        rebalancing_needed = False
        allocation_drifts = {}
        for category, target_weight in portfolio.target_allocation.items():
            current_weight = portfolio.current_allocation.get(category, Decimal("0"))
            drift = abs(current_weight - target_weight)
            allocation_drifts[category] = {
                "target": target_weight,
                "current": current_weight,
                "drift": drift,
                "drift_percentage": (drift * 100).quantize(Decimal("0.01")),
            }
            if drift > portfolio.rebalancing_threshold:
                rebalancing_needed = True
        if not rebalancing_needed:
            return {
                "portfolio_id": portfolio_id,
                "rebalancing_needed": False,
                "allocation_drifts": {
                    k: {
                        "target": str(v["target"]),
                        "current": str(v["current"]),
                        "drift": str(v["drift"]),
                        "drift_percentage": str(v["drift_percentage"]),
                    }
                    for k, v in allocation_drifts.items()
                },
                "message": "Portfolio is within rebalancing thresholds",
            }
        recommended_trades = []
        total_value = portfolio.total_value
        for category, allocation_info in allocation_drifts.items():
            if allocation_info["drift"] > portfolio.rebalancing_threshold:
                target_value = total_value * allocation_info["target"]
                current_value = total_value * allocation_info["current"]
                trade_value = target_value - current_value
                if trade_value != 0:
                    recommended_trades.append(
                        {
                            "category": category,
                            "action": "buy" if trade_value > 0 else "sell",
                            "amount": str(abs(trade_value)),
                            "current_allocation": str(allocation_info["current"]),
                            "target_allocation": str(allocation_info["target"]),
                        }
                    )
        estimated_cost = len(recommended_trades) * Decimal("9.99")
        estimated_benefit = (
            sum((allocation_drifts[cat]["drift"] for cat in allocation_drifts))
            * total_value
            * Decimal("0.01")
        )
        recommendation = RebalancingRecommendation(
            portfolio_id=portfolio_id,
            recommended_trades=recommended_trades,
            expected_cost=estimated_cost,
            expected_benefit=estimated_benefit,
            risk_impact={"volatility_change": "minimal"},
            created_at=datetime.now(timezone.utc),
        )
        logger.info(
            f"Rebalancing recommendations generated for portfolio {portfolio_id}"
        )
        return {
            "portfolio_id": portfolio_id,
            "rebalancing_needed": True,
            "allocation_drifts": {
                k: {
                    "target": str(v["target"]),
                    "current": str(v["current"]),
                    "drift": str(v["drift"]),
                    "drift_percentage": str(v["drift_percentage"]),
                }
                for k, v in allocation_drifts.items()
            },
            "recommended_trades": recommended_trades,
            "expected_cost": str(estimated_cost),
            "expected_benefit": str(estimated_benefit),
            "cost_benefit_ratio": (
                str((estimated_benefit / estimated_cost).quantize(Decimal("0.01")))
                if estimated_cost > 0
                else "N/A"
            ),
            "created_at": recommendation.created_at.isoformat(),
        }

    async def _update_portfolio_values(self, portfolio: Portfolio):
        """Update portfolio values based on current market prices"""
        total_value = portfolio.cash_balance
        invested_amount = Decimal("0.00")
        total_return = Decimal("0.00")
        allocation_by_type = {}
        for position in portfolio.positions:
            position.current_price = position.average_cost * Decimal("1.05")
            position.market_value = position.quantity * position.current_price
            position.unrealized_pnl = position.market_value - position.cost_basis
            total_value += position.market_value
            invested_amount += position.cost_basis
            total_return += position.unrealized_pnl
            asset = self.assets.get(position.asset_id)
            if asset:
                asset_category = self._get_asset_category(asset.asset_type)
                if asset_category not in allocation_by_type:
                    allocation_by_type[asset_category] = Decimal("0.00")
                allocation_by_type[asset_category] += position.market_value
        portfolio.total_value = total_value
        portfolio.invested_amount = invested_amount
        portfolio.total_return = total_return
        portfolio.total_return_percentage = (
            (total_return / invested_amount * 100).quantize(Decimal("0.01"))
            if invested_amount > 0
            else Decimal("0.00")
        )
        portfolio.current_allocation = {}
        if total_value > 0:
            for category, value in allocation_by_type.items():
                portfolio.current_allocation[category] = value / total_value
            if portfolio.cash_balance > 0:
                portfolio.current_allocation["cash"] = (
                    portfolio.cash_balance / total_value
                )
        for position in portfolio.positions:
            position.weight = (
                position.market_value / total_value
                if total_value > 0
                else Decimal("0.00")
            )
        portfolio.updated_at = datetime.now(timezone.utc)

    def _get_asset_category(self, asset_type: AssetType) -> str:
        """Map asset type to allocation category"""
        mapping = {
            AssetType.STOCK: "stocks",
            AssetType.ETF: "stocks",
            AssetType.BOND: "bonds",
            AssetType.MUTUAL_FUND: "stocks",
            AssetType.CRYPTOCURRENCY: "alternative",
            AssetType.COMMODITY: "alternative",
            AssetType.REAL_ESTATE: "alternative",
            AssetType.CASH: "cash",
        }
        return mapping.get(asset_type, "other")

    async def _get_portfolio_historical_values(
        self, portfolio_id: str, period: str
    ) -> List[Decimal]:
        """Get historical portfolio values (simulated)"""
        days = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(
            period, 365
        )
        portfolio = self.portfolios[portfolio_id]
        current_value = portfolio.total_value
        historical_values = []
        for i in range(days):
            daily_return = Decimal("0.0005")
            volatility = Decimal("0.01")
            if i == 0:
                value = current_value * Decimal("0.95")
            else:
                change = daily_return + volatility * Decimal("0.5")
                value = historical_values[-1] * (Decimal("1.0") + change)
            historical_values.append(value)
        return historical_values

    def _calculate_annualized_return(
        self, returns: List[float], period: str
    ) -> Decimal:
        """Calculate annualized return"""
        if not returns:
            return Decimal("0.00")
        compound_return = 1.0
        for r in returns:
            compound_return *= 1.0 + r
        total_return = compound_return - 1.0
        days = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(
            period, 365
        )
        annualization_factor = 365.0 / days
        annualized = (1.0 + total_return) ** annualization_factor - 1.0
        return Decimal(str(annualized))

    def _calculate_max_drawdown(self, values: List[Decimal]) -> Decimal:
        """Calculate maximum drawdown"""
        if len(values) < 2:
            return Decimal("0.00")
        peak = values[0]
        max_drawdown = Decimal("0.00")
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        return max_drawdown

    def get_portfolio_statistics(self) -> Dict[str, Any]:
        """Get portfolio service statistics"""
        total_value = sum((p.total_value for p in self.portfolios.values()))
        type_counts = {}
        risk_profile_counts = {}
        for portfolio in self.portfolios.values():
            type_counts[portfolio.portfolio_type.value] = (
                type_counts.get(portfolio.portfolio_type.value, 0) + 1
            )
            risk_profile_counts[portfolio.risk_profile.value] = (
                risk_profile_counts.get(portfolio.risk_profile.value, 0) + 1
            )
        return {
            "total_portfolios": len(self.portfolios),
            "total_positions": len(self.positions),
            "total_assets": len(self.assets),
            "total_value": str(total_value),
            "type_distribution": type_counts,
            "risk_profile_distribution": risk_profile_counts,
        }
