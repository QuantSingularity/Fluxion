"""
Risk management models for Fluxion backend
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from models.base import AuditMixin, BaseModel, TimestampMixin
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


class RiskLevel(enum.Enum):
    """Risk levels"""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class RiskCategory(enum.Enum):
    """Risk categories"""

    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    OPERATIONAL_RISK = "operational_risk"
    COMPLIANCE_RISK = "compliance_risk"
    COUNTERPARTY_RISK = "counterparty_risk"
    CONCENTRATION_RISK = "concentration_risk"
    SMART_CONTRACT_RISK = "smart_contract_risk"


class RiskAlertType(enum.Enum):
    """Risk alert types"""

    POSITION_LIMIT_BREACH = "position_limit_breach"
    VAR_LIMIT_BREACH = "var_limit_breach"
    CONCENTRATION_LIMIT = "concentration_limit"
    LIQUIDITY_SHORTAGE = "liquidity_shortage"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    DRAWDOWN_LIMIT = "drawdown_limit"
    LEVERAGE_LIMIT = "leverage_limit"


class RiskAlertStatus(enum.Enum):
    """Risk alert status"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RiskProfile(BaseModel, TimestampMixin, AuditMixin):
    """User risk profile model"""

    __tablename__ = "risk_profiles"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )

    # Risk tolerance
    risk_tolerance = Column(
        Enum(RiskLevel),
        default=RiskLevel.MEDIUM,
        nullable=False,
        comment="Risk tolerance level",
    )
    risk_capacity = Column(
        Enum(RiskLevel),
        default=RiskLevel.MEDIUM,
        nullable=False,
        comment="Risk capacity level",
    )

    # Investment profile
    investment_experience = Column(
        String(50), nullable=True, comment="Investment experience level"
    )
    investment_horizon = Column(
        String(50), nullable=True, comment="Investment time horizon"
    )
    investment_objectives = Column(JSON, nullable=True, comment="Investment objectives")

    # Financial information
    annual_income = Column(DECIMAL(20, 8), nullable=True, comment="Annual income")
    net_worth = Column(DECIMAL(20, 8), nullable=True, comment="Net worth")
    liquid_assets = Column(DECIMAL(20, 8), nullable=True, comment="Liquid assets")

    # Risk limits
    max_portfolio_risk = Column(
        Float, nullable=True, comment="Maximum portfolio risk percentage"
    )
    max_single_asset_allocation = Column(
        Float, nullable=True, comment="Maximum single asset allocation"
    )
    max_sector_allocation = Column(
        Float, nullable=True, comment="Maximum sector allocation"
    )
    max_drawdown_tolerance = Column(
        Float, nullable=True, comment="Maximum drawdown tolerance"
    )

    # VaR limits
    daily_var_limit = Column(DECIMAL(20, 8), nullable=True, comment="Daily VaR limit")
    weekly_var_limit = Column(DECIMAL(20, 8), nullable=True, comment="Weekly VaR limit")
    monthly_var_limit = Column(
        DECIMAL(20, 8), nullable=True, comment="Monthly VaR limit"
    )

    # Leverage limits
    max_leverage = Column(
        Float, default=1.0, nullable=False, comment="Maximum leverage ratio"
    )
    margin_requirement = Column(
        Float, nullable=True, comment="Margin requirement percentage"
    )

    # Questionnaire responses
    questionnaire_responses = Column(
        JSON, nullable=True, comment="Risk questionnaire responses"
    )
    questionnaire_score = Column(
        Integer, nullable=True, comment="Risk questionnaire score"
    )
    questionnaire_date = Column(
        DateTime(timezone=True), nullable=True, comment="Questionnaire completion date"
    )

    # Profile status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Profile active status"
    )
    last_reviewed_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last review timestamp"
    )
    next_review_due = Column(
        DateTime(timezone=True), nullable=True, comment="Next review due date"
    )

    # Relationships
    user = relationship("User", back_populates="risk_profiles")
    assessments = relationship(
        "RiskAssessment", back_populates="risk_profile", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "RiskAlert", back_populates="risk_profile", cascade="all, delete-orphan"
    )

    def needs_review(self) -> bool:
        """Check if risk profile needs review"""
        if self.next_review_due:
            return datetime.now(timezone.utc) >= self.next_review_due
        return False

    def calculate_risk_score(self) -> int:
        """Calculate overall risk score"""
        # Simple scoring based on tolerance and capacity
        tolerance_scores = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.VERY_HIGH: 5,
            RiskLevel.CRITICAL: 6,
        }

        tolerance_score = tolerance_scores.get(self.risk_tolerance, 3)
        capacity_score = tolerance_scores.get(self.risk_capacity, 3)
        questionnaire_score = self.questionnaire_score or 50

        # Weighted average
        return int(
            (tolerance_score * 30 + capacity_score * 30 + questionnaire_score * 40)
            / 100
        )


class RiskAssessment(BaseModel, TimestampMixin, AuditMixin):
    """Risk assessment model"""

    __tablename__ = "risk_assessments"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=True,
        comment="Portfolio ID",
    )
    risk_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("risk_profiles.id"),
        nullable=False,
        comment="Risk profile ID",
    )

    # Assessment details
    assessment_type = Column(String(50), nullable=False, comment="Assessment type")
    assessment_date = Column(
        DateTime(timezone=True), nullable=False, comment="Assessment date"
    )

    # Overall risk metrics
    overall_risk_level = Column(
        Enum(RiskLevel), nullable=False, comment="Overall risk level"
    )
    overall_risk_score = Column(Float, nullable=False, comment="Overall risk score")
    confidence_level = Column(Float, nullable=True, comment="Confidence level")

    # Risk breakdown by category
    market_risk_score = Column(Float, nullable=True, comment="Market risk score")
    credit_risk_score = Column(Float, nullable=True, comment="Credit risk score")
    liquidity_risk_score = Column(Float, nullable=True, comment="Liquidity risk score")
    operational_risk_score = Column(
        Float, nullable=True, comment="Operational risk score"
    )
    compliance_risk_score = Column(
        Float, nullable=True, comment="Compliance risk score"
    )

    # VaR calculations
    daily_var = Column(DECIMAL(20, 8), nullable=True, comment="Daily Value at Risk")
    weekly_var = Column(DECIMAL(20, 8), nullable=True, comment="Weekly Value at Risk")
    monthly_var = Column(DECIMAL(20, 8), nullable=True, comment="Monthly Value at Risk")
    var_confidence_level = Column(
        Float, default=95.0, nullable=False, comment="VaR confidence level"
    )

    # Stress testing
    stress_test_results = Column(JSON, nullable=True, comment="Stress test results")
    scenario_analysis = Column(JSON, nullable=True, comment="Scenario analysis results")

    # Portfolio metrics
    portfolio_volatility = Column(Float, nullable=True, comment="Portfolio volatility")
    portfolio_beta = Column(Float, nullable=True, comment="Portfolio beta")
    sharpe_ratio = Column(Float, nullable=True, comment="Sharpe ratio")
    max_drawdown = Column(Float, nullable=True, comment="Maximum drawdown")

    # Concentration metrics
    concentration_risk = Column(
        Float, nullable=True, comment="Concentration risk score"
    )
    largest_position_weight = Column(
        Float, nullable=True, comment="Largest position weight"
    )
    top_5_positions_weight = Column(
        Float, nullable=True, comment="Top 5 positions weight"
    )

    # Correlation analysis
    correlation_matrix = Column(JSON, nullable=True, comment="Asset correlation matrix")
    correlation_breakdown = Column(JSON, nullable=True, comment="Correlation breakdown")

    # Risk factors
    risk_factors = Column(JSON, nullable=True, comment="Identified risk factors")
    risk_recommendations = Column(
        JSON, nullable=True, comment="Risk mitigation recommendations"
    )

    # Model information
    model_version = Column(String(20), nullable=True, comment="Risk model version")
    calculation_method = Column(
        String(50), nullable=True, comment="Calculation methodology"
    )

    # Relationships
    user = relationship("User")
    portfolio = relationship("Portfolio")
    risk_profile = relationship("RiskProfile", back_populates="assessments")

    def is_high_risk(self) -> bool:
        """Check if assessment indicates high risk"""
        return self.overall_risk_level in [
            RiskLevel.HIGH,
            RiskLevel.VERY_HIGH,
            RiskLevel.CRITICAL,
        ]

    def exceeds_var_limit(self, limit: Decimal, period: str = "daily") -> bool:
        """Check if VaR exceeds limit"""
        var_value = getattr(self, f"{period}_var")
        return var_value is not None and var_value > limit

    # Indexes
    __table_args__ = (
        Index("idx_risk_assessments_user_date", "user_id", "assessment_date"),
        Index("idx_risk_assessments_portfolio", "portfolio_id"),
        Index("idx_risk_assessments_risk_level", "overall_risk_level"),
        Index("idx_risk_assessments_type", "assessment_type"),
    )


class RiskAlert(BaseModel, TimestampMixin, AuditMixin):
    """Risk alert model"""

    __tablename__ = "risk_alerts"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=True,
        comment="Portfolio ID",
    )
    risk_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("risk_profiles.id"),
        nullable=True,
        comment="Risk profile ID",
    )
    risk_assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("risk_assessments.id"),
        nullable=True,
        comment="Risk assessment ID",
    )

    # Alert details
    alert_type = Column(Enum(RiskAlertType), nullable=False, comment="Alert type")
    risk_category = Column(Enum(RiskCategory), nullable=False, comment="Risk category")
    severity = Column(Enum(RiskLevel), nullable=False, comment="Alert severity")
    status = Column(
        Enum(RiskAlertStatus),
        default=RiskAlertStatus.ACTIVE,
        nullable=False,
        comment="Alert status",
    )

    # Alert content
    title = Column(String(200), nullable=False, comment="Alert title")
    description = Column(Text, nullable=False, comment="Alert description")
    recommendation = Column(
        Text, nullable=True, comment="Risk mitigation recommendation"
    )

    # Threshold information
    threshold_value = Column(DECIMAL(20, 8), nullable=True, comment="Threshold value")
    current_value = Column(DECIMAL(20, 8), nullable=True, comment="Current value")
    breach_percentage = Column(
        Float, nullable=True, comment="Threshold breach percentage"
    )

    # Alert context
    affected_assets = Column(JSON, nullable=True, comment="Affected assets")
    risk_metrics = Column(JSON, nullable=True, comment="Risk metrics at alert time")

    # Timing
    triggered_at = Column(
        DateTime(timezone=True), nullable=False, comment="Alert trigger timestamp"
    )
    acknowledged_at = Column(
        DateTime(timezone=True), nullable=True, comment="Acknowledgment timestamp"
    )
    resolved_at = Column(
        DateTime(timezone=True), nullable=True, comment="Resolution timestamp"
    )

    # Response
    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who acknowledged",
    )
    response_notes = Column(Text, nullable=True, comment="Response notes")
    actions_taken = Column(JSON, nullable=True, comment="Actions taken")

    # Escalation
    escalated = Column(Boolean, default=False, nullable=False, comment="Escalated flag")
    escalated_at = Column(
        DateTime(timezone=True), nullable=True, comment="Escalation timestamp"
    )

    # Relationships
    user = relationship("User")
    portfolio = relationship("Portfolio")
    risk_profile = relationship("RiskProfile", back_populates="alerts")
    risk_assessment = relationship("RiskAssessment")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])

    def is_active(self) -> bool:
        """Check if alert is active"""
        return self.status == RiskAlertStatus.ACTIVE

    def is_overdue(self, hours: int = 4) -> bool:
        """Check if alert response is overdue"""
        if self.is_active():
            delta = datetime.now(timezone.utc) - self.triggered_at
            return delta.total_seconds() > (hours * 3600)
        return False

    def get_breach_severity(self) -> str:
        """Get breach severity description"""
        if self.breach_percentage is None:
            return "unknown"
        elif self.breach_percentage < 10:
            return "minor"
        elif self.breach_percentage < 25:
            return "moderate"
        elif self.breach_percentage < 50:
            return "significant"
        else:
            return "severe"

    # Indexes
    __table_args__ = (
        Index("idx_risk_alerts_user_triggered", "user_id", "triggered_at"),
        Index("idx_risk_alerts_status_severity", "status", "severity"),
        Index("idx_risk_alerts_type_category", "alert_type", "risk_category"),
        Index("idx_risk_alerts_portfolio", "portfolio_id"),
        Index("idx_risk_alerts_escalated", "escalated"),
    )


class RiskLimit(BaseModel, TimestampMixin, AuditMixin):
    """Risk limit model"""

    __tablename__ = "risk_limits"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="User ID"
    )
    portfolio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=True,
        comment="Portfolio ID",
    )

    # Limit details
    limit_type = Column(String(50), nullable=False, comment="Limit type")
    limit_category = Column(Enum(RiskCategory), nullable=False, comment="Risk category")

    # Limit values
    limit_value = Column(DECIMAL(20, 8), nullable=False, comment="Limit value")
    warning_threshold = Column(
        DECIMAL(20, 8), nullable=True, comment="Warning threshold"
    )
    currency = Column(String(10), nullable=True, comment="Currency for monetary limits")

    # Limit scope
    asset_symbol = Column(
        String(20), nullable=True, comment="Asset symbol (for asset-specific limits)"
    )
    asset_category = Column(String(50), nullable=True, comment="Asset category")

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Limit active status"
    )
    is_breached = Column(
        Boolean, default=False, nullable=False, comment="Limit breach status"
    )

    # Monitoring
    current_value = Column(DECIMAL(20, 8), nullable=True, comment="Current value")
    utilization_percentage = Column(
        Float, nullable=True, comment="Limit utilization percentage"
    )
    last_checked_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last check timestamp"
    )

    # Breach information
    first_breach_at = Column(
        DateTime(timezone=True), nullable=True, comment="First breach timestamp"
    )
    last_breach_at = Column(
        DateTime(timezone=True), nullable=True, comment="Last breach timestamp"
    )
    breach_count = Column(
        Integer, default=0, nullable=False, comment="Total breach count"
    )

    # Relationships
    user = relationship("User")
    portfolio = relationship("Portfolio")

    def calculate_utilization(self) -> Optional[float]:
        """Calculate limit utilization percentage"""
        if self.current_value is not None and self.limit_value > 0:
            return float((self.current_value / self.limit_value) * 100)
        return None

    def is_warning_level(self) -> bool:
        """Check if at warning threshold"""
        if self.warning_threshold and self.current_value:
            return self.current_value >= self.warning_threshold
        return False

    def update_breach_status(self) -> None:
        """Update breach status based on current value"""
        if self.current_value and self.current_value > self.limit_value:
            if not self.is_breached:
                self.first_breach_at = datetime.now(timezone.utc)
                self.breach_count += 1
            self.is_breached = True
            self.last_breach_at = datetime.now(timezone.utc)
        else:
            self.is_breached = False

    # Indexes
    __table_args__ = (
        Index("idx_risk_limits_user_type", "user_id", "limit_type"),
        Index("idx_risk_limits_portfolio", "portfolio_id"),
        Index("idx_risk_limits_breached", "is_breached"),
        Index("idx_risk_limits_active", "is_active"),
    )


class RiskScenario(BaseModel, TimestampMixin, AuditMixin):
    """Risk scenario model for stress testing"""

    __tablename__ = "risk_scenarios"

    # Scenario details
    name = Column(String(100), nullable=False, comment="Scenario name")
    description = Column(Text, nullable=True, comment="Scenario description")
    scenario_type = Column(String(50), nullable=False, comment="Scenario type")

    # Scenario parameters
    parameters = Column(JSON, nullable=False, comment="Scenario parameters")
    market_shocks = Column(JSON, nullable=True, comment="Market shock parameters")

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Scenario active status"
    )

    # Relationships - scenarios can be used in multiple assessments

    def apply_to_portfolio(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply scenario to portfolio data"""
        # This would contain the logic to apply scenario shocks
        # to portfolio positions and calculate stressed values

    # Indexes
    __table_args__ = (
        Index("idx_risk_scenarios_type", "scenario_type"),
        Index("idx_risk_scenarios_active", "is_active"),
    )
