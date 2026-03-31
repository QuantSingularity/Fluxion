import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnalyticsType(Enum):
    """Types of analytics available in the Fluxion Backend."""

    USER_ANALYTICS = "user_analytics"
    TRANSACTION_ANALYTICS = "transaction_analytics"
    PORTFOLIO_ANALYTICS = "portfolio_analytics"
    RISK_ANALYTICS = "risk_analytics"
    PERFORMANCE_ANALYTICS = "performance_analytics"
    MARKET_ANALYTICS = "market_analytics"
    COMPLIANCE_ANALYTICS = "compliance_analytics"
    OPERATIONAL_ANALYTICS = "operational_analytics"


class ReportType(Enum):
    """Types of reports that can be generated."""

    DASHBOARD = "dashboard"
    SUMMARY = "summary"
    DETAILED = "detailed"
    REGULATORY = "regulatory"
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    CUSTOM = "custom"


class TimeFrame(Enum):
    """Time frame options for analytics calculations."""

    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class MetricType(Enum):
    """Types of metrics calculation."""

    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MEDIAN = "median"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    GROWTH_RATE = "growth_rate"
    VOLATILITY = "volatility"


@dataclass
class AnalyticsMetric:
    """Individual analytics metric data structure."""

    metric_id: str = field(default_factory=lambda: f"metric_{uuid.uuid4().hex[:8]}")
    name: str
    analytics_type: AnalyticsType
    metric_type: MetricType
    value: Decimal
    previous_value: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percentage: Optional[Decimal] = None
    unit: str = ""
    time_frame: TimeFrame = TimeFrame.CUSTOM
    calculation_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsReport:
    """A comprehensive analytics report."""

    report_id: str = field(default_factory=lambda: f"report_{uuid.uuid4().hex[:12]}")
    name: str
    report_type: ReportType
    analytics_type: AnalyticsType
    time_frame: TimeFrame
    start_date: datetime
    end_date: datetime
    metrics: List[AnalyticsMetric] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_by: str = "system"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Analytics dashboard configuration and state."""

    dashboard_id: str = field(
        default_factory=lambda: f"dashboard_{uuid.uuid4().hex[:12]}"
    )
    name: str
    description: str
    user_id: str
    widgets: List[Dict[str, Any]] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 300
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_public: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KPI:
    """Key Performance Indicator (KPI) structure."""

    kpi_id: str = field(default_factory=lambda: f"kpi_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    category: str
    current_value: Decimal
    target_value: Decimal
    threshold_warning: Decimal
    threshold_critical: Decimal
    unit: str
    trend: str = "stable"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    historical_values: List[Tuple[datetime, Decimal]] = field(default_factory=list)


class AnalyticsService:
    """
    Comprehensive analytics service for financial services platform.

    Provides real-time and historical analytics, reporting, dashboard creation,
    and KPI monitoring.
    """

    def __init__(self) -> None:
        self.cache_duration: timedelta = timedelta(minutes=15)
        self.max_data_points: int = 1000
        self.QUANTIZE_PRECISION = Decimal("0.01")
        self.default_kpis: Dict[str, Dict[str, Decimal]] = {
            "user_growth_rate": {
                "target": Decimal("10.0"),
                "warning": Decimal("5.0"),
                "critical": Decimal("0.0"),
            },
            "transaction_volume": {
                "target": Decimal("1000000.00"),
                "warning": Decimal("500000.00"),
                "critical": Decimal("100000.00"),
            },
            "portfolio_performance": {
                "target": Decimal("8.0"),
                "warning": Decimal("4.0"),
                "critical": Decimal("0.0"),
            },
            "risk_score": {
                "target": Decimal("5.0"),
                "warning": Decimal("7.0"),
                "critical": Decimal("9.0"),
            },
        }
        self.analytics_cache: Dict[str, Dict[str, Any]] = {}
        self.reports: Dict[str, AnalyticsReport] = {}
        self.dashboards: Dict[str, Dashboard] = {}
        self.kpis: Dict[str, KPI] = {}
        self.metrics_history: Dict[str, List[AnalyticsMetric]] = {}
        self.sample_data: Dict[str, Dict[str, Any]] = {}
        self._initialize_sample_data()
        self._initialize_default_kpis()

    def _initialize_sample_data(self) -> Any:
        """Initializes sample analytics data. Uses Decimal for all financial/numeric data."""
        self.sample_data = {
            "users": {
                "total_users": 1250,
                "active_users_daily": 890,
                "active_users_monthly": 1100,
                "new_users_today": 15,
                "new_users_this_month": 180,
                "user_retention_rate": Decimal("0.85"),
            },
            "transactions": {
                "total_transactions": 15420,
                "daily_volume": Decimal("2500000.00"),
                "monthly_volume": Decimal("75000000.00"),
                "average_transaction_size": Decimal("1620.00"),
                "transaction_success_rate": Decimal("0.987"),
                "failed_transactions": 203,
            },
            "portfolios": {
                "total_portfolios": 980,
                "total_aum": Decimal("125000000.00"),
                "average_portfolio_size": Decimal("127551.02"),
                "top_performing_portfolios": 45,
                "underperforming_portfolios": 12,
            },
            "risk": {
                "high_risk_portfolios": 23,
                "medium_risk_portfolios": 456,
                "low_risk_portfolios": 501,
                "risk_alerts_active": 8,
                "compliance_violations": 2,
            },
        }

    def _initialize_default_kpis(self) -> Any:
        """Initialize default KPIs from configuration."""
        for kpi_name, config in self.default_kpis.items():
            current_value = config["target"] * Decimal("0.8")
            if "rate" in kpi_name or "performance" in kpi_name:
                unit = "%"
            elif "volume" in kpi_name:
                unit = "$"
            else:
                unit = "score"
            is_lower_better = kpi_name == "risk_score"
            if is_lower_better:
                current_value = config["target"] + Decimal("0.5")
                trend = "down" if current_value > config["target"] else "up"
            else:
                current_value = config["target"] * Decimal("0.8")
                trend = (
                    "up"
                    if current_value > config["target"] * Decimal("0.7")
                    else "down"
                )
            kpi = KPI(
                name=kpi_name.replace("_", " ").title(),
                description=f"Key performance indicator for {kpi_name.replace('_', ' ')}",
                category=kpi_name.split("_")[0],
                current_value=current_value.quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                ),
                target_value=config["target"].quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                ),
                threshold_warning=config["warning"].quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                ),
                threshold_critical=config["critical"].quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                ),
                unit=unit,
                trend=trend,
                historical_values=[],
            )
            self.kpis[kpi.kpi_id] = kpi

    async def generate_analytics_report(
        self,
        analytics_type: AnalyticsType,
        report_type: ReportType,
        time_frame: TimeFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        generated_by: str = "system",
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        start_date, end_date = self._determine_date_range(
            time_frame, start_date, end_date
        )
        metrics = await self._generate_metrics(
            analytics_type, time_frame, start_date, end_date, filters
        )
        charts = await self._generate_charts(analytics_type, metrics, time_frame)
        insights = await self._generate_insights(analytics_type, metrics)
        recommendations = await self._generate_recommendations(
            analytics_type, metrics, insights
        )
        report = AnalyticsReport(
            name=f"{analytics_type.value.replace('_', ' ').title()} {report_type.name.title()} Report",
            report_type=report_type,
            analytics_type=analytics_type,
            time_frame=time_frame,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            charts=charts,
            insights=insights,
            recommendations=recommendations,
            generated_by=generated_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            metadata=filters or {},
        )
        self.reports[report.report_id] = report
        logger.info(
            f"Analytics report generated: {report.report_id} ({analytics_type.value}, {report_type.value})"
        )
        return {
            "report_id": report.report_id,
            "name": report.name,
            "type": report_type.value,
            "analytics_type": analytics_type.value,
            "time_frame": time_frame.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics_count": len(metrics),
            "charts_count": len(charts),
            "insights_count": len(insights),
            "recommendations_count": len(recommendations),
            "generated_at": report.generated_at.isoformat(),
        }

    async def get_real_time_analytics(
        self, analytics_type: AnalyticsType, metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get real-time analytics data with caching logic."""
        cache_key = f"{analytics_type.value}_realtime"
        now_utc = datetime.now(timezone.utc)
        cache_entry = self.analytics_cache.get(cache_key)
        if cache_entry and now_utc - cache_entry["timestamp"] < self.cache_duration:
            if metrics:
                return {k: v for k, v in cache_entry["data"].items() if k in metrics}
            return cache_entry["data"]
        real_time_data = self._simulate_real_time_data(analytics_type)
        self.analytics_cache[cache_key] = {"data": real_time_data, "timestamp": now_utc}
        logger.debug(
            f"Real-time analytics fetched for {analytics_type.value} (Cache Miss)."
        )
        if metrics:
            return {k: v for k, v in real_time_data.items() if k in metrics}
        return real_time_data

    async def create_dashboard(
        self,
        name: str,
        description: str,
        user_id: str,
        widgets: List[Dict[str, Any]],
        layout: Dict[str, Any],
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Create custom analytics dashboard."""
        dashboard = Dashboard(
            name=name,
            description=description,
            user_id=user_id,
            widgets=widgets,
            layout=layout,
            is_public=is_public,
        )
        self.dashboards[dashboard.dashboard_id] = dashboard
        logger.info(f"Dashboard created: {dashboard.dashboard_id} by user {user_id}")
        return {
            "dashboard_id": dashboard.dashboard_id,
            "name": name,
            "widgets_count": len(widgets),
            "created_at": dashboard.created_at.isoformat(),
            "is_public": is_public,
        }

    async def get_dashboard_data(
        self, dashboard_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get dashboard data with all widget information."""
        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            logger.warning(
                f"Attempted access to non-existent dashboard: {dashboard_id}"
            )
            raise ValueError(f"Dashboard not found: {dashboard_id}")
        if not dashboard.is_public and dashboard.user_id != user_id:
            logger.error(
                f"Unauthorized access to dashboard {dashboard_id} by user {user_id}"
            )
            raise PermissionError("Unauthorized access to dashboard")
        widget_data_tasks: List[Coroutine] = [
            self._get_widget_data(widget) for widget in dashboard.widgets
        ]
        widget_data = [await task for task in widget_data_tasks]
        dashboard.last_updated = datetime.now(timezone.utc)
        return {
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
            "description": dashboard.description,
            "layout": dashboard.layout,
            "widgets": widget_data,
            "last_updated": dashboard.last_updated.isoformat(),
            "refresh_interval": dashboard.refresh_interval,
        }

    async def get_kpi_summary(self) -> Dict[str, Any]:
        """Get summary of all KPIs."""
        kpi_summary: Dict[str, Any] = {
            "total_kpis": len(self.kpis),
            "on_target": 0,
            "warning": 0,
            "critical": 0,
            "kpis": [],
        }
        for kpi in self.kpis.values():
            is_lower_better = kpi.name == "Risk Score"
            if is_lower_better:
                if kpi.current_value <= kpi.target_value:
                    status = "on_target"
                    kpi_summary["on_target"] += 1
                elif kpi.current_value <= kpi.threshold_warning:
                    status = "warning"
                    kpi_summary["warning"] += 1
                else:
                    status = "critical"
                    kpi_summary["critical"] += 1
            elif kpi.current_value >= kpi.target_value:
                status = "on_target"
                kpi_summary["on_target"] += 1
            elif kpi.current_value >= kpi.threshold_critical:
                status = "warning"
                kpi_summary["warning"] += 1
            else:
                status = "critical"
                kpi_summary["critical"] += 1
            if kpi.target_value == Decimal("0"):
                progress = Decimal("0")
            elif is_lower_better:
                progress = (kpi.target_value / kpi.current_value * 100).quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                )
                progress = min(progress, Decimal("200"))
            else:
                progress = (kpi.current_value / kpi.target_value * 100).quantize(
                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                )
            kpi_summary["kpis"].append(
                {
                    "kpi_id": kpi.kpi_id,
                    "name": kpi.name,
                    "category": kpi.category,
                    "current_value": str(kpi.current_value),
                    "target_value": str(kpi.target_value),
                    "unit": kpi.unit,
                    "status": status,
                    "progress_percentage": str(progress),
                    "trend": kpi.trend,
                    "last_updated": kpi.last_updated.isoformat(),
                }
            )
        return kpi_summary

    async def get_comparative_analysis(
        self,
        entity_type: str,
        entity_ids: List[str],
        metrics: List[str],
        time_frame: TimeFrame,
    ) -> Dict[str, Any]:
        """Get comparative analysis between entities (e.g., portfolios, users, regions)."""
        analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
        comparison_data = {}
        for entity_id in entity_ids:
            entity_metrics = {}
            for metric in metrics:
                seed = hash(entity_id + metric)
                if metric == "total_return":
                    value = Decimal("8.5") + Decimal(str(seed % 100)) / Decimal("100.0")
                elif metric == "volatility":
                    value = Decimal("15.0") + Decimal(str(seed % 50)) / Decimal("100.0")
                elif metric == "sharpe_ratio":
                    value = Decimal("1.2") + Decimal(str(seed % 30)) / Decimal("100.0")
                elif metric == "max_drawdown":
                    value = Decimal("5.0") + Decimal(str(seed % 20)) / Decimal("100.0")
                else:
                    value = Decimal("100.0") + Decimal(str(seed % 200)) / Decimal(
                        "10.0"
                    )
                entity_metrics[metric] = str(
                    value.quantize(self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)
                )
            comparison_data[entity_id] = entity_metrics
        rankings = {}
        LOWER_IS_BETTER_METRICS = {"volatility", "max_drawdown"}
        for metric in metrics:
            metric_values = []
            for entity_id, data in comparison_data.items():
                try:
                    metric_values.append((entity_id, Decimal(data[metric])))
                except KeyError:
                    logger.warning(f"Metric {metric} not found for entity {entity_id}")
                    continue
            reverse_sort = metric not in LOWER_IS_BETTER_METRICS
            metric_values.sort(key=lambda x: x[1], reverse=reverse_sort)
            rankings[metric] = [
                {
                    "entity_id": entity_id,
                    "value": str(
                        value.quantize(self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)
                    ),
                    "rank": i + 1,
                }
                for i, (entity_id, value) in enumerate(metric_values)
            ]
        return {
            "analysis_id": analysis_id,
            "entity_type": entity_type,
            "entities_compared": len(entity_ids),
            "metrics_analyzed": len(metrics),
            "time_frame": time_frame.value,
            "comparison_data": comparison_data,
            "rankings": rankings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _determine_date_range(
        self,
        time_frame: TimeFrame,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> Tuple[datetime, datetime]:
        """Utility to calculate start and end dates based on TimeFrame."""
        end_date = end_date or datetime.now(timezone.utc)
        if start_date and end_date:
            return (start_date, end_date)
        if time_frame == TimeFrame.HOURLY:
            start_date = end_date - timedelta(hours=1)
        elif time_frame == TimeFrame.DAILY:
            start_date = end_date - timedelta(days=1)
        elif time_frame == TimeFrame.WEEKLY:
            start_date = end_date - timedelta(weeks=1)
        elif time_frame == TimeFrame.MONTHLY:
            start_date = end_date - timedelta(days=30)
        elif time_frame == TimeFrame.QUARTERLY:
            start_date = end_date - timedelta(days=90)
        elif time_frame == TimeFrame.YEARLY:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return (start_date, end_date)

    def _simulate_real_time_data(self, analytics_type: AnalyticsType) -> Dict[str, Any]:
        """Simulates fetching fresh real-time data."""
        real_time_data: Dict[str, Any] = {}
        if analytics_type == AnalyticsType.USER_ANALYTICS:
            real_time_data = {
                "active_users_now": self.sample_data["users"].get(
                    "active_users_daily", 0
                ),
                "new_registrations_today": self.sample_data["users"].get(
                    "new_users_today", 0
                ),
                "user_sessions_active": 234,
                "average_session_duration_sec": 754,
                "bounce_rate_pct": Decimal("15.2"),
                "conversion_rate_pct": Decimal("3.8"),
            }
        elif analytics_type == AnalyticsType.TRANSACTION_ANALYTICS:
            real_time_data = {
                "transactions_per_minute": Decimal("12.5"),
                "volume_per_minute": Decimal("45000.00"),
                "success_rate_pct": Decimal("98.7"),
                "average_processing_time_sec": Decimal("2.3"),
                "pending_transactions": 45,
                "failed_transactions_today": 12,
            }
        elif analytics_type == AnalyticsType.PORTFOLIO_ANALYTICS:
            real_time_data = {
                "total_aum": self.sample_data["portfolios"].get(
                    "total_aum", Decimal("0")
                ),
                "portfolios_rebalanced_today": 23,
                "top_performing_asset": "AAPL (+2.3%)",
                "worst_performing_asset": "TSLA (-1.8%)",
                "market_sentiment": "Bullish",
                "volatility_index": Decimal("18.5"),
            }
        elif analytics_type == AnalyticsType.RISK_ANALYTICS:
            real_time_data = {
                "active_risk_alerts": self.sample_data["risk"].get(
                    "risk_alerts_active", 0
                ),
                "high_risk_portfolios": self.sample_data["risk"].get(
                    "high_risk_portfolios", 0
                ),
                "var_95_breach_count": 2,
                "stress_test_failures": 1,
                "compliance_score_pct": Decimal("94.2"),
                "risk_adjusted_return_pct": Decimal("8.7"),
            }
        return {
            k: str(v) if isinstance(v, Decimal) else v
            for k, v in real_time_data.items()
        }

    async def _generate_metrics(
        self,
        analytics_type: AnalyticsType,
        time_frame: TimeFrame,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]],
    ) -> List[AnalyticsMetric]:
        """Generate metrics for analytics report. Fixed to use Decimal correctly."""
        metrics: List[AnalyticsMetric] = []
        if analytics_type == AnalyticsType.USER_ANALYTICS:
            metrics.append(
                AnalyticsMetric(
                    name="Total Users",
                    analytics_type=analytics_type,
                    metric_type=MetricType.COUNT,
                    value=Decimal(self.sample_data["users"]["total_users"]),
                    previous_value=Decimal("1180"),
                    unit="users",
                    time_frame=time_frame,
                )
            )
            metrics.append(
                AnalyticsMetric(
                    name="User Retention Rate",
                    analytics_type=analytics_type,
                    metric_type=MetricType.PERCENTAGE,
                    value=self.sample_data["users"]["user_retention_rate"]
                    * Decimal("100"),
                    previous_value=Decimal("82.5"),
                    unit="%",
                    time_frame=time_frame,
                )
            )
        elif analytics_type == AnalyticsType.TRANSACTION_ANALYTICS:
            metrics.append(
                AnalyticsMetric(
                    name="Transaction Volume",
                    analytics_type=analytics_type,
                    metric_type=MetricType.SUM,
                    value=self.sample_data["transactions"]["daily_volume"],
                    previous_value=Decimal("2300000.00"),
                    unit="USD",
                    time_frame=time_frame,
                )
            )
            metrics.append(
                AnalyticsMetric(
                    name="Success Rate",
                    analytics_type=analytics_type,
                    metric_type=MetricType.PERCENTAGE,
                    value=self.sample_data["transactions"]["transaction_success_rate"]
                    * Decimal("100"),
                    previous_value=Decimal("98.2"),
                    unit="%",
                    time_frame=time_frame,
                )
            )
        elif analytics_type == AnalyticsType.PORTFOLIO_ANALYTICS:
            metrics.append(
                AnalyticsMetric(
                    name="Assets Under Management",
                    analytics_type=analytics_type,
                    metric_type=MetricType.SUM,
                    value=self.sample_data["portfolios"]["total_aum"],
                    previous_value=Decimal("120000000.00"),
                    unit="USD",
                    time_frame=time_frame,
                )
            )
            metrics.append(
                AnalyticsMetric(
                    name="Average Portfolio Performance",
                    analytics_type=analytics_type,
                    metric_type=MetricType.PERCENTAGE,
                    value=Decimal("8.5"),
                    previous_value=Decimal("7.8"),
                    unit="%",
                    time_frame=time_frame,
                )
            )
        elif analytics_type == AnalyticsType.RISK_ANALYTICS:
            metrics.append(
                AnalyticsMetric(
                    name="Average Risk Score",
                    analytics_type=analytics_type,
                    metric_type=MetricType.AVERAGE,
                    value=Decimal("5.2"),
                    previous_value=Decimal("5.8"),
                    unit="score",
                    time_frame=time_frame,
                )
            )
            metrics.append(
                AnalyticsMetric(
                    name="High Risk Portfolios",
                    analytics_type=analytics_type,
                    metric_type=MetricType.COUNT,
                    value=Decimal(self.sample_data["risk"]["high_risk_portfolios"]),
                    previous_value=Decimal("28"),
                    unit="portfolios",
                    time_frame=time_frame,
                )
            )
        for metric in metrics:
            if metric.previous_value is not None:
                metric.change = metric.value - metric.previous_value
                if metric.previous_value != Decimal("0"):
                    metric.change_percentage = (
                        metric.change / metric.previous_value * Decimal("100")
                    ).quantize(self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)
                else:
                    metric.change_percentage = (
                        Decimal("0")
                        if metric.change == Decimal("0")
                        else Decimal("1000000")
                    )
        return metrics

    async def _generate_charts(
        self,
        analytics_type: AnalyticsType,
        metrics: List[AnalyticsMetric],
        time_frame: TimeFrame,
    ) -> List[Dict[str, Any]]:
        """Generate chart configurations for metrics."""
        charts: List[Dict[str, Any]] = []
        if not metrics:
            return charts
        main_metric = metrics[0]
        time_series_data = []
        for i in range(30):
            date = datetime.now(timezone.utc) - timedelta(days=29 - i)
            value = main_metric.value * (Decimal("0.9") + Decimal(str(i % 10 * 0.02)))
            time_series_data.append(
                {
                    "date": date.isoformat(),
                    "value": float(
                        value.quantize(self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)
                    ),
                }
            )
        charts.append(
            {
                "chart_id": f"chart_{uuid.uuid4().hex[:8]}",
                "type": "line",
                "title": f"{main_metric.name} Trend ({time_frame.value.title()})",
                "data": time_series_data,
                "x_axis": "date",
                "y_axis": "value",
                "unit": main_metric.unit,
            }
        )
        if analytics_type == AnalyticsType.RISK_ANALYTICS:
            charts.append(
                {
                    "chart_id": f"chart_{uuid.uuid4().hex[:8]}",
                    "type": "pie",
                    "title": "Risk Portfolio Distribution",
                    "data": [
                        {
                            "label": "Low Risk",
                            "value": self.sample_data["risk"]["low_risk_portfolios"],
                        },
                        {
                            "label": "Medium Risk",
                            "value": self.sample_data["risk"]["medium_risk_portfolios"],
                        },
                        {
                            "label": "High Risk",
                            "value": self.sample_data["risk"]["high_risk_portfolios"],
                        },
                    ],
                }
            )
        if len(metrics) > 1:
            bar_data = []
            for metric in metrics[:5]:
                bar_data.append(
                    {
                        "label": metric.name,
                        "value": float(
                            metric.value.quantize(
                                self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                            )
                        ),
                        "change": (
                            float(
                                metric.change.quantize(
                                    self.QUANTIZE_PRECISION, rounding=ROUND_HALF_UP
                                )
                            )
                            if metric.change
                            else 0.0
                        ),
                    }
                )
            charts.append(
                {
                    "chart_id": f"chart_{uuid.uuid4().hex[:8]}",
                    "type": "bar",
                    "title": "Key Metrics Comparison",
                    "data": bar_data,
                    "x_axis": "metric",
                    "y_axis": "value",
                }
            )
        return charts

    async def _generate_insights(
        self, analytics_type: AnalyticsType, metrics: List[AnalyticsMetric]
    ) -> List[str]:
        """Generate qualitative insights from metrics."""
        insights: List[str] = []

        def find_metric(name: str) -> Optional[AnalyticsMetric]:
            return next((m for m in metrics if m.name == name), None)

        for metric in metrics:
            change_pct = metric.change_percentage
            if change_pct is not None:
                if change_pct > Decimal("10"):
                    insights.append(
                        f"📊 **{metric.name}** has increased significantly by **{change_pct}%** over the period, indicating a strong positive trend."
                    )
                elif change_pct < Decimal("-10"):
                    insights.append(
                        f"⚠️ **{metric.name}** has decreased significantly by **{abs(change_pct)}%**, which requires immediate investigation."
                    )
        if analytics_type == AnalyticsType.USER_ANALYTICS:
            total_users_metric = find_metric("Total Users")
            retention_rate_metric = find_metric("User Retention Rate")
            if total_users_metric and total_users_metric.change_percentage > Decimal(
                "5"
            ):
                insights.append(
                    "📈 Significant growth in the user base, indicating successful acquisition strategies in the last period."
                )
            if (
                retention_rate_metric
                and retention_rate_metric.change_percentage > Decimal("0")
            ):
                insights.append(
                    "🌟 User engagement is trending upward with improved retention rates, validating product sticky-ness."
                )
        elif analytics_type == AnalyticsType.TRANSACTION_ANALYTICS:
            volume_metric = find_metric("Transaction Volume")
            success_metric = find_metric("Success Rate")
            if volume_metric and volume_metric.change_percentage > Decimal("10"):
                insights.append(
                    "🚀 Exceptional growth in transaction volume, suggesting high market activity and demand."
                )
            if success_metric and success_metric.change_percentage < Decimal("0"):
                insights.append(
                    "🔍 A slight dip in transaction success rate. A root cause analysis on failed transactions is recommended."
                )
        elif analytics_type == AnalyticsType.RISK_ANALYTICS:
            risk_score_metric = find_metric("Average Risk Score")
            high_risk_metric = find_metric("High Risk Portfolios")
            if risk_score_metric and risk_score_metric.change < Decimal("0"):
                insights.append(
                    "✅ Average portfolio risk score has decreased, indicating a successful de-risking strategy."
                )
            if high_risk_metric and high_risk_metric.value > Decimal("20"):
                insights.append(
                    "🚨 Over 20 high-risk portfolios detected. Increased monitoring and client outreach is necessary."
                )
        if not insights:
            insights.append(
                "Neutral performance observed across key metrics for this period."
            )
        return insights

    async def _generate_recommendations(
        self,
        analytics_type: AnalyticsType,
        metrics: List[AnalyticsMetric],
        insights: List[str],
    ) -> List[str]:
        """Generate actionable recommendations based on insights."""
        recommendations: List[str] = []
        if any(("requires immediate investigation" in i for i in insights)):
            recommendations.append(
                "Investigate the root cause of the significantly decreased metric(s) immediately, focusing on underlying data sources or process changes."
            )
        if any(("successful de-risking strategy" in i for i in insights)):
            recommendations.append(
                "Formalize and document the de-risking strategies deployed this period for replication in other risk-bearing areas."
            )
        if any(("High Risk Portfolios" in i for i in insights)):
            recommendations.append(
                "Prioritize an urgent review of all portfolios flagged as high-risk and implement risk-mitigation actions (e.g., rebalancing, hedging)."
            )
        if analytics_type == AnalyticsType.USER_ANALYTICS and (
            not any(("retention" in i for i in insights))
        ):
            recommendations.append(
                "Develop targeted campaigns to boost user retention, focusing on a specific underperforming segment or feature."
            )
        if analytics_type == AnalyticsType.TRANSACTION_ANALYTICS and any(
            ("dip in transaction success rate" in i for i in insights)
        ):
            recommendations.append(
                "Perform a diagnostic on payment gateway reliability and latency during peak transaction hours."
            )
        if not recommendations:
            recommendations.append(
                "Maintain current performance and schedule a deep-dive session to explore optimization opportunities."
            )
        return recommendations

    async def _get_widget_data(self, widget_config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate fetching and processing data for a single dashboard widget."""
        widget_type = widget_config.get("widget_type")
        metric_key = widget_config.get("metric_key")
        if not widget_type or not metric_key:
            return {"error": "Invalid widget configuration", "config": widget_config}
        if widget_type == "kpi_card":
            kpi = self.kpis.get(metric_key)
            if kpi:
                return {
                    "widget_id": widget_config.get("id", str(uuid.uuid4())),
                    "type": widget_type,
                    "title": kpi.name,
                    "value": str(kpi.current_value),
                    "unit": kpi.unit,
                    "status": (
                        "on_target"
                        if kpi.current_value >= kpi.target_value
                        else "warning"
                    ),
                }
            else:
                return {"error": f"KPI not found for key: {metric_key}"}
        elif widget_type == "realtime_chart":
            real_time_data = self._simulate_real_time_data(
                AnalyticsType.PORTFOLIO_ANALYTICS
            )
            value = real_time_data.get(metric_key, "N/A")
            historical = [
                (
                    datetime.now(timezone.utc) - timedelta(hours=i),
                    Decimal(120000000.0) + Decimal(i * 1000000),
                )
                for i in range(10)
            ]
            return {
                "widget_id": widget_config.get("id", str(uuid.uuid4())),
                "type": widget_type,
                "title": f"Real-Time {metric_key.replace('_', ' ').title()}",
                "current_value": value,
                "chart_data": [
                    {"time": t.isoformat(), "value": str(v.quantize(Decimal("0.01")))}
                    for t, v in historical
                ],
            }
        else:
            return {"error": f"Unsupported widget type: {widget_type}"}
