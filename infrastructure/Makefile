.PHONY: help up down build pull logs ps clean init-dirs validate \
        tf-init tf-plan tf-apply tf-destroy \
        ansible-check ansible-apply \
        k8s-apply k8s-delete k8s-status

SHELL := /bin/bash
COMPOSE := docker compose
COMPOSE_ZK := docker compose -f docker-compose.yml -f docker-compose.zk.yml
ENV_FILE := .env

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ───────────────────────────────────────────────────────────────────

init-dirs: ## Create required local data directories
	@mkdir -p data/{redis,blockchain,ml-models,prometheus,grafana,elasticsearch,vault}
	@mkdir -p config/{nginx/conf.d,nginx/ssl,prometheus/rules,grafana/provisioning/{datasources,dashboards},grafana/dashboards,filebeat}
	@echo "✓ Directories created"

up: init-dirs ## Start all services
	@[ -f $(ENV_FILE) ] || (cp .env.example $(ENV_FILE) && echo "⚠  Created .env from .env.example - please review before running again")
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: ## Build all custom images
	$(COMPOSE) build --no-cache

pull: ## Pull all base images
	$(COMPOSE) pull

logs: ## Tail logs for all services (or SERVICE=<name> for one)
	$(COMPOSE) logs -f $(SERVICE)

ps: ## Show running containers
	$(COMPOSE) ps

restart: ## Restart a service: make restart SERVICE=api
	$(COMPOSE) restart $(SERVICE)

clean: ## Stop services and remove volumes (DESTRUCTIVE)
	@echo "WARNING: This will delete all data volumes. Press Ctrl-C to cancel."
	@sleep 5
	$(COMPOSE) down -v --remove-orphans

# ZK variant
up-zk: init-dirs ## Start all services including ZK prover
	$(COMPOSE_ZK) up -d

# ─── Terraform ────────────────────────────────────────────────────────────────

ENV ?= dev
TF_DIR := terraform
TF_VARS := $(TF_DIR)/environments/$(ENV)/terraform.tfvars

tf-init: ## Init Terraform for ENV (default: dev)
	cd $(TF_DIR) && terraform init -upgrade

tf-plan: ## Plan Terraform changes for ENV
	cd $(TF_DIR) && terraform plan -var-file=environments/$(ENV)/terraform.tfvars -out=tfplan

tf-apply: ## Apply Terraform changes for ENV
	cd $(TF_DIR) && terraform apply tfplan

tf-destroy: ## Destroy Terraform resources for ENV (DESTRUCTIVE)
	cd $(TF_DIR) && terraform destroy -var-file=environments/$(ENV)/terraform.tfvars

tf-validate: ## Validate Terraform configuration
	cd $(TF_DIR) && terraform validate

# ─── Ansible ──────────────────────────────────────────────────────────────────

INVENTORY ?= ansible/inventory/hosts.yml

ansible-deps: ## Install Ansible Galaxy dependencies
	ansible-galaxy install -r ansible/requirements.yml

ansible-check: ## Dry-run Ansible playbook
	ansible-playbook -i $(INVENTORY) ansible/playbooks/main.yml --check --diff

ansible-apply: ## Apply Ansible playbook
	ansible-playbook -i $(INVENTORY) ansible/playbooks/main.yml

# ─── Kubernetes ───────────────────────────────────────────────────────────────

K8S_ENV ?= dev
K8S_BASE := kubernetes/base
K8S_ENV_DIR := kubernetes/environments/$(K8S_ENV)

k8s-apply: ## Apply Kubernetes manifests for K8S_ENV (default: dev)
	kubectl apply -f $(K8S_BASE)/
	@if [ -d $(K8S_ENV_DIR) ]; then kubectl apply -f $(K8S_ENV_DIR)/; fi

k8s-delete: ## Delete Kubernetes resources for K8S_ENV
	kubectl delete -f $(K8S_BASE)/

k8s-status: ## Show Kubernetes pod/service status
	kubectl get pods,svc,ingress -n default

# ─── Validation ───────────────────────────────────────────────────────────────

validate: ## Run infrastructure validation script
	@bash validate_infrastructure.sh
