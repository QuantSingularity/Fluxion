"""
Fluxion Deployment Validator
Validates deployment readiness and configuration for production environments
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import hvac
import requests
from kubernetes import client, config
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Production deployment readiness validator"""

    def __init__(self, environment: str = "production") -> None:
        self.environment = environment
        self.checks = []
        self.failures = []
        self.warnings = []
        self.requirements = {
            "infrastructure": {
                "kubernetes_cluster": True,
                "load_balancer": True,
                "database": True,
                "cache": True,
                "monitoring": True,
                "logging": True,
            },
            "security": {
                "secrets_management": True,
                "network_policies": True,
                "rbac": True,
                "pod_security": True,
                "image_scanning": True,
            },
            "compliance": {
                "backup_strategy": True,
                "disaster_recovery": True,
                "audit_logging": True,
                "data_encryption": True,
            },
            "performance": {
                "resource_limits": True,
                "auto_scaling": True,
                "health_checks": True,
                "readiness_probes": True,
            },
        }

    def validate_kubernetes_cluster(self) -> None:
        """Validate Kubernetes cluster readiness"""
        logger.info("🔍 Validating Kubernetes cluster...")
        try:
            config.load_kube_config()
            v1 = client.CoreV1Api()
            nodes = v1.list_node()
            if not nodes.items:
                self.failures.append(
                    {
                        "category": "kubernetes",
                        "message": "No nodes found in cluster",
                        "severity": "critical",
                    }
                )
                return
            ready_nodes = 0
            for node in nodes.items:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        ready_nodes += 1
                        break
            if ready_nodes == 0:
                self.failures.append(
                    {
                        "category": "kubernetes",
                        "message": "No ready nodes in cluster",
                        "severity": "critical",
                    }
                )
            else:
                self.checks.append(f"Kubernetes cluster ready with {ready_nodes} nodes")
            namespaces = v1.list_namespace()
            system_namespaces = ["kube-system", "kube-public", "kube-node-lease"]
            for ns in system_namespaces:
                if not any(
                    (namespace.metadata.name == ns for namespace in namespaces.items)
                ):
                    self.failures.append(
                        {
                            "category": "kubernetes",
                            "message": f"Missing system namespace: {ns}",
                            "severity": "high",
                        }
                    )
            if not any(
                (
                    namespace.metadata.name == "monitoring"
                    for namespace in namespaces.items
                )
            ):
                self.warnings.append(
                    {
                        "category": "kubernetes",
                        "message": "Monitoring namespace not found",
                    }
                )
            if not any(
                (namespace.metadata.name == "logging" for namespace in namespaces.items)
            ):
                self.warnings.append(
                    {"category": "kubernetes", "message": "Logging namespace not found"}
                )
        except Exception as e:
            self.failures.append(
                {
                    "category": "kubernetes",
                    "message": f"Cannot connect to Kubernetes cluster: {e}",
                    "severity": "critical",
                }
            )

    def validate_secrets_management(self) -> None:
        """Validate secrets management system"""
        logger.info("🔍 Validating secrets management...")
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        if not vault_addr:
            self.failures.append(
                {
                    "category": "secrets",
                    "message": "VAULT_ADDR environment variable not set",
                    "severity": "critical",
                }
            )
            return
        try:
            vault_client = hvac.Client(url=vault_addr, token=vault_token)
            if not vault_client.is_authenticated():
                self.failures.append(
                    {
                        "category": "secrets",
                        "message": "Cannot authenticate with Vault",
                        "severity": "critical",
                    }
                )
                return
            self.checks.append("Vault authentication successful")
            if vault_client.sys.is_sealed():
                self.failures.append(
                    {
                        "category": "secrets",
                        "message": "Vault is sealed",
                        "severity": "critical",
                    }
                )
                return
            self.checks.append("Vault is unsealed and ready")
            required_secrets = [
                "secret/data/jwt",
                "secret/data/api",
                "secret/data/encryption",
                "secret/data/database",
            ]
            for secret_path in required_secrets:
                try:
                    response = vault_client.secrets.kv.v2.read_secret_version(
                        path=secret_path.replace("secret/data/", "")
                    )
                    if response:
                        self.checks.append(f"Secret exists: {secret_path}")
                    else:
                        self.failures.append(
                            {
                                "category": "secrets",
                                "message": f"Required secret not found: {secret_path}",
                                "severity": "high",
                            }
                        )
                except Exception:
                    self.failures.append(
                        {
                            "category": "secrets",
                            "message": f"Cannot access secret: {secret_path}",
                            "severity": "high",
                        }
                    )
        except Exception as e:
            self.failures.append(
                {
                    "category": "secrets",
                    "message": f"Vault validation failed: {e}",
                    "severity": "critical",
                }
            )

    def validate_database_connectivity(self) -> None:
        """Validate database connectivity and configuration"""
        logger.info("🔍 Validating database connectivity...")
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            self.failures.append(
                {
                    "category": "database",
                    "message": "DATABASE_URL environment variable not set",
                    "severity": "critical",
                }
            )
            return
        if not db_url.startswith(("postgresql://", "mysql://", "mongodb://")):
            self.failures.append(
                {
                    "category": "database",
                    "message": "Invalid database URL format",
                    "severity": "high",
                }
            )
        else:
            self.checks.append("Database URL format is valid")
        if "sslmode=require" not in db_url and "ssl=true" not in db_url:
            self.warnings.append(
                {
                    "category": "database",
                    "message": "Database connection may not enforce SSL",
                }
            )
        else:
            self.checks.append("Database SSL configuration detected")

    def validate_monitoring_stack(self) -> None:
        """Validate monitoring and alerting stack"""
        logger.info("🔍 Validating monitoring stack...")
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
        try:
            response = requests.get(
                f"{prometheus_url}/api/v1/status/config", timeout=10
            )
            if response.status_code == 200:
                self.checks.append("Prometheus is accessible")
            else:
                self.failures.append(
                    {
                        "category": "monitoring",
                        "message": f"Prometheus not accessible: {response.status_code}",
                        "severity": "high",
                    }
                )
        except Exception as e:
            self.failures.append(
                {
                    "category": "monitoring",
                    "message": f"Cannot connect to Prometheus: {e}",
                    "severity": "high",
                }
            )
        grafana_url = os.getenv("GRAFANA_URL", "http://grafana:3000")
        try:
            response = requests.get(f"{grafana_url}/api/health", timeout=10)
            if response.status_code == 200:
                self.checks.append("Grafana is accessible")
            else:
                self.warnings.append(
                    {
                        "category": "monitoring",
                        "message": f"Grafana not accessible: {response.status_code}",
                    }
                )
        except Exception as e:
            self.warnings.append(
                {"category": "monitoring", "message": f"Cannot connect to Grafana: {e}"}
            )

    def validate_logging_stack(self) -> None:
        """Validate centralized logging stack"""
        logger.info("🔍 Validating logging stack...")
        elasticsearch_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        try:
            response = requests.get(f"{elasticsearch_url}/_cluster/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") in ["green", "yellow"]:
                    self.checks.append(
                        f"Elasticsearch cluster health: {health_data.get('status')}"
                    )
                else:
                    self.failures.append(
                        {
                            "category": "logging",
                            "message": f"Elasticsearch cluster unhealthy: {health_data.get('status')}",
                            "severity": "high",
                        }
                    )
            else:
                self.failures.append(
                    {
                        "category": "logging",
                        "message": f"Elasticsearch not accessible: {response.status_code}",
                        "severity": "high",
                    }
                )
        except Exception as e:
            self.failures.append(
                {
                    "category": "logging",
                    "message": f"Cannot connect to Elasticsearch: {e}",
                    "severity": "high",
                }
            )
        kibana_url = os.getenv("KIBANA_URL", "http://kibana:5601")
        try:
            response = requests.get(f"{kibana_url}/api/status", timeout=10)
            if response.status_code == 200:
                self.checks.append("Kibana is accessible")
            else:
                self.warnings.append(
                    {
                        "category": "logging",
                        "message": f"Kibana not accessible: {response.status_code}",
                    }
                )
        except Exception as e:
            self.warnings.append(
                {"category": "logging", "message": f"Cannot connect to Kibana: {e}"}
            )

    def validate_resource_requirements(self) -> None:
        """Validate resource requirements and limits"""
        logger.info("🔍 Validating resource requirements...")
        try:
            config.load_kube_config()
            client.CoreV1Api()
            apps_v1 = client.AppsV1Api()
            deployments = apps_v1.list_deployment_for_all_namespaces()
            for deployment in deployments.items:
                deployment_name = deployment.metadata.name
                namespace = deployment.metadata.namespace
                if namespace in ["kube-system", "kube-public", "kube-node-lease"]:
                    continue
                containers = deployment.spec.template.spec.containers
                for container in containers:
                    if not container.resources or not container.resources.limits:
                        self.warnings.append(
                            {
                                "category": "resources",
                                "message": f"Container {container.name} in {deployment_name} missing resource limits",
                            }
                        )
                    else:
                        self.checks.append(
                            f"Resource limits set for {container.name} in {deployment_name}"
                        )
                    if not container.resources or not container.resources.requests:
                        self.warnings.append(
                            {
                                "category": "resources",
                                "message": f"Container {container.name} in {deployment_name} missing resource requests",
                            }
                        )
                    if not container.liveness_probe:
                        self.warnings.append(
                            {
                                "category": "resources",
                                "message": f"Container {container.name} in {deployment_name} missing liveness probe",
                            }
                        )
                    if not container.readiness_probe:
                        self.warnings.append(
                            {
                                "category": "resources",
                                "message": f"Container {container.name} in {deployment_name} missing readiness probe",
                            }
                        )
        except Exception as e:
            self.warnings.append(
                {
                    "category": "resources",
                    "message": f"Cannot validate Kubernetes resources: {e}",
                }
            )

    def validate_backup_strategy(self) -> None:
        """Validate backup and disaster recovery strategy"""
        logger.info("🔍 Validating backup strategy...")
        backup_configs = [
            "infrastructure/scripts/backup.sh",
            "infrastructure/kubernetes/base/backup-cronjob.yaml",
            "infrastructure/terraform/modules/backup",
        ]
        backup_found = False
        for config_path in backup_configs:
            if Path(config_path).exists():
                backup_found = True
                self.checks.append(f"Backup configuration found: {config_path}")
                break
        if not backup_found:
            self.failures.append(
                {
                    "category": "backup",
                    "message": "No backup configuration found",
                    "severity": "high",
                }
            )
        backup_retention = os.getenv("BACKUP_RETENTION_DAYS")
        if backup_retention:
            try:
                retention_days = int(backup_retention)
                if retention_days >= 2555:
                    self.checks.append(
                        f"Backup retention meets compliance: {retention_days} days"
                    )
                else:
                    self.failures.append(
                        {
                            "category": "backup",
                            "message": f"Backup retention insufficient: {retention_days} days (required: 2555)",
                            "severity": "high",
                        }
                    )
            except ValueError:
                self.warnings.append(
                    {
                        "category": "backup",
                        "message": "Invalid backup retention configuration",
                    }
                )
        else:
            self.warnings.append(
                {"category": "backup", "message": "Backup retention not configured"}
            )

    def validate_network_security(self) -> None:
        """Validate network security configuration"""
        logger.info("🔍 Validating network security...")
        try:
            config.load_kube_config()
            networking_v1 = client.NetworkingV1Api()
            network_policies = networking_v1.list_network_policy_for_all_namespaces()
            if not network_policies.items:
                self.failures.append(
                    {
                        "category": "network",
                        "message": "No network policies found",
                        "severity": "high",
                    }
                )
            else:
                self.checks.append(
                    f"Found {len(network_policies.items)} network policies"
                )
            v1 = client.CoreV1Api()
            services = v1.list_service_for_all_namespaces()
            ingress_found = False
            for service in services.items:
                if (
                    "ingress" in service.metadata.name.lower()
                    or "nginx" in service.metadata.name.lower()
                ):
                    ingress_found = True
                    self.checks.append(
                        f"Ingress controller found: {service.metadata.name}"
                    )
                    break
            if not ingress_found:
                self.warnings.append(
                    {"category": "network", "message": "No ingress controller found"}
                )
        except Exception as e:
            self.warnings.append(
                {
                    "category": "network",
                    "message": f"Cannot validate network security: {e}",
                }
            )

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate deployment readiness report"""
        total_checks = len(self.checks) + len(self.warnings) + len(self.failures)
        readiness_score = (
            len(self.checks) / total_checks * 100 if total_checks > 0 else 0
        )
        critical_failures = [
            f for f in self.failures if f.get("severity") == "critical"
        ]
        deployment_ready = len(critical_failures) == 0
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "deployment_ready": deployment_ready,
            "readiness_score": round(readiness_score, 2),
            "summary": {
                "total_checks": total_checks,
                "passed": len(self.checks),
                "warnings": len(self.warnings),
                "failures": len(self.failures),
                "critical_failures": len(critical_failures),
            },
            "checks_passed": self.checks,
            "warnings": self.warnings,
            "failures": self.failures,
            "requirements": self.requirements,
            "recommendations": self._generate_recommendations(),
        }
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"📄 Deployment readiness report saved to {output_file}")
        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate deployment recommendations"""
        recommendations = []
        critical_failures = [
            f for f in self.failures if f.get("severity") == "critical"
        ]
        if critical_failures:
            recommendations.append(
                "❌ DEPLOYMENT BLOCKED: Resolve all critical failures before deployment"
            )
            for failure in critical_failures:
                recommendations.append(f"  • {failure['message']}")
        else:
            recommendations.append(
                "✅ No critical issues found - deployment can proceed"
            )
        if self.warnings:
            recommendations.append(
                "⚠️  Address warnings to improve deployment reliability:"
            )
            for warning in self.warnings[:3]:
                recommendations.append(f"  • {warning['message']}")
        if len(self.failures) > len(critical_failures):
            recommendations.append(
                "🔧 Fix high-priority issues for optimal deployment:"
            )
            high_failures = [f for f in self.failures if f.get("severity") == "high"]
            for failure in high_failures[:3]:
                recommendations.append(f"  • {failure['message']}")
        return recommendations

    def print_summary(self) -> None:
        """Print deployment readiness summary"""
        total_checks = len(self.checks) + len(self.warnings) + len(self.failures)
        readiness_score = (
            len(self.checks) / total_checks * 100 if total_checks > 0 else 0
        )
        critical_failures = [
            f for f in self.failures if f.get("severity") == "critical"
        ]
        deployment_ready = len(critical_failures) == 0
        logger.info("\n" + "=" * 60)
        logger.info("🚀 DEPLOYMENT READINESS VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.environment.upper()}")
        logger.info(f"Readiness Score: {readiness_score:.1f}%")
        logger.info(
            f"Deployment Status: {('✅ READY' if deployment_ready else '❌ BLOCKED')}"
        )
        logger.info()
        logger.info(f"📊 Summary:")
        logger.info(f"  • Total Checks: {total_checks}")
        logger.info(f"  • Passed: {len(self.checks)}")
        logger.info(f"  • Warnings: {len(self.warnings)}")
        logger.info(f"  • Failures: {len(self.failures)}")
        logger.info(f"  • Critical Failures: {len(critical_failures)}")
        logger.info()
        if critical_failures:
            logger.info("🚨 Critical Issues (Deployment Blocked):")
            for failure in critical_failures:
                logger.info(
                    f"  🔴 [{failure['category'].upper()}] {failure['message']}"
                )
            logger.info()
        if self.failures and len(self.failures) > len(critical_failures):
            logger.info("⚠️  High Priority Issues:")
            high_failures = [f for f in self.failures if f.get("severity") == "high"]
            for failure in high_failures[:5]:
                logger.info(
                    f"  🟠 [{failure['category'].upper()}] {failure['message']}"
                )
            logger.info()
        if self.warnings:
            logger.info("💡 Warnings:")
            for warning in self.warnings[:5]:
                logger.info(
                    f"  🟡 [{warning['category'].upper()}] {warning['message']}"
                )
            if len(self.warnings) > 5:
                logger.info(f"  ... and {len(self.warnings) - 5} more warnings")
            logger.info()
        logger.info("📋 Next Steps:")
        if deployment_ready:
            logger.info("  ✅ All critical requirements met")
            logger.info("  🚀 Deployment can proceed")
            logger.info("  💡 Consider addressing warnings for optimal performance")
        else:
            logger.info("  ❌ Resolve critical failures before deployment")
            logger.info("  🔧 Review infrastructure and security configuration")
            logger.info("  📞 Contact DevOps team if assistance needed")
        logger.info("=" * 60)


def main() -> Any:
    parser = argparse.ArgumentParser(description="Fluxion Deployment Validator")
    parser.add_argument(
        "--environment", default="production", help="Target environment"
    )
    parser.add_argument(
        "--validate-secrets", action="store_true", help="Validate secrets management"
    )
    parser.add_argument(
        "--validate-resources",
        action="store_true",
        help="Validate resource configuration",
    )
    parser.add_argument("--output", help="Output file for report")
    args = parser.parse_args()
    validator = DeploymentValidator(args.environment)
    logger.info("🚀 Starting Deployment Readiness Validation...")
    logger.info(f"🎯 Target environment: {args.environment}")
    logger.info()
    validator.validate_kubernetes_cluster()
    validator.validate_monitoring_stack()
    validator.validate_logging_stack()
    validator.validate_backup_strategy()
    validator.validate_network_security()
    if args.validate_secrets:
        validator.validate_secrets_management()
        validator.validate_database_connectivity()
    if args.validate_resources:
        validator.validate_resource_requirements()
    validator.generate_report(args.output)
    validator.print_summary()
    critical_failures = [
        f for f in validator.failures if f.get("severity") == "critical"
    ]
    sys.exit(0 if len(critical_failures) == 0 else 1)


if __name__ == "__main__":
    main()
