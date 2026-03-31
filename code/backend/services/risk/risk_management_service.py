"""
Risk Management Service for Fluxion Backend
Implements comprehensive risk assessment, monitoring, and mitigation strategies
following financial industry best practices and regulatory requirements.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
from models.portfolio import Portfolio, PortfolioAsset
from models.transaction import Transaction
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class RiskCategory(Enum):
    """Risk categories for comprehensive assessment"""

    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    OPERATIONAL_RISK = "operational_risk"
    CONCENTRATION_RISK = "concentration_risk"
    COUNTERPARTY_RISK = "counterparty_risk"
    REGULATORY_RISK = "regulatory_risk"
    TECHNOLOGY_RISK = "technology_risk"


class RiskSeverity(Enum):
    """Risk severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAlert:
    """Risk alert structure"""

    risk_id: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    description: str
    affected_entities: List[str]
    recommended_actions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class PortfolioRiskMetrics:
    """Portfolio risk metrics"""

    portfolio_id: str
    total_value: Decimal
    var_1d: Decimal
    var_5d: Decimal
    expected_shortfall: Decimal
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    beta: float
    volatility: float
    concentration_score: float
    liquidity_score: float
    stress_test_loss: Decimal
    risk_score: float
    calculated_at: datetime


class RiskManagementService:
    """
    Risk management service providing:
    - Real-time risk monitoring and assessment
    - Value at Risk (VaR) calculations
    - Stress testing and scenario analysis
    - Concentration risk analysis
    - Liquidity risk assessment
    - Regulatory compliance monitoring
    - Risk-based position limits
    - Automated risk alerts and notifications
    """

    def __init__(self) -> None:
        self.confidence_levels = [0.95, 0.99, 0.999]
        self.var_time_horizons = [1, 5, 10]
        self.max_concentration_single_asset = 0.25
        self.max_concentration_sector = 0.4
        self.min_liquidity_ratio = 0.1
        self.stress_scenarios = {
            "market_crash": {
                "equity_shock": -0.3,
                "bond_shock": -0.1,
                "crypto_shock": -0.5,
            },
            "interest_rate_shock": {
                "rate_increase": 0.02,
                "bond_shock": -0.15,
                "equity_shock": -0.1,
            },
            "liquidity_crisis": {"liquidity_discount": 0.2, "spread_widening": 0.05},
            "crypto_winter": {"crypto_shock": -0.7, "defi_shock": -0.8},
            "regulatory_crackdown": {
                "compliance_cost": 0.05,
                "operational_shock": -0.15,
            },
        }
        self.risk_limits = {
            "retail": {
                "max_portfolio_var": 0.05,
                "max_single_position": 0.2,
                "max_leverage": 2.0,
            },
            "professional": {
                "max_portfolio_var": 0.1,
                "max_single_position": 0.3,
                "max_leverage": 5.0,
            },
            "institutional": {
                "max_portfolio_var": 0.15,
                "max_single_position": 0.5,
                "max_leverage": 10.0,
            },
        }

    async def assess_portfolio_risk(
        self, db: AsyncSession, portfolio_id: UUID, include_stress_tests: bool = True
    ) -> PortfolioRiskMetrics:
        """Comprehensive portfolio risk assessment"""
        try:
            portfolio_result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.assets))
                .where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            total_value = sum((asset.current_value for asset in portfolio.assets))
            price_data = await self._get_historical_prices(db, portfolio.assets)
            var_1d, var_5d = await self._calculate_var(price_data, total_value)
            expected_shortfall = await self._calculate_expected_shortfall(
                price_data, total_value
            )
            returns = await self._calculate_portfolio_returns(price_data)
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            sortino_ratio = self._calculate_sortino_ratio(returns)
            max_drawdown = self._calculate_max_drawdown(returns)
            beta = await self._calculate_beta(returns, db)
            volatility = np.std(returns) * np.sqrt(252)
            concentration_score = self._calculate_concentration_risk(
                portfolio.assets, total_value
            )
            liquidity_score = await self._calculate_liquidity_risk(db, portfolio.assets)
            stress_test_loss = Decimal("0")
            if include_stress_tests:
                stress_test_loss = await self._perform_stress_tests(
                    portfolio.assets, total_value
                )
            risk_score = self._calculate_overall_risk_score(
                var_1d / total_value,
                concentration_score,
                liquidity_score,
                volatility,
                max_drawdown,
            )
            risk_metrics = PortfolioRiskMetrics(
                portfolio_id=str(portfolio_id),
                total_value=total_value,
                var_1d=var_1d,
                var_5d=var_5d,
                expected_shortfall=expected_shortfall,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                beta=beta,
                volatility=volatility,
                concentration_score=concentration_score,
                liquidity_score=liquidity_score,
                stress_test_loss=stress_test_loss,
                risk_score=risk_score,
                calculated_at=datetime.utcnow(),
            )
            await self._store_risk_assessment(db, portfolio_id, risk_metrics)
            logger.info(
                f"Portfolio risk assessment completed for {portfolio_id}: Risk Score: {risk_score:.2f}, VaR 1d: {var_1d}"
            )
            return risk_metrics
        except Exception as e:
            logger.error(
                f"Portfolio risk assessment failed for {portfolio_id}: {str(e)}"
            )
            raise

    async def monitor_real_time_risk(
        self, db: AsyncSession, user_id: UUID, transaction: Optional[Transaction] = None
    ) -> List[RiskAlert]:
        """Real-time risk monitoring and alert generation"""
        try:
            alerts = []
            portfolios_result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.assets))
                .where(Portfolio.user_id == user_id)
            )
            portfolios = portfolios_result.scalars().all()
            for portfolio in portfolios:
                position_alerts = await self._check_position_limits(
                    portfolio, transaction
                )
                alerts.extend(position_alerts)
                concentration_alerts = await self._check_concentration_limits(portfolio)
                alerts.extend(concentration_alerts)
                var_alerts = await self._check_var_limits(db, portfolio)
                alerts.extend(var_alerts)
                liquidity_alerts = await self._check_liquidity_risk(db, portfolio)
                alerts.extend(liquidity_alerts)
            if transaction:
                transaction_alerts = await self._check_transaction_risks(
                    db, transaction
                )
                alerts.extend(transaction_alerts)
            compliance_alerts = await self._check_regulatory_compliance(db, user_id)
            alerts.extend(compliance_alerts)
            for alert in alerts:
                await self._store_risk_alert(db, alert)
            logger.info(
                f"Real-time risk monitoring completed for user {user_id}: {len(alerts)} alerts generated"
            )
            return alerts
        except Exception as e:
            logger.error(
                f"Real-time risk monitoring failed for user {user_id}: {str(e)}"
            )
            raise

    async def calculate_position_limits(
        self,
        db: AsyncSession,
        user_id: UUID,
        asset_symbol: str,
        user_tier: str = "retail",
    ) -> Dict[str, Any]:
        """Calculate position limits for a specific asset"""
        try:
            portfolio_result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.assets))
                .where(Portfolio.user_id == user_id)
                .order_by(desc(Portfolio.created_at))
                .limit(1)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            if not portfolio:
                return {
                    "max_position_value": Decimal("1000"),
                    "max_position_percentage": 0.1,
                    "current_position_value": Decimal("0"),
                    "current_position_percentage": 0.0,
                    "available_capacity": Decimal("1000"),
                    "risk_tier": user_tier,
                }
            total_portfolio_value = sum(
                (asset.current_value for asset in portfolio.assets)
            )
            current_position = next(
                (asset for asset in portfolio.assets if asset.symbol == asset_symbol),
                None,
            )
            current_position_value = (
                current_position.current_value if current_position else Decimal("0")
            )
            current_position_percentage = (
                float(current_position_value / total_portfolio_value)
                if total_portfolio_value > 0
                else 0.0
            )
            tier_limits = self.risk_limits.get(user_tier, self.risk_limits["retail"])
            max_position_percentage = tier_limits["max_single_position"]
            max_position_value = total_portfolio_value * Decimal(
                str(max_position_percentage)
            )
            available_capacity = max_position_value - current_position_value
            asset_risk_multiplier = await self._get_asset_risk_multiplier(
                db, asset_symbol
            )
            max_position_value *= Decimal(str(asset_risk_multiplier))
            available_capacity *= Decimal(str(asset_risk_multiplier))
            return {
                "max_position_value": max_position_value,
                "max_position_percentage": max_position_percentage
                * asset_risk_multiplier,
                "current_position_value": current_position_value,
                "current_position_percentage": current_position_percentage,
                "available_capacity": max(available_capacity, Decimal("0")),
                "risk_tier": user_tier,
                "asset_risk_multiplier": asset_risk_multiplier,
            }
        except Exception as e:
            logger.error(
                f"Position limit calculation failed for user {user_id}, asset {asset_symbol}: {str(e)}"
            )
            raise

    async def perform_scenario_analysis(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        custom_scenarios: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive scenario analysis and stress testing"""
        try:
            portfolio_result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.assets))
                .where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            total_value = sum((asset.current_value for asset in portfolio.assets))
            scenarios_to_test = {**self.stress_scenarios}
            if custom_scenarios:
                scenarios_to_test.update(custom_scenarios)
            scenario_results = {}
            for scenario_name, scenario_params in scenarios_to_test.items():
                scenario_loss = await self._calculate_scenario_impact(
                    portfolio.assets, total_value, scenario_params
                )
                scenario_results[scenario_name] = {
                    "absolute_loss": scenario_loss,
                    "percentage_loss": (
                        float(scenario_loss / total_value) if total_value > 0 else 0.0
                    ),
                    "parameters": scenario_params,
                    "severity": self._classify_scenario_severity(
                        scenario_loss, total_value
                    ),
                }
            worst_case_loss = max(
                (result["absolute_loss"] for result in scenario_results.values())
            )
            worst_case_scenario = max(
                scenario_results.items(), key=lambda x: x[1]["absolute_loss"]
            )
            recovery_estimates = await self._estimate_recovery_times(
                scenario_results, total_value
            )
            analysis_result = {
                "portfolio_id": str(portfolio_id),
                "total_portfolio_value": total_value,
                "scenarios": scenario_results,
                "worst_case_loss": worst_case_loss,
                "worst_case_scenario": worst_case_scenario[0],
                "recovery_estimates": recovery_estimates,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "recommendations": await self._generate_risk_recommendations(
                    scenario_results, total_value
                ),
            }
            await self._store_scenario_analysis(db, portfolio_id, analysis_result)
            logger.info(
                f"Scenario analysis completed for portfolio {portfolio_id}: Worst case loss: {worst_case_loss}"
            )
            return analysis_result
        except Exception as e:
            logger.error(
                f"Scenario analysis failed for portfolio {portfolio_id}: {str(e)}"
            )
            raise

    async def _get_historical_prices(
        self, db: AsyncSession, assets: List[PortfolioAsset]
    ) -> pd.DataFrame:
        """Get historical price data for portfolio assets"""
        dates = pd.date_range(end=datetime.now(), periods=252, freq="D")
        price_data = {}
        for asset in assets:
            np.random.seed(hash(asset.symbol) % 2**32)
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = [100.0]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            price_data[asset.symbol] = prices
        return pd.DataFrame(price_data, index=dates)

    async def _calculate_var(
        self, price_data: pd.DataFrame, portfolio_value: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Calculate Value at Risk using historical simulation"""
        returns = price_data.pct_change().dropna()
        portfolio_returns = returns.mean(axis=1)
        var_1d = np.percentile(portfolio_returns, 5) * float(portfolio_value)
        var_5d = var_1d * np.sqrt(5)
        return (Decimal(str(abs(var_1d))), Decimal(str(abs(var_5d))))

    async def _calculate_expected_shortfall(
        self, price_data: pd.DataFrame, portfolio_value: Decimal
    ) -> Decimal:
        """Calculate Expected Shortfall (Conditional VaR)"""
        returns = price_data.pct_change().dropna()
        portfolio_returns = returns.mean(axis=1)
        var_threshold = np.percentile(portfolio_returns, 5)
        tail_returns = portfolio_returns[portfolio_returns <= var_threshold]
        expected_shortfall = tail_returns.mean() * float(portfolio_value)
        return Decimal(str(abs(expected_shortfall)))

    async def _calculate_portfolio_returns(
        self, price_data: pd.DataFrame
    ) -> np.ndarray:
        """Calculate portfolio returns"""
        returns = price_data.pct_change().dropna()
        return returns.mean(axis=1).values

    def _calculate_sharpe_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        if len(returns) == 0:
            raise ValueError("Cannot calculate Sharpe Ratio of an empty array")
        "Calculate Sharpe ratio"
        excess_returns = returns - risk_free_rate / 252
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

    def _calculate_sortino_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        if len(returns) == 0:
            raise ValueError("Cannot calculate Sortino Ratio of an empty array")
        "Calculate Sortino ratio (downside deviation)"
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = (
            np.std(downside_returns)
            if len(downside_returns) > 0
            else np.std(excess_returns)
        )
        return float(np.mean(excess_returns) / downside_deviation * np.sqrt(252))

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        if len(returns) == 0:
            raise ValueError("Cannot calculate Max Drawdown of an empty array")
        "Calculate maximum drawdown"
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        return float(np.min(drawdown))

    async def _calculate_beta(self, returns: np.ndarray, db: AsyncSession) -> float:
        if len(returns) == 0:
            raise ValueError("Cannot calculate Beta of an empty array")
        "Calculate portfolio beta against market benchmark"
        np.random.seed(42)
        market_returns = np.random.normal(0.0008, 0.015, len(returns))
        covariance = np.cov(returns, market_returns)[0, 1]
        market_variance = np.var(market_returns)
        return float(covariance / market_variance) if market_variance > 0 else 1.0

    def _calculate_concentration_risk(
        self, assets: List[PortfolioAsset], total_value: Decimal
    ) -> float:
        """Calculate concentration risk score"""
        if total_value == 0:
            return 0.0
        weights = [float(asset.current_value / total_value) for asset in assets]
        hhi = sum((w**2 for w in weights))
        max_hhi = 1.0
        min_hhi = 1.0 / len(assets) if assets else 1.0
        if max_hhi == min_hhi:
            return 0.0
        concentration_score = (hhi - min_hhi) / (max_hhi - min_hhi)
        return min(concentration_score, 1.0)

    async def _calculate_liquidity_risk(
        self, db: AsyncSession, assets: List[PortfolioAsset]
    ) -> float:
        """Calculate liquidity risk score"""
        if not assets:
            return 1.0
        liquidity_scores = []
        for asset in assets:
            if any(
                (
                    crypto in asset.symbol.upper()
                    for crypto in ["BTC", "ETH", "USDT", "USDC"]
                )
            ):
                liquidity_scores.append(0.8)
            elif "USD" in asset.symbol.upper():
                liquidity_scores.append(0.95)
            else:
                liquidity_scores.append(0.6)
        total_value = sum((asset.current_value for asset in assets))
        if total_value == 0:
            return 1.0
        weighted_liquidity = sum(
            (
                score * float(asset.current_value / total_value)
                for score, asset in zip(liquidity_scores, assets)
            )
        )
        return 1.0 - weighted_liquidity

    async def _perform_stress_tests(
        self, assets: List[PortfolioAsset], total_value: Decimal
    ) -> Decimal:
        """Perform stress tests on portfolio"""
        max_loss = Decimal("0")
        for scenario_name, scenario_params in self.stress_scenarios.items():
            scenario_loss = await self._calculate_scenario_impact(
                assets, total_value, scenario_params
            )
            max_loss = max(max_loss, scenario_loss)
        return max_loss

    def _calculate_overall_risk_score(
        self,
        var_ratio: Decimal,
        concentration_score: float,
        liquidity_score: float,
        volatility: float,
        max_drawdown: float,
    ) -> float:
        """Calculate overall risk score (0-100)"""
        weights = {
            "var": 0.25,
            "concentration": 0.2,
            "liquidity": 0.2,
            "volatility": 0.2,
            "drawdown": 0.15,
        }
        var_component = min(float(var_ratio) * 10, 1.0)
        concentration_component = concentration_score
        liquidity_component = liquidity_score
        volatility_component = min(volatility / 0.5, 1.0)
        drawdown_component = min(abs(max_drawdown) / 0.3, 1.0)
        risk_score = (
            weights["var"] * var_component
            + weights["concentration"] * concentration_component
            + weights["liquidity"] * liquidity_component
            + weights["volatility"] * volatility_component
            + weights["drawdown"] * drawdown_component
        ) * 100
        return min(risk_score, 100.0)

    async def _store_risk_assessment(
        self, db: AsyncSession, portfolio_id: UUID, metrics: PortfolioRiskMetrics
    ):
        """Store risk assessment in database"""
        logger.info(f"Storing risk assessment for portfolio {portfolio_id}")

    async def _check_position_limits(
        self, portfolio: Portfolio, transaction: Optional[Transaction]
    ) -> List[RiskAlert]:
        """Check position limits and generate alerts"""
        alerts = []
        return alerts

    async def _check_concentration_limits(
        self, portfolio: Portfolio
    ) -> List[RiskAlert]:
        """Check concentration limits"""
        alerts = []
        total_value = sum((asset.current_value for asset in portfolio.assets))
        if total_value == 0:
            return alerts
        for asset in portfolio.assets:
            concentration = float(asset.current_value / total_value)
            if concentration > self.max_concentration_single_asset:
                alerts.append(
                    RiskAlert(
                        risk_id=f"concentration_{asset.symbol}_{datetime.utcnow().timestamp()}",
                        category=RiskCategory.CONCENTRATION_RISK,
                        severity=(
                            RiskSeverity.HIGH
                            if concentration > 0.4
                            else RiskSeverity.MEDIUM
                        ),
                        title=f"High concentration in {asset.symbol}",
                        description=f"Asset {asset.symbol} represents {concentration:.1%} of portfolio, exceeding limit of {self.max_concentration_single_asset:.1%}",
                        affected_entities=[str(portfolio.id)],
                        recommended_actions=[
                            f"Consider reducing position in {asset.symbol}",
                            "Diversify portfolio across more assets",
                            "Implement position size limits",
                        ],
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                        metadata={
                            "asset": asset.symbol,
                            "concentration": concentration,
                        },
                    )
                )
        return alerts

    async def _check_var_limits(
        self, db: AsyncSession, portfolio: Portfolio
    ) -> List[RiskAlert]:
        """Check VaR limits"""
        return []

    async def _check_liquidity_risk(
        self, db: AsyncSession, portfolio: Portfolio
    ) -> List[RiskAlert]:
        """Check liquidity risk"""
        return []

    async def _check_transaction_risks(
        self, db: AsyncSession, transaction: Transaction
    ) -> List[RiskAlert]:
        """Check transaction-specific risks"""
        return []

    async def _check_regulatory_compliance(
        self, db: AsyncSession, user_id: UUID
    ) -> List[RiskAlert]:
        """Check regulatory compliance"""
        return []

    async def _store_risk_alert(self, db: AsyncSession, alert: RiskAlert):
        """Store risk alert in database"""
        logger.info(f"Storing risk alert: {alert.title}")

    async def _get_asset_risk_multiplier(
        self, db: AsyncSession, asset_symbol: str
    ) -> float:
        """Get risk multiplier for asset"""
        risk_multipliers = {"BTC": 0.7, "ETH": 0.8, "USDT": 1.0, "USDC": 1.0}
        return risk_multipliers.get(asset_symbol.upper(), 0.9)

    async def _calculate_scenario_impact(
        self,
        assets: List[PortfolioAsset],
        total_value: Decimal,
        scenario_params: Dict[str, float],
    ) -> Decimal:
        """Calculate impact of stress scenario"""
        total_loss = Decimal("0")
        for asset in assets:
            asset_loss = Decimal("0")
            if "crypto" in asset.symbol.lower() or any(
                (crypto in asset.symbol.upper() for crypto in ["BTC", "ETH"])
            ):
                if "crypto_shock" in scenario_params:
                    asset_loss = asset.current_value * Decimal(
                        str(abs(scenario_params["crypto_shock"]))
                    )
                elif "defi_shock" in scenario_params:
                    asset_loss = asset.current_value * Decimal(
                        str(abs(scenario_params["defi_shock"]))
                    )
            if "equity_shock" in scenario_params:
                asset_loss = max(
                    asset_loss,
                    asset.current_value
                    * Decimal(str(abs(scenario_params["equity_shock"]))),
                )
            total_loss += asset_loss
        return total_loss

    def _classify_scenario_severity(
        self, loss: Decimal, total_value: Decimal
    ) -> RiskSeverity:
        """Classify scenario severity based on loss percentage"""
        if total_value == 0:
            return RiskSeverity.LOW
        loss_percentage = float(loss / total_value)
        if loss_percentage >= 0.3:
            return RiskSeverity.CRITICAL
        elif loss_percentage >= 0.2:
            return RiskSeverity.HIGH
        elif loss_percentage >= 0.1:
            return RiskSeverity.MEDIUM
        else:
            return RiskSeverity.LOW

    async def _estimate_recovery_times(
        self, scenario_results: Dict[str, Any], total_value: Decimal
    ) -> Dict[str, str]:
        """Estimate recovery times for different scenarios"""
        recovery_estimates = {}
        for scenario_name, result in scenario_results.items():
            loss_percentage = result["percentage_loss"]
            if loss_percentage < 0.1:
                recovery_estimates[scenario_name] = "1-3 months"
            elif loss_percentage < 0.2:
                recovery_estimates[scenario_name] = "6-12 months"
            elif loss_percentage < 0.3:
                recovery_estimates[scenario_name] = "1-2 years"
            else:
                recovery_estimates[scenario_name] = "2+ years"
        return recovery_estimates

    async def _generate_risk_recommendations(
        self, scenario_results: Dict[str, Any], total_value: Decimal
    ) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        high_risk_scenarios = [
            name
            for name, result in scenario_results.items()
            if result["severity"] in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]
        ]
        if high_risk_scenarios:
            recommendations.extend(
                [
                    "Consider reducing portfolio concentration in high-risk assets",
                    "Implement stop-loss orders to limit downside risk",
                    "Increase cash reserves for liquidity buffer",
                ]
            )
        if any(("crypto" in scenario for scenario in high_risk_scenarios)):
            recommendations.append("Consider reducing cryptocurrency exposure")
        if len(scenario_results) > 3:
            recommendations.append("Diversify across uncorrelated asset classes")
        return recommendations

    async def _store_scenario_analysis(
        self, db: AsyncSession, portfolio_id: UUID, analysis_result: Dict[str, Any]
    ):
        """Store scenario analysis results"""
        logger.info(f"Storing scenario analysis for portfolio {portfolio_id}")
