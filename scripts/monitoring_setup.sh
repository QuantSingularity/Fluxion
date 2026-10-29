#!/bin/bash
# Monitoring and Alerting Script for Fluxion
# This script sets up and manages monitoring for Fluxion components
# across multiple environments and blockchain networks.

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
COMPONENTS=("backend" "frontend" "blockchain" "database" "ai")
CONFIG_DIR="./infrastructure/monitoring/configs"
ALERT_CHANNELS=("slack" "email")
DASHBOARD_ONLY=false
INSTALL_DEPS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Function to display usage information
function show_usage {
    echo -e "${BLUE}Fluxion Monitoring and Alerting Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV       Specify environment (development, staging, production)"
    echo "  -c, --components COMP1,COMP2 Comma-separated list of components to monitor"
    echo "  --config-dir DIR            Directory containing monitoring configuration files"
    echo "  -a, --alert-channels CH1,CH2 Comma-separated list of alert channels"
    echo "  --dashboard-only            Only set up dashboards, don't configure alerts"
    echo "  --no-install                Skip installation of dependencies"
    echo "  --prometheus-port PORT      Port for Prometheus server"
    echo "  --grafana-port PORT         Port for Grafana server"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Available components: backend, frontend, blockchain, database, ai, infrastructure"
    echo "Available alert channels: slack, email, pagerduty, webhook, telegram"
    echo ""
    echo "Example: $0 -e production -c backend,blockchain,database -a slack,email"
}

# Function to validate environment
function validate_environment {
    case "$ENVIRONMENT" in
        development|staging|production)
            return 0
            ;;
        *)
            echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
            echo "Valid environments are: development, staging, production"
            exit 1
            ;;
    esac
}

# Function to validate components
function validate_components {
    local valid_components=("backend" "frontend" "blockchain" "database" "ai" "infrastructure")

    for component in "${COMPONENTS[@]}"; do
        local valid=false
        for valid_component in "${valid_components[@]}"; do
            if [[ "$component" == "$valid_component" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "false" ]]; then
            echo -e "${RED}Error: Invalid component '$component'${NC}"
            echo "Valid components are: ${valid_components[*]}"
            exit 1
        fi
    done
}

# Function to validate alert channels
function validate_alert_channels {
    local valid_channels=("slack" "email" "pagerduty" "webhook" "telegram")

    for channel in "${ALERT_CHANNELS[@]}"; do
        local valid=false
        for valid_channel in "${valid_channels[@]}"; do
            if [[ "$channel" == "$valid_channel" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "false" ]]; then
            echo -e "${RED}Error: Invalid alert channel '$channel'${NC}"
            echo "Valid alert channels are: ${valid_channels[*]}"
            exit 1
        fi
    done
}

# Function to check prerequisites
function check_prerequisites {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check for Docker if we're installing dependencies
    if [[ "$INSTALL_DEPS" == "true" ]]; then
        command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required but not installed${NC}"; exit 1; }
        command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Error: Docker Compose is required but not installed${NC}"; exit 1; }
    fi

    # Check for configuration directory
    if [[ ! -d "$CONFIG_DIR" ]]; then
        echo -e "${RED}Error: Configuration directory '$CONFIG_DIR' not found${NC}"
        exit 1
    fi

    # Check for environment configuration
    if [[ ! -f "$CONFIG_DIR/$ENVIRONMENT.yaml" ]]; then
        echo -e "${RED}Error: Environment configuration file '$CONFIG_DIR/$ENVIRONMENT.yaml' not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}All prerequisites satisfied${NC}"
}

# Function to install monitoring stack
function install_monitoring_stack {
    if [[ "$INSTALL_DEPS" != "true" ]]; then
        echo -e "${YELLOW}Skipping installation of monitoring stack${NC}"
        return 0
    fi

    echo -e "${BLUE}Installing monitoring stack...${NC}"

    # Create monitoring directory
    mkdir -p monitoring

    # Create docker-compose.yml for monitoring stack
    cat > monitoring/docker-compose.yml << EOF
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: fluxion-prometheus
    ports:
      - "${PROMETHEUS_PORT}:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: fluxion-grafana
    ports:
      - "${GRAFANA_PORT}:3000"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=fluxion
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: fluxion-node-exporter
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped
    expose:
      - 9100

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: fluxion-cadvisor
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    restart: unless-stopped
    expose:
      - 8080

  alertmanager:
    image: prom/alertmanager:latest
    container_name: fluxion-alertmanager
    volumes:
      - ./alertmanager:/etc/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped
    expose:
      - 9093

volumes:
  prometheus_data:
  grafana_data:
EOF

    # Create directories for configuration
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/provisioning/datasources
    mkdir -p monitoring/grafana/provisioning/dashboards
    mkdir -p monitoring/alertmanager

    # Create Prometheus configuration
    cat > monitoring/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
EOF

    # Create Prometheus rules directory
    mkdir -p monitoring/prometheus/rules

    # Create Grafana datasource
    cat > monitoring/grafana/provisioning/datasources/datasource.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

    # Create Grafana dashboard configuration
    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'Fluxion'
    orgId: 1
    folder: 'Fluxion'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # Create AlertManager configuration
    cat > monitoring/alertmanager/alertmanager.yml << EOF
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default'

receivers:
  - name: 'default'
    # Configure receivers based on alert channels
EOF

    # Start monitoring stack
    echo -e "${BLUE}Starting monitoring stack...${NC}"
    cd monitoring
    docker-compose up -d
    cd ..

    echo -e "${GREEN}Monitoring stack installed successfully${NC}"
}

# Function to configure component monitoring
function configure_component_monitoring {
    echo -e "${BLUE}Configuring component monitoring...${NC}"

    # For each component, configure monitoring
    for component in "${COMPONENTS[@]}"; do
        echo -e "${BLUE}Configuring monitoring for $component...${NC}"

        # Add component-specific scrape configuration to Prometheus
        case "$component" in
            backend)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:8000']
        labels:
          environment: '$ENVIRONMENT'
          component: 'backend'
EOF
                ;;
            frontend)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-frontend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:3000']
        labels:
          environment: '$ENVIRONMENT'
          component: 'frontend'
EOF
                ;;
            blockchain)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-blockchain'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:9545']
        labels:
          environment: '$ENVIRONMENT'
          component: 'blockchain'
EOF
                ;;
            database)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-database'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:9187']
        labels:
          environment: '$ENVIRONMENT'
          component: 'database'
EOF
                ;;
            ai)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-ai'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:8501']
        labels:
          environment: '$ENVIRONMENT'
          component: 'ai'
EOF
                ;;
            infrastructure)
                cat >> monitoring/prometheus/prometheus.yml << EOF

  - job_name: 'fluxion-infrastructure'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['host.docker.internal:9100']
        labels:
          environment: '$ENVIRONMENT'
          component: 'infrastructure'
EOF
                ;;
        esac

        # Copy component-specific dashboard to Grafana
        cp "$CONFIG_DIR/dashboards/$component.json" "monitoring/grafana/provisioning/dashboards/$component-$ENVIRONMENT.json"

        # Update dashboard with environment information
        sed -i "s/\${DS_PROMETHEUS}/Prometheus/g" "monitoring/grafana/provisioning/dashboards/$component-$ENVIRONMENT.json"
        sed -i "s/\${ENV}/$ENVIRONMENT/g" "monitoring/grafana/provisioning/dashboards/$component-$ENVIRONMENT.json"

        # Add component-specific alert rules
        if [[ "$DASHBOARD_ONLY" != "true" ]]; then
            cp "$CONFIG_DIR/rules/$component.yml" "monitoring/prometheus/rules/$component-$ENVIRONMENT.yml"

            # Update alert rules with environment information
            sed -i "s/\${ENV}/$ENVIRONMENT/g" "monitoring/prometheus/rules/$component-$ENVIRONMENT.yml"
        fi
    done

    echo -e "${GREEN}Component monitoring configured successfully${NC}"
}

# Function to configure alert channels
function configure_alert_channels {
    if [[ "$DASHBOARD_ONLY" == "true" ]]; then
        echo -e "${YELLOW}Skipping alert channel configuration (dashboard-only mode)${NC}"
        return 0
    fi

    echo -e "${BLUE}Configuring alert channels...${NC}"

    # Start with empty receivers section
    cat > monitoring/alertmanager/alertmanager.yml << EOF
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default'

receivers:
EOF

    # Configure receivers based on alert channels
    local receivers=""
    for channel in "${ALERT_CHANNELS[@]}"; do
        case "$channel" in
            slack)
                # Load Slack configuration from environment file
                source "$CONFIG_DIR/channels/slack.env"

                receivers+="  - name: 'slack'\n"
                receivers+="    slack_configs:\n"
                receivers+="      - api_url: '$SLACK_WEBHOOK_URL'\n"
                receivers+="        channel: '$SLACK_CHANNEL'\n"
                receivers+="        send_resolved: true\n"
                ;;
            email)
                # Load email configuration from environment file
                source "$CONFIG_DIR/channels/email.env"

                receivers+="  - name: 'email'\n"
                receivers+="    email_configs:\n"
                receivers+="      - to: '$EMAIL_TO'\n"
                receivers+="        from: '$EMAIL_FROM'\n"
                receivers+="        smarthost: '$EMAIL_SMARTHOST'\n"
                receivers+="        auth_username: '$EMAIL_AUTH_USERNAME'\n"
                receivers+="        auth_password: '$EMAIL_AUTH_PASSWORD'\n"
                receivers+="        send_resolved: true\n"
                ;;
            pagerduty)
                # Load PagerDuty configuration from environment file
                source "$CONFIG_DIR/channels/pagerduty.env"

                receivers+="  - name: 'pagerduty'\n"
                receivers+="    pagerduty_configs:\n"
                receivers+="      - service_key: '$PAGERDUTY_SERVICE_KEY'\n"
                receivers+="        send_resolved: true\n"
                ;;
            webhook)
                # Load webhook configuration from environment file
                source "$CONFIG_DIR/channels/webhook.env"

                receivers+="  - name: 'webhook'\n"
                receivers+="    webhook_configs:\n"
                receivers+="      - url: '$WEBHOOK_URL'\n"
                receivers+="        send_resolved: true\n"
                ;;
            telegram)
                # Load Telegram configuration from environment file
                source "$CONFIG_DIR/channels/telegram.env"

                receivers+="  - name: 'telegram'\n"
                receivers+="    webhook_configs:\n"
                receivers+="      - url: 'https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage'\n"
                receivers+="        send_resolved: true\n"
                receivers+="        http_config:\n"
                receivers+="          bearer_token: '$TELEGRAM_BOT_TOKEN'\n"
                receivers+="        max_alerts: 5\n"
                ;;
        esac
    done

    # Add receivers to AlertManager configuration
    echo -e "$receivers" >> monitoring/alertmanager/alertmanager.yml

    # Update route to include all receivers
    sed -i "s/receiver: 'default'/receiver: '${ALERT_CHANNELS[0]}'/" monitoring/alertmanager/alertmanager.yml

    # Add routes for each receiver
    local routes=""
    routes+="  routes:\n"
    for channel in "${ALERT_CHANNELS[@]}"; do
        routes+="    - receiver: '$channel'\n"
        routes+="      group_by: ['alertname', 'job']\n"
        routes+="      match:\n"
        routes+="        severity: '$channel'\n"
    done

    # Add routes to AlertManager configuration
    sed -i "/repeat_interval: 12h/a\\$routes" monitoring/alertmanager/alertmanager.yml

    echo -e "${GREEN}Alert channels configured successfully${NC}"
}

# Function to reload monitoring configuration
function reload_monitoring_configuration {
    echo -e "${BLUE}Reloading monitoring configuration...${NC}"

    # Reload Prometheus configuration
    curl -X POST http://localhost:$PROMETHEUS_PORT/-/reload

    # Reload AlertManager configuration
    curl -X POST http://localhost:9093/-/reload

    echo -e "${GREEN}Monitoring configuration reloaded successfully${NC}"
}

# Function to generate monitoring documentation
function generate_documentation {
    echo -e "${BLUE}Generating monitoring documentation...${NC}"

    # Create documentation directory
    mkdir -p monitoring/documentation

    # Generate main documentation file
    cat > monitoring/documentation/README.md << EOF
# Fluxion Monitoring and Alerting

## Overview

This document provides information about the monitoring and alerting setup for Fluxion in the $ENVIRONMENT environment.

## Components Monitored

The following components are being monitored:

$(for component in "${COMPONENTS[@]}"; do echo "- $component"; done)

## Alert Channels

Alerts are being sent to the following channels:

$(for channel in "${ALERT_CHANNELS[@]}"; do echo "- $channel"; done)

## Accessing Monitoring

- Prometheus: http://localhost:$PROMETHEUS_PORT
- Grafana: http://localhost:$GRAFANA_PORT (admin/fluxion)

## Dashboards

The following dashboards are available in Grafana:

$(for component in "${COMPONENTS[@]}"; do echo "- $component"; done)

## Alert Rules

$(if [[ "$DASHBOARD_ONLY" == "true" ]]; then echo "Alert rules are not configured (dashboard-only mode)."; else echo "Alert rules are configured for all monitored components."; fi)

## Maintenance

To reload the configuration:

\`\`\`bash
curl -X POST http://localhost:$PROMETHEUS_PORT/-/reload
curl -X POST http://localhost:9093/-/reload
\`\`\`

To restart the monitoring stack:

\`\`\`bash
cd monitoring
docker-compose restart
\`\`\`

To stop the monitoring stack:

\`\`\`bash
cd monitoring
docker-compose down
\`\`\`
EOF

    echo -e "${GREEN}Documentation generated successfully${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--components)
            IFS=',' read -ra COMPONENTS <<< "$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -a|--alert-channels)
            IFS=',' read -ra ALERT_CHANNELS <<< "$2"
            shift 2
            ;;
        --dashboard-only)
            DASHBOARD_ONLY=true
            shift
            ;;
        --no-install)
            INSTALL_DEPS=false
            shift
            ;;
        --prometheus-port)
            PROMETHEUS_PORT="$2"
            shift 2
            ;;
        --grafana-port)
            GRAFANA_PORT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
echo -e "${BLUE}Fluxion Monitoring and Alerting${NC}"
echo -e "${BLUE}=============================${NC}"
echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
echo -e "${BLUE}Components:${NC} ${COMPONENTS[*]}"
echo -e "${BLUE}Alert Channels:${NC} ${ALERT_CHANNELS[*]}"
echo -e "${BLUE}Dashboard Only:${NC} $DASHBOARD_ONLY"
echo -e "${BLUE}Install Dependencies:${NC} $INSTALL_DEPS"
echo -e "${BLUE}Prometheus Port:${NC} $PROMETHEUS_PORT"
echo -e "${BLUE}Grafana Port:${NC} $GRAFANA_PORT"

# Validate inputs
validate_environment
validate_components
validate_alert_channels

# Check prerequisites
check_prerequisites

# Install monitoring stack
install_monitoring_stack

# Configure component monitoring
configure_component_monitoring

# Configure alert channels
configure_alert_channels

# Reload monitoring configuration
reload_monitoring_configuration

# Generate documentation
generate_documentation

echo -e "${GREEN}Monitoring and alerting setup completed successfully${NC}"
echo -e "${GREEN}Prometheus: http://localhost:$PROMETHEUS_PORT${NC}"
echo -e "${GREEN}Grafana: http://localhost:$GRAFANA_PORT (admin/fluxion)${NC}"
echo -e "${GREEN}Documentation: monitoring/documentation/README.md${NC}"
