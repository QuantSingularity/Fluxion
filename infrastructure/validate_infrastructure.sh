#!/bin/bash
# Fluxion Infrastructure Validation Script
set -euo pipefail

ERRORS=0
WARNINGS=0
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

pass()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()    { echo -e "  ${YELLOW}⚠${NC} $1"; WARNINGS=$((WARNINGS+1)); }
fail()    { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }

echo "═══════════════════════════════════════════"
echo "  Fluxion Infrastructure Validation"
echo "═══════════════════════════════════════════"

# ── Docker Compose ────────────────────────────────────────────────────────────
echo ""
echo "▶ Docker Compose"

if command -v docker &>/dev/null; then
  pass "Docker is installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
else
  fail "Docker is not installed"
fi

if command -v docker &>/dev/null && docker compose version &>/dev/null 2>&1; then
  pass "Docker Compose v2 is available"
elif command -v docker-compose &>/dev/null; then
  warn "Only docker-compose v1 found - recommend upgrading to Docker Compose v2"
else
  fail "Docker Compose is not installed"
fi

if [ -f "docker-compose.yml" ]; then
  if ! command -v docker &>/dev/null; then
    warn "Skipping docker-compose.yml validation - Docker not installed"
  elif docker compose config -q 2>/dev/null; then
    pass "docker-compose.yml is valid"
  else
    fail "docker-compose.yml has syntax errors"
  fi
else
  fail "docker-compose.yml not found"
fi

if [ -f ".env" ]; then
  pass ".env file exists"
  # Check for placeholder values
  if grep -q "change-me" .env 2>/dev/null; then
    warn ".env contains placeholder 'change-me' values - update before deploying"
  fi
else
  warn ".env file missing - copy from .env.example"
fi

# ── Terraform ─────────────────────────────────────────────────────────────────
echo ""
echo "▶ Terraform"

if command -v terraform &>/dev/null; then
  TF_VER=$(terraform version -json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['terraform_version'])" 2>/dev/null || terraform version | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
  pass "Terraform is installed (v${TF_VER})"
  REQUIRED_TF="1.0"
  if python3 -c "import sys; v='${TF_VER}'.split('.'); r='${REQUIRED_TF}'.split('.'); sys.exit(0 if (int(v[0]),int(v[1])) >= (int(r[0]),int(r[1])) else 1)" 2>/dev/null; then
    pass "Terraform version >= ${REQUIRED_TF}"
  else
    fail "Terraform version ${TF_VER} < required ${REQUIRED_TF}"
  fi
else
  warn "Terraform is not installed - required for cloud provisioning"
fi

if [ -d "terraform" ]; then
  if command -v terraform &>/dev/null; then
    cd terraform
    if terraform validate -no-color &>/dev/null 2>&1; then
      pass "Terraform configuration is valid"
    else
      fail "Terraform validation failed - run: cd terraform && terraform validate"
    fi
    cd ..
  fi
else
  fail "terraform/ directory not found"
fi

for env in dev staging prod; do
  if [ -f "terraform/environments/${env}/terraform.tfvars" ]; then
    pass "terraform/environments/${env}/terraform.tfvars exists"
    if grep -q "Password123!" "terraform/environments/${env}/terraform.tfvars" 2>/dev/null; then
      fail "terraform/environments/${env}/terraform.tfvars contains hardcoded password"
    fi
  else
    warn "terraform/environments/${env}/terraform.tfvars missing"
  fi
done

# ── Ansible ───────────────────────────────────────────────────────────────────
echo ""
echo "▶ Ansible"

if command -v ansible &>/dev/null; then
  pass "Ansible is installed ($(ansible --version | head -1))"
else
  warn "Ansible is not installed - required for server configuration"
fi

if command -v ansible-playbook &>/dev/null; then
  if ansible-playbook --syntax-check ansible/playbooks/main.yml \
      -i ansible/inventory/hosts.yml \
      --extra-vars "app_name=fluxion db_root_password=x db_password=x db_backup_password=x db_monitor_password=x" \
      &>/dev/null 2>&1; then
    pass "Ansible playbook syntax is valid"
  else
    warn "Ansible playbook syntax check failed (may need Galaxy roles installed)"
  fi
fi

for role in common database security webserver; do
  if [ -d "ansible/roles/${role}" ]; then
    pass "Ansible role '${role}' exists"
  else
    fail "Ansible role '${role}' is missing"
  fi
done

# ── Kubernetes ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Kubernetes"

if command -v kubectl &>/dev/null; then
  pass "kubectl is installed"
else
  warn "kubectl is not installed - required for Kubernetes deployments"
fi

if command -v kubectl &>/dev/null; then
  for manifest in kubernetes/base/*.yaml; do
    if kubectl apply --dry-run=client -f "$manifest" &>/dev/null 2>&1; then
      pass "$(basename $manifest) is valid"
    else
      fail "$(basename $manifest) failed dry-run validation"
    fi
  done
else
  # Fallback: basic YAML check
  if command -v python3 &>/dev/null; then
    for manifest in kubernetes/base/*.yaml; do
      if python3 -c "
import sys
try:
  import yaml
  list(yaml.safe_load_all(open('$manifest')))
  sys.exit(0)
except Exception as e:
  print(e, file=sys.stderr)
  sys.exit(1)
" 2>/dev/null; then
        pass "$(basename $manifest) YAML is valid"
      else
        fail "$(basename $manifest) has YAML errors"
      fi
    done
  fi
fi

# ── Security Checks ───────────────────────────────────────────────────────────
echo ""
echo "▶ Security"

# Check for hardcoded secrets in tracked files
SECRET_PATTERNS=('password.*=.*["\x27][^${}][^"\x27]*["\x27]' 'secret.*=.*["\x27][^${}][^"\x27]*["\x27]' 'Password123' 'prod-password' 'prod-jwt-secret')
FOUND_SECRETS=0
for pattern in "${SECRET_PATTERNS[@]}"; do
  MATCHES=$(grep -rniE "$pattern" \
    --include="*.yml" --include="*.yaml" --include="*.tf" --include="*.tfvars" \
    --exclude-dir=".git" \
    --exclude="*.example" \
    --exclude="all.example" \
    --exclude="terraform.tfvars.example" \
    . 2>/dev/null | grep -v "^Binary" | grep -v "# " || true)
  if [ -n "$MATCHES" ]; then
    fail "Possible hardcoded secret found (pattern: ${pattern})"
    echo "$MATCHES" | head -3 | sed 's/^/      /'
    FOUND_SECRETS=1
  fi
done
[ $FOUND_SECRETS -eq 0 ] && pass "No obvious hardcoded secrets found"

if [ -f ".gitignore" ] && grep -q "^\.env$" .gitignore 2>/dev/null; then
  pass ".env is in .gitignore"
else
  fail ".env is NOT in .gitignore - add it immediately"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Summary"
echo "═══════════════════════════════════════════"
echo -e "  Errors:   ${RED}${ERRORS}${NC}"
echo -e "  Warnings: ${YELLOW}${WARNINGS}${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "  ${GREEN}All checks passed!${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "  ${YELLOW}Passed with warnings - review before deploying.${NC}"
  exit 0
else
  echo -e "  ${RED}Validation failed - fix errors before deploying.${NC}"
  exit 1
fi
