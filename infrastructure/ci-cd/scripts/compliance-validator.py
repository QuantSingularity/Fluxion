"""
Fluxion Compliance Validator
Validates infrastructure and application compliance with financial standards
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ComplianceValidator:
    """Financial compliance validator for Fluxion infrastructure"""

    def __init__(self, framework: str = "financial") -> None:
        self.framework = framework
        self.violations = []
        self.warnings = []
        self.passed_checks = []
        self.requirements = {
            "data_retention": {
                "min_years": 7,
                "description": "Financial data must be retained for at least 7 years",
            },
            "encryption": {
                "at_rest": True,
                "in_transit": True,
                "key_rotation": True,
                "description": "All data must be encrypted at rest and in transit",
            },
            "access_control": {
                "mfa_required": True,
                "rbac_enabled": True,
                "least_privilege": True,
                "session_timeout": 1800,
                "description": "Strong access controls must be implemented",
            },
            "audit_logging": {
                "enabled": True,
                "immutable": True,
                "real_time": True,
                "retention_years": 7,
                "description": "Comprehensive audit logging is required",
            },
            "network_security": {
                "segmentation": True,
                "firewall": True,
                "intrusion_detection": True,
                "description": "Network security controls must be implemented",
            },
            "backup_recovery": {
                "automated": True,
                "tested": True,
                "offsite": True,
                "rto_hours": 4,
                "rpo_hours": 1,
                "description": "Robust backup and recovery procedures required",
            },
            "vulnerability_management": {
                "scanning": True,
                "patching": True,
                "assessment_frequency": "monthly",
                "description": "Regular vulnerability assessments required",
            },
            "incident_response": {
                "plan_exists": True,
                "tested": True,
                "notification_time": 72,
                "description": "Incident response plan must be in place",
            },
        }

    def validate_kubernetes_manifests(self, k8s_path: str) -> None:
        """Validate Kubernetes manifests for compliance"""
        logger.info("🔍 Validating Kubernetes manifests...")
        k8s_dir = Path(k8s_path)
        if not k8s_dir.exists():
            self.violations.append(
                {
                    "category": "kubernetes",
                    "severity": "high",
                    "message": f"Kubernetes directory not found: {k8s_path}",
                    "requirement": "infrastructure",
                }
            )
            return
        security_files = [
            "network-policies.yaml",
            "pod-security-policy.yaml",
            "rbac.yaml",
        ]
        for file in security_files:
            file_path = k8s_dir / "base" / file
            if not file_path.exists():
                self.violations.append(
                    {
                        "category": "kubernetes",
                        "severity": "high",
                        "message": f"Missing security file: {file}",
                        "requirement": "access_control",
                    }
                )
            else:
                self.passed_checks.append(f"Security file present: {file}")
        for yaml_file in k8s_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if doc and doc.get("kind") == "Deployment":
                            self._validate_deployment_security(doc, yaml_file.name)
            except Exception as e:
                self.warnings.append(
                    {
                        "category": "kubernetes",
                        "message": f"Could not parse {yaml_file}: {e}",
                    }
                )

    def _validate_deployment_security(self, deployment: Dict, filename: str) -> None:
        """Validate deployment security configuration"""
        spec = deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})
        security_context = pod_spec.get("securityContext", {})
        if not security_context.get("runAsNonRoot"):
            self.violations.append(
                {
                    "category": "kubernetes",
                    "severity": "high",
                    "message": f"Pod not configured to run as non-root in {filename}",
                    "requirement": "access_control",
                }
            )
        containers = pod_spec.get("containers", [])
        for container in containers:
            container_security = container.get("securityContext", {})
            if container_security.get("allowPrivilegeEscalation", True):
                self.violations.append(
                    {
                        "category": "kubernetes",
                        "severity": "high",
                        "message": f"Container allows privilege escalation in {filename}",
                        "requirement": "access_control",
                    }
                )
            if not container_security.get("readOnlyRootFilesystem"):
                self.warnings.append(
                    {
                        "category": "kubernetes",
                        "message": f"Container root filesystem not read-only in {filename}",
                    }
                )
            resources = container.get("resources", {})
            if not resources.get("limits"):
                self.violations.append(
                    {
                        "category": "kubernetes",
                        "severity": "medium",
                        "message": f"Container missing resource limits in {filename}",
                        "requirement": "resource_management",
                    }
                )

    def validate_terraform_configuration(self, tf_path: str) -> None:
        """Validate Terraform configuration for compliance"""
        logger.info("🔍 Validating Terraform configuration...")
        tf_dir = Path(tf_path)
        if not tf_dir.exists():
            self.violations.append(
                {
                    "category": "terraform",
                    "severity": "high",
                    "message": f"Terraform directory not found: {tf_path}",
                    "requirement": "infrastructure",
                }
            )
            return
        required_files = ["main.tf", "variables.tf", "outputs.tf"]
        for file in required_files:
            file_path = tf_dir / file
            if not file_path.exists():
                self.violations.append(
                    {
                        "category": "terraform",
                        "severity": "medium",
                        "message": f"Missing Terraform file: {file}",
                        "requirement": "infrastructure",
                    }
                )
        main_tf = tf_dir / "main.tf"
        if main_tf.exists():
            self._validate_terraform_security(main_tf)

    def _validate_terraform_security(self, tf_file: Path) -> None:
        """Validate Terraform file for security configurations"""
        try:
            with open(tf_file, "r") as f:
                content = f.read()
            if "kms_key_id" not in content:
                self.violations.append(
                    {
                        "category": "terraform",
                        "severity": "high",
                        "message": "No KMS encryption configuration found",
                        "requirement": "encryption",
                    }
                )
            else:
                self.passed_checks.append("KMS encryption configuration present")
            if "backup_retention" not in content:
                self.violations.append(
                    {
                        "category": "terraform",
                        "severity": "high",
                        "message": "No backup retention configuration found",
                        "requirement": "backup_recovery",
                    }
                )
            if "cloudtrail" not in content.lower():
                self.violations.append(
                    {
                        "category": "terraform",
                        "severity": "high",
                        "message": "No CloudTrail configuration found",
                        "requirement": "audit_logging",
                    }
                )
            if "security_group" not in content:
                self.violations.append(
                    {
                        "category": "terraform",
                        "severity": "high",
                        "message": "No security group configuration found",
                        "requirement": "network_security",
                    }
                )
        except Exception as e:
            self.warnings.append(
                {"category": "terraform", "message": f"Could not parse {tf_file}: {e}"}
            )

    def validate_docker_configuration(self, docker_path: str) -> None:
        """Validate Docker configuration for compliance"""
        logger.info("🔍 Validating Docker configuration...")
        compose_files = [
            Path(docker_path) / "docker-compose.yml",
            Path(docker_path) / "docker-compose.yaml",
        ]
        for compose_file in compose_files:
            if compose_file.exists():
                self._validate_docker_compose(compose_file)
                break
        else:
            self.violations.append(
                {
                    "category": "docker",
                    "severity": "medium",
                    "message": "No Docker Compose file found",
                    "requirement": "infrastructure",
                }
            )

    def _validate_docker_compose(self, compose_file: Path) -> None:
        """Validate Docker Compose file for security"""
        try:
            with open(compose_file, "r") as f:
                compose_config = yaml.safe_load(f)
            services = compose_config.get("services", {})
            for service_name, service_config in services.items():
                security_opt = service_config.get("security_opt", [])
                if "no-new-privileges:true" not in security_opt:
                    self.violations.append(
                        {
                            "category": "docker",
                            "severity": "medium",
                            "message": f"Service {service_name} missing no-new-privileges",
                            "requirement": "access_control",
                        }
                    )
                if not service_config.get("user"):
                    self.warnings.append(
                        {
                            "category": "docker",
                            "message": f"Service {service_name} not running as specific user",
                        }
                    )
                if not service_config.get("read_only"):
                    self.warnings.append(
                        {
                            "category": "docker",
                            "message": f"Service {service_name} not configured as read-only",
                        }
                    )
                if not service_config.get("healthcheck"):
                    self.violations.append(
                        {
                            "category": "docker",
                            "severity": "medium",
                            "message": f"Service {service_name} missing health check",
                            "requirement": "monitoring",
                        }
                    )
        except Exception as e:
            self.warnings.append(
                {
                    "category": "docker",
                    "message": f"Could not parse {compose_file}: {e}",
                }
            )

    def validate_ansible_configuration(self, ansible_path: str) -> None:
        """Validate Ansible configuration for compliance"""
        logger.info("🔍 Validating Ansible configuration...")
        ansible_dir = Path(ansible_path)
        if not ansible_dir.exists():
            self.violations.append(
                {
                    "category": "ansible",
                    "severity": "medium",
                    "message": f"Ansible directory not found: {ansible_path}",
                    "requirement": "infrastructure",
                }
            )
            return
        security_role = ansible_dir / "roles" / "security"
        if not security_role.exists():
            self.violations.append(
                {
                    "category": "ansible",
                    "severity": "high",
                    "message": "No security role found in Ansible configuration",
                    "requirement": "access_control",
                }
            )
        else:
            self.passed_checks.append("Ansible security role present")
        main_playbook = ansible_dir / "playbooks" / "main.yml"
        if main_playbook.exists():
            self._validate_ansible_playbook(main_playbook)

    def _validate_ansible_playbook(self, playbook_file: Path) -> None:
        """Validate Ansible playbook for security"""
        try:
            with open(playbook_file, "r") as f:
                playbook = yaml.safe_load(f)
            if isinstance(playbook, list):
                for play in playbook:
                    if play.get("become") and (not play.get("become_user")):
                        self.warnings.append(
                            {
                                "category": "ansible",
                                "message": "Privilege escalation without specific user",
                            }
                        )
                    roles = play.get("roles", [])
                    security_roles = ["security", "hardening", "firewall"]
                    if not any((role in str(roles) for role in security_roles)):
                        self.warnings.append(
                            {
                                "category": "ansible",
                                "message": "No security-related roles found in playbook",
                            }
                        )
        except Exception as e:
            self.warnings.append(
                {
                    "category": "ansible",
                    "message": f"Could not parse {playbook_file}: {e}",
                }
            )

    def validate_secrets_management(self, base_path: str) -> None:
        """Validate secrets management practices"""
        logger.info("🔍 Validating secrets management...")
        base_dir = Path(base_path)
        secret_patterns = [
            "password\\s*=\\s*[\"\\'][^\"\\']+[\"\\']",
            "secret\\s*=\\s*[\"\\'][^\"\\']+[\"\\']",
            "token\\s*=\\s*[\"\\'][^\"\\']+[\"\\']",
            "key\\s*=\\s*[\"\\'][^\"\\']+[\"\\']",
            "api_key\\s*=\\s*[\"\\'][^\"\\']+[\"\\']",
        ]
        for file_path in base_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".yml",
                ".yaml",
                ".tf",
                ".py",
                ".js",
            ]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    for pattern in secret_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            self.violations.append(
                                {
                                    "category": "secrets",
                                    "severity": "critical",
                                    "message": f"Potential hardcoded secret in {file_path}",
                                    "requirement": "access_control",
                                }
                            )
                except Exception:
                    continue
        vault_configs = list(base_dir.rglob("*vault*"))
        if vault_configs:
            self.passed_checks.append("Vault configuration found")
        else:
            self.violations.append(
                {
                    "category": "secrets",
                    "severity": "high",
                    "message": "No secrets management solution (Vault) configured",
                    "requirement": "access_control",
                }
            )

    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate compliance report"""
        total_checks = (
            len(self.violations) + len(self.warnings) + len(self.passed_checks)
        )
        compliance_score = (
            len(self.passed_checks) / total_checks * 100 if total_checks > 0 else 0
        )
        report = {
            "timestamp": datetime.now().isoformat(),
            "framework": self.framework,
            "compliance_score": round(compliance_score, 2),
            "status": "COMPLIANT" if len(self.violations) == 0 else "NON_COMPLIANT",
            "summary": {
                "total_checks": total_checks,
                "passed": len(self.passed_checks),
                "warnings": len(self.warnings),
                "violations": len(self.violations),
            },
            "violations": self.violations,
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
            "requirements": self.requirements,
        }
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"📄 Compliance report saved to {output_file}")
        return report

    def print_summary(self) -> None:
        """Print compliance summary"""
        total_checks = (
            len(self.violations) + len(self.warnings) + len(self.passed_checks)
        )
        compliance_score = (
            len(self.passed_checks) / total_checks * 100 if total_checks > 0 else 0
        )
        logger.info("\n" + "=" * 60)
        logger.info("🏛️  FINANCIAL COMPLIANCE VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Framework: {self.framework.upper()}")
        logger.info(f"Compliance Score: {compliance_score:.1f}%")
        logger.info(
            f"Status: {('✅ COMPLIANT' if len(self.violations) == 0 else '❌ NON-COMPLIANT')}"
        )
        logger.info()
        logger.info(f"📊 Summary:")
        logger.info(f"  • Total Checks: {total_checks}")
        logger.info(f"  • Passed: {len(self.passed_checks)}")
        logger.info(f"  • Warnings: {len(self.warnings)}")
        logger.info(f"  • Violations: {len(self.violations)}")
        logger.info()
        if self.violations:
            logger.info("🚨 Critical Violations:")
            for violation in self.violations:
                severity_icon = (
                    "🔴"
                    if violation["severity"] == "critical"
                    else "🟠" if violation["severity"] == "high" else "🟡"
                )
                logger.info(
                    f"  {severity_icon} [{violation['category'].upper()}] {violation['message']}"
                )
            logger.info()
        if self.warnings:
            logger.info("⚠️  Warnings:")
            for warning in self.warnings[:5]:
                logger.info(
                    f"  🟡 [{warning['category'].upper()}] {warning['message']}"
                )
            if len(self.warnings) > 5:
                logger.info(f"  ... and {len(self.warnings) - 5} more warnings")
            logger.info()
        logger.info("✅ Recommendations:")
        if len(self.violations) == 0:
            logger.info("  • All critical compliance requirements are met")
            logger.info("  • Consider addressing warnings to improve security posture")
        else:
            logger.info(
                "  • Address all critical violations before production deployment"
            )
            logger.info("  • Implement missing security controls")
            logger.info("  • Review and update security policies")
        logger.info("=" * 60)


def main() -> Any:
    parser = argparse.ArgumentParser(description="Fluxion Compliance Validator")
    parser.add_argument("--framework", default="financial", help="Compliance framework")
    parser.add_argument("--path", default=".", help="Path to validate")
    parser.add_argument("--output", help="Output file for report")
    parser.add_argument(
        "--kubernetes",
        default="infrastructure/kubernetes",
        help="Kubernetes manifests path",
    )
    parser.add_argument(
        "--terraform",
        default="infrastructure/terraform",
        help="Terraform configuration path",
    )
    parser.add_argument(
        "--ansible", default="infrastructure/ansible", help="Ansible configuration path"
    )
    parser.add_argument(
        "--docker", default="infrastructure", help="Docker configuration path"
    )
    args = parser.parse_args()
    validator = ComplianceValidator(args.framework)
    logger.info("🏛️  Starting Financial Compliance Validation...")
    logger.info(f"📁 Base path: {args.path}")
    logger.info()
    validator.validate_kubernetes_manifests(args.kubernetes)
    validator.validate_terraform_configuration(args.terraform)
    validator.validate_ansible_configuration(args.ansible)
    validator.validate_docker_configuration(args.docker)
    validator.validate_secrets_management(args.path)
    validator.generate_report(args.output)
    validator.print_summary()
    sys.exit(0 if len(validator.violations) == 0 else 1)


if __name__ == "__main__":
    main()
