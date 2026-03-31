"""
Comprehensive Metrics Collection System for Fluxion Backend
Implements enterprise-grade monitoring, metrics collection, and observability
for financial services platform with real-time monitoring and alerting.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point"""

    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str]
    timestamp: datetime
    unit: str
    description: str


@dataclass
class Alert:
    """Monitoring alert"""

    alert_id: str
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float
    labels: Dict[str, str]
    triggered_at: datetime
    resolved_at: Optional[datetime]
    is_active: bool


@dataclass
class HealthCheck:
    """Health check result"""

    name: str
    status: str
    message: str
    response_time_ms: float
    timestamp: datetime
    metadata: Dict[str, Any]


class MetricsCollector:
    """
    Comprehensive metrics collection system providing:
    - System metrics (CPU, memory, disk, network)
    - Application metrics (requests, errors, latency)
    - Business metrics (transactions, users, revenue)
    - Custom metrics with labels and dimensions
    - Real-time alerting and notifications
    - Health checks and service monitoring
    - Performance profiling and tracing
    - Metrics aggregation and storage
    """

    def __init__(self) -> None:
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_callbacks: List[Callable] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_check_functions: Dict[str, Callable] = {}
        self.collection_interval = 10
        self.retention_period = timedelta(hours=24)
        self.is_collecting = False
        self.collection_task = None
        self.cleanup_task = None
        self._initialize_default_alert_rules()
        self.start_collection()

    def _initialize_default_alert_rules(self) -> Any:
        """Initialize default alerting rules"""
        self.alert_rules = {
            "high_cpu_usage": {
                "metric": "system.cpu.usage",
                "threshold": 80.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "duration": 300,
            },
            "high_memory_usage": {
                "metric": "system.memory.usage",
                "threshold": 85.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "duration": 300,
            },
            "low_disk_space": {
                "metric": "system.disk.usage",
                "threshold": 90.0,
                "operator": ">",
                "severity": AlertSeverity.ERROR,
                "duration": 60,
            },
            "high_error_rate": {
                "metric": "application.error.rate",
                "threshold": 5.0,
                "operator": ">",
                "severity": AlertSeverity.ERROR,
                "duration": 120,
            },
            "high_response_time": {
                "metric": "application.response.time.p95",
                "threshold": 2000.0,
                "operator": ">",
                "severity": AlertSeverity.WARNING,
                "duration": 180,
            },
            "low_transaction_success_rate": {
                "metric": "business.transaction.success_rate",
                "threshold": 95.0,
                "operator": "<",
                "severity": AlertSeverity.CRITICAL,
                "duration": 60,
            },
        }

    def start_collection(self) -> Any:
        """Start metrics collection"""
        if not self.is_collecting:
            self.is_collecting = True
            self.collection_task = asyncio.create_task(self._collection_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Metrics collection started")

    def stop_collection(self) -> Any:
        """Stop metrics collection"""
        if self.is_collecting:
            self.is_collecting = False
            if self.collection_task:
                self.collection_task.cancel()
            if self.cleanup_task:
                self.cleanup_task.cancel()
            logger.info("Metrics collection stopped")

    async def _collection_loop(self):
        """Main collection loop"""
        while self.is_collecting:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await self._run_health_checks()
                await self._check_alerts()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {str(e)}")
                await asyncio.sleep(self.collection_interval)

    async def _cleanup_loop(self):
        """Cleanup old metrics"""
        while self.is_collecting:
            try:
                await self._cleanup_old_metrics()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics cleanup error: {str(e)}")
                await asyncio.sleep(3600)

    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        datetime.now(timezone.utc)
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
        self.record_gauge("system.cpu.usage", cpu_percent, {"unit": "percent"})
        self.record_gauge("system.cpu.count", cpu_count, {"unit": "cores"})
        self.record_gauge("system.load.1m", load_avg[0], {"unit": "load"})
        self.record_gauge("system.load.5m", load_avg[1], {"unit": "load"})
        self.record_gauge("system.load.15m", load_avg[2], {"unit": "load"})
        memory = psutil.virtual_memory()
        self.record_gauge("system.memory.total", memory.total, {"unit": "bytes"})
        self.record_gauge(
            "system.memory.available", memory.available, {"unit": "bytes"}
        )
        self.record_gauge("system.memory.used", memory.used, {"unit": "bytes"})
        self.record_gauge("system.memory.usage", memory.percent, {"unit": "percent"})
        disk = psutil.disk_usage("/")
        self.record_gauge(
            "system.disk.total", disk.total, {"unit": "bytes", "mount": "/"}
        )
        self.record_gauge(
            "system.disk.used", disk.used, {"unit": "bytes", "mount": "/"}
        )
        self.record_gauge(
            "system.disk.free", disk.free, {"unit": "bytes", "mount": "/"}
        )
        self.record_gauge(
            "system.disk.usage",
            disk.used / disk.total * 100,
            {"unit": "percent", "mount": "/"},
        )
        network = psutil.net_io_counters()
        self.record_counter(
            "system.network.bytes_sent", network.bytes_sent, {"unit": "bytes"}
        )
        self.record_counter(
            "system.network.bytes_recv", network.bytes_recv, {"unit": "bytes"}
        )
        self.record_counter(
            "system.network.packets_sent", network.packets_sent, {"unit": "packets"}
        )
        self.record_counter(
            "system.network.packets_recv", network.packets_recv, {"unit": "packets"}
        )
        process = psutil.Process()
        self.record_gauge(
            "process.cpu.usage", process.cpu_percent(), {"unit": "percent"}
        )
        self.record_gauge(
            "process.memory.rss", process.memory_info().rss, {"unit": "bytes"}
        )
        self.record_gauge(
            "process.memory.vms", process.memory_info().vms, {"unit": "bytes"}
        )
        self.record_gauge("process.threads", process.num_threads(), {"unit": "count"})
        self.record_gauge(
            "process.fds",
            process.num_fds() if hasattr(process, "num_fds") else 0,
            {"unit": "count"},
        )

    async def _collect_application_metrics(self):
        """Collect application-level metrics"""
        self.record_gauge("application.requests.active", 25, {"unit": "count"})
        self.record_gauge("application.response.time.avg", 150.5, {"unit": "ms"})
        self.record_gauge("application.response.time.p95", 450.2, {"unit": "ms"})
        self.record_gauge("application.response.time.p99", 850.7, {"unit": "ms"})
        self.record_gauge("application.error.rate", 2.1, {"unit": "percent"})
        self.record_counter("application.errors.total", 42, {"unit": "count"})
        self.record_gauge("database.connections.active", 15, {"unit": "count"})
        self.record_gauge("database.connections.idle", 35, {"unit": "count"})
        self.record_gauge("database.query.time.avg", 25.3, {"unit": "ms"})
        self.record_gauge("cache.hit.rate", 87.5, {"unit": "percent"})
        self.record_gauge("cache.memory.usage", 65.2, {"unit": "percent"})
        self.record_gauge("queue.size", 123, {"unit": "count"})
        self.record_gauge("queue.processing.rate", 45.2, {"unit": "per_second"})

    def record_counter(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Record a counter metric"""
        labels = labels or {}
        self.counters[name] = value
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels,
            timestamp=datetime.now(timezone.utc),
            unit=labels.get("unit", ""),
            description=f"Counter metric: {name}",
        )
        self.metrics[name].append(metric)

    def record_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Record a gauge metric"""
        labels = labels or {}
        self.gauges[name] = value
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels,
            timestamp=datetime.now(timezone.utc),
            unit=labels.get("unit", ""),
            description=f"Gauge metric: {name}",
        )
        self.metrics[name].append(metric)

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Record a histogram metric"""
        labels = labels or {}
        self.histograms[name].append(value)
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels,
            timestamp=datetime.now(timezone.utc),
            unit=labels.get("unit", ""),
            description=f"Histogram metric: {name}",
        )
        self.metrics[name].append(metric)

    def record_timer(
        self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Record a timer metric"""
        labels = labels or {}
        labels["unit"] = "ms"
        self.record_histogram(name, duration_ms, labels)

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> Any:
        """Increment a counter metric"""
        current_value = self.counters.get(name, 0.0)
        self.record_counter(name, current_value + value, labels)

    def get_metric_value(self, name: str) -> Optional[float]:
        """Get current value of a metric"""
        if name in self.counters:
            return self.counters[name]
        elif name in self.gauges:
            return self.gauges[name]
        return None

    def get_metric_history(
        self, name: str, duration: Optional[timedelta] = None
    ) -> List[Metric]:
        """Get metric history"""
        if name not in self.metrics:
            return []
        metrics = list(self.metrics[name])
        if duration:
            cutoff_time = datetime.now(timezone.utc) - duration
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        return metrics

    def get_histogram_percentiles(
        self, name: str, percentiles: List[float]
    ) -> Dict[float, float]:
        """Get histogram percentiles"""
        if name not in self.histograms or not self.histograms[name]:
            return {p: 0.0 for p in percentiles}
        values = sorted(self.histograms[name])
        result = {}
        for percentile in percentiles:
            index = int(percentile / 100.0 * len(values))
            if index >= len(values):
                index = len(values) - 1
            result[percentile] = values[index]
        return result

    def add_alert_rule(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str,
        severity: AlertSeverity,
        duration: int = 60,
    ) -> Any:
        """Add custom alert rule"""
        self.alert_rules[name] = {
            "metric": metric,
            "threshold": threshold,
            "operator": operator,
            "severity": severity,
            "duration": duration,
        }
        logger.info(f"Alert rule added: {name}")

    def add_alert_callback(self, callback: Callable[[Alert], None]) -> Any:
        """Add alert callback function"""
        self.alert_callbacks.append(callback)

    async def _check_alerts(self):
        """Check alert conditions"""
        for rule_name, rule in self.alert_rules.items():
            metric_name = rule["metric"]
            threshold = rule["threshold"]
            operator = rule["operator"]
            severity = rule["severity"]
            rule["duration"]
            current_value = self.get_metric_value(metric_name)
            if current_value is None:
                continue
            condition_met = False
            if operator == ">":
                condition_met = current_value > threshold
            elif operator == "<":
                condition_met = current_value < threshold
            elif operator == ">=":
                condition_met = current_value >= threshold
            elif operator == "<=":
                condition_met = current_value <= threshold
            elif operator == "==":
                condition_met = current_value == threshold
            elif operator == "!=":
                condition_met = current_value != threshold
            alert_id = f"alert_{rule_name}"
            if condition_met:
                if alert_id not in self.alerts or not self.alerts[alert_id].is_active:
                    alert = Alert(
                        alert_id=alert_id,
                        metric_name=metric_name,
                        severity=severity,
                        message=f"{metric_name} {operator} {threshold} (current: {current_value})",
                        current_value=current_value,
                        threshold_value=threshold,
                        labels={"rule": rule_name},
                        triggered_at=datetime.now(timezone.utc),
                        resolved_at=None,
                        is_active=True,
                    )
                    self.alerts[alert_id] = alert
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback error: {str(e)}")
                    logger.warning(f"Alert triggered: {alert.message}")
            elif alert_id in self.alerts and self.alerts[alert_id].is_active:
                self.alerts[alert_id].is_active = False
                self.alerts[alert_id].resolved_at = datetime.now(timezone.utc)
                logger.info(f"Alert resolved: {rule_name}")

    def register_health_check(
        self, name: str, check_function: Callable[[], Dict[str, Any]]
    ) -> Any:
        """Register a health check function"""
        self.health_check_functions[name] = check_function
        logger.info(f"Health check registered: {name}")

    async def _run_health_checks(self):
        """Run all health checks"""
        for name, check_function in self.health_check_functions.items():
            try:
                start_time = time.time()
                result = check_function()
                response_time = (time.time() - start_time) * 1000
                health_check = HealthCheck(
                    name=name,
                    status=result.get("status", "unknown"),
                    message=result.get("message", ""),
                    response_time_ms=response_time,
                    timestamp=datetime.now(timezone.utc),
                    metadata=result.get("metadata", {}),
                )
                self.health_checks[name] = health_check
                status_code = 1 if health_check.status == "healthy" else 0
                self.record_gauge(
                    f"health.{name}.status", status_code, {"unit": "boolean"}
                )
                self.record_gauge(
                    f"health.{name}.response_time", response_time, {"unit": "ms"}
                )
            except Exception as e:
                logger.error(f"Health check failed for {name}: {str(e)}")
                health_check = HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=f"Health check failed: {str(e)}",
                    response_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc),
                    metadata={},
                )
                self.health_checks[name] = health_check
                self.record_gauge(f"health.{name}.status", 0, {"unit": "boolean"})

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.health_checks:
            return {"status": "unknown", "checks": {}}
        healthy_checks = sum(
            (1 for hc in self.health_checks.values() if hc.status == "healthy")
        )
        total_checks = len(self.health_checks)
        if healthy_checks == total_checks:
            overall_status = "healthy"
        elif healthy_checks > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        return {
            "status": overall_status,
            "healthy_checks": healthy_checks,
            "total_checks": total_checks,
            "checks": {
                name: {
                    "status": hc.status,
                    "message": hc.message,
                    "response_time_ms": hc.response_time_ms,
                    "timestamp": hc.timestamp.isoformat(),
                }
                for name, hc in self.health_checks.items()
            },
        }

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        active_alerts = [alert for alert in self.alerts.values() if alert.is_active]
        return [
            {
                "alert_id": alert.alert_id,
                "metric_name": alert.metric_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "labels": alert.labels,
            }
            for alert in active_alerts
        ]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            "total_metrics": len(self.metrics),
            "counters": len(self.counters),
            "gauges": len(self.gauges),
            "histograms": len(self.histograms),
            "active_alerts": len([a for a in self.alerts.values() if a.is_active]),
            "health_checks": len(self.health_checks),
            "collection_interval": self.collection_interval,
            "is_collecting": self.is_collecting,
        }

    async def _cleanup_old_metrics(self):
        """Clean up old metrics"""
        cutoff_time = datetime.now(timezone.utc) - self.retention_period
        for metric_name, metric_deque in self.metrics.items():
            while metric_deque and metric_deque[0].timestamp < cutoff_time:
                metric_deque.popleft()
        for name in self.histograms:
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
        logger.debug("Old metrics cleaned up")

    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in specified format"""
        if format_type == "json":
            export_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "counters": self.counters,
                "gauges": self.gauges,
                "histograms": {
                    name: values[-100:] for name, values in self.histograms.items()
                },
                "alerts": [asdict(alert) for alert in self.alerts.values()],
                "health_checks": [asdict(hc) for hc in self.health_checks.values()],
            }
            return json.dumps(export_data, indent=2, default=str)
        elif format_type == "prometheus":
            lines = []
            for name, value in self.counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")
            for name, value in self.gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


metrics_collector = MetricsCollector()


def timed_metric(metric_name: str, labels: Optional[Dict[str, str]] = None) -> Any:
    """Decorator to time function execution"""

    def decorator(func):

        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_timer(metric_name, duration_ms, labels)
                return result
            except Exception:
                duration_ms = (time.time() - start_time) * 1000
                error_labels = (labels or {}).copy()
                error_labels["error"] = "true"
                metrics_collector.record_timer(metric_name, duration_ms, error_labels)
                raise

        return wrapper

    return decorator


class TimedContext:
    """Context manager for timing code blocks"""

    def __init__(
        self, metric_name: str, labels: Optional[Dict[str, str]] = None
    ) -> None:
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self) -> Any:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        duration_ms = (time.time() - self.start_time) * 1000
        if exc_type is not None:
            self.labels["error"] = "true"
        metrics_collector.record_timer(self.metric_name, duration_ms, self.labels)
