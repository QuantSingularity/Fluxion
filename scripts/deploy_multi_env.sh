#!/bin/bash
# Multi-Environment Deployment Script for Fluxion
# This script automates the deployment of Fluxion to multiple environments
# (development, staging, production) and across multiple blockchain networks.

# Exit immediately if a command exits with a non-zero status
set -e

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
NETWORKS=("ethereum")
CONFIG_DIR="./infrastructure/deployment/configs"
DEPLOY_BACKEND=true
DEPLOY_FRONTEND=true
DEPLOY_CONTRACTS=true
SKIP_TESTS=false
SKIP_CONFIRMATION=false

# Function to display usage information
function show_usage {
    echo -e "${BLUE}Fluxion Multi-Environment Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Specify environment (development, staging, production)"
    echo "  -n, --networks NET1,NET2 Comma-separated list of blockchain networks to deploy to"
    echo "  -c, --config-dir DIR     Directory containing environment configuration files"
    echo "  --backend-only           Deploy only backend components"
    echo "  --frontend-only          Deploy only frontend components"
    echo "  --contracts-only         Deploy only smart contracts"
    echo "  --skip-tests             Skip pre-deployment tests"
    echo "  -y, --yes                Skip deployment confirmation"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Available networks: ethereum, polygon, arbitrum, optimism, avalanche, binance"
    echo "                   zksync, starknet, base, linea, scroll"
    echo ""
    echo "Example: $0 -e staging -n ethereum,polygon,arbitrum"
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

# Function to validate networks
function validate_networks {
    local valid_networks=("ethereum" "polygon" "arbitrum" "optimism" "avalanche" "binance" "zksync" "starknet" "base" "linea" "scroll")

    for network in "${NETWORKS[@]}"; do
        local valid=false
        for valid_network in "${valid_networks[@]}"; do
            if [[ "$network" == "$valid_network" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "false" ]]; then
            echo -e "${RED}Error: Invalid network '$network'${NC}"
            echo "Valid networks are: ${valid_networks[*]}"
            exit 1
        fi
    done
}

# Function to check prerequisites
function check_prerequisites {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check for required tools
    command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required but not installed${NC}"; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}Error: kubectl is required but not installed${NC}"; exit 1; }
    command -v terraform >/dev/null 2>&1 || { echo -e "${RED}Error: Terraform is required but not installed${NC}"; exit 1; }
    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: Python 3 is required but not installed${NC}"; exit 1; }
    command -v npm >/dev/null 2>&1 || { echo -e "${RED}Error: npm is required but not installed${NC}"; exit 1; }

    # Check for configuration directory
    if [[ ! -d "$CONFIG_DIR" ]]; then
        echo -e "${RED}Error: Configuration directory '$CONFIG_DIR' not found${NC}"
        exit 1
    fi

    # Check for environment configuration
    if [[ ! -f "$CONFIG_DIR/$ENVIRONMENT.env" ]]; then
        echo -e "${RED}Error: Environment configuration file '$CONFIG_DIR/$ENVIRONMENT.env' not found${NC}"
        exit 1
    fi

    echo -e "${GREEN}All prerequisites satisfied${NC}"
}

# Function to run tests before deployment
function run_tests {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        echo -e "${YELLOW}Skipping pre-deployment tests${NC}"
        return 0
    fi

    echo -e "${BLUE}Running pre-deployment tests...${NC}"

    # Run backend tests
    if [[ "$DEPLOY_BACKEND" == "true" ]]; then
        echo -e "${BLUE}Running backend tests...${NC}"
        cd code/backend
        python3 -m pytest -xvs
        cd ../..
    fi

    # Run frontend tests
    if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
        echo -e "${BLUE}Running frontend tests...${NC}"
        cd web-frontend
        npm test -- --watchAll=false
        cd ..
    fi

    # Run smart contract tests
    if [[ "$DEPLOY_CONTRACTS" == "true" ]]; then
        echo -e "${BLUE}Running smart contract tests...${NC}"
        cd code/blockchain
        forge test -vvv
        cd ../..
    fi

    echo -e "${GREEN}All tests passed successfully${NC}"
}

# Function to deploy backend
function deploy_backend {
    echo -e "${BLUE}Deploying backend to $ENVIRONMENT environment...${NC}"

    # Load environment variables
    # shellcheck source=/dev/null
    source "$CONFIG_DIR/$ENVIRONMENT.env"

    # Build Docker image
    echo -e "${BLUE}Building backend Docker image...${NC}"
    cd code/backend
    docker build -t "fluxion-backend:$ENVIRONMENT" .

    # Push to container registry
    echo -e "${BLUE}Pushing backend Docker image to registry...${NC}"
    docker tag "fluxion-backend:$ENVIRONMENT" "$CONTAINER_REGISTRY/fluxion-backend:$ENVIRONMENT"
    docker push "$CONTAINER_REGISTRY/fluxion-backend:$ENVIRONMENT"

    # Apply Kubernetes configurations
    echo -e "${BLUE}Applying Kubernetes configurations...${NC}"
    cd ../../infrastructure/kubernetes
    kubectl apply -f base/backend-deployment.yaml -f base/backend-service.yaml

    cd ../..
    echo -e "${GREEN}Backend deployment to $ENVIRONMENT completed successfully${NC}"
}

# Function to deploy frontend
function deploy_frontend {
    echo -e "${BLUE}Deploying frontend to $ENVIRONMENT environment...${NC}"

    # Load environment variables
    # shellcheck source=/dev/null
    source "$CONFIG_DIR/$ENVIRONMENT.env"

    # Build frontend
    echo -e "${BLUE}Building frontend...${NC}"
    cd web-frontend
    npm install
    npm run build

    # Deploy to CDN/hosting service based on environment
    echo -e "${BLUE}Deploying frontend to hosting service...${NC}"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Production deployment (example using AWS S3)
        aws s3 sync dist/ "s3://$FRONTEND_BUCKET" --delete
        aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DISTRIBUTION" --paths "/*"
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        # Staging deployment
        aws s3 sync dist/ "s3://$FRONTEND_BUCKET-staging" --delete
    else
        # Development deployment
        aws s3 sync dist/ "s3://$FRONTEND_BUCKET-dev" --delete
    fi

    cd ..
    echo -e "${GREEN}Frontend deployment to $ENVIRONMENT completed successfully${NC}"
}

# Function to deploy smart contracts
function deploy_contracts {
    echo -e "${BLUE}Deploying smart contracts to selected networks...${NC}"

    # Load environment variables
    # shellcheck source=/dev/null
    source "$CONFIG_DIR/$ENVIRONMENT.env"

    # For each network, deploy contracts
    for network in "${NETWORKS[@]}"; do
        echo -e "${BLUE}Deploying contracts to $network network...${NC}"

        cd code/blockchain

        # Set network-specific configuration
        export NETWORK="$network"

        # Deploy contracts using Foundry
        forge script script/Deploy.s.sol:DeployScript --rpc-url "$RPC_URL_$network" --private-key "$PRIVATE_KEY" --broadcast --verify

        # Verify contracts on block explorer if not development
        if [[ "$ENVIRONMENT" != "development" ]]; then
            echo -e "${BLUE}Verifying contracts on $network block explorer...${NC}"
            forge verify-contract --chain-id "$CHAIN_ID_$network" --compiler-version "$(forge --version)" "$(cat deployments/$network/latest.json | jq -r '.contractAddress')" "src/Fluxion.sol:Fluxion" --etherscan-api-key "$ETHERSCAN_API_KEY_$network"
        fi

        cd ../..
        echo -e "${GREEN}Smart contract deployment to $network completed successfully${NC}"
    done
}

# Function to update deployment registry
function update_deployment_registry {
    echo -e "${BLUE}Updating deployment registry...${NC}"

    # Create deployment record
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    DEPLOYMENT_ID=$(uuidgen)

    # Record deployment details
    cat > "infrastructure/deployment/registry/$DEPLOYMENT_ID.json" << EOF
{
    "id": "$DEPLOYMENT_ID",
    "timestamp": "$TIMESTAMP",
    "environment": "$ENVIRONMENT",
    "networks": [$(printf '"%s",' "${NETWORKS[@]}" | sed 's/,$//')],
    "components": {
        "backend": $DEPLOY_BACKEND,
        "frontend": $DEPLOY_FRONTEND,
        "contracts": $DEPLOY_CONTRACTS
    },
    "version": "$(git describe --tags --always)",
    "commit": "$(git rev-parse HEAD)",
    "deployer": "$(whoami)"
}
EOF

    echo -e "${GREEN}Deployment registry updated with ID: $DEPLOYMENT_ID${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--networks)
            IFS=',' read -ra NETWORKS <<< "$2"
            shift 2
            ;;
        -c|--config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --backend-only)
            DEPLOY_BACKEND=true
            DEPLOY_FRONTEND=false
            DEPLOY_CONTRACTS=false
            shift
            ;;
        --frontend-only)
            DEPLOY_BACKEND=false
            DEPLOY_FRONTEND=true
            DEPLOY_CONTRACTS=false
            shift
            ;;
        --contracts-only)
            DEPLOY_BACKEND=false
            DEPLOY_FRONTEND=false
            DEPLOY_CONTRACTS=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -y|--yes)
            SKIP_CONFIRMATION=true
            shift
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
echo -e "${BLUE}Fluxion Multi-Environment Deployment${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
echo -e "${BLUE}Networks:${NC} ${NETWORKS[*]}"
echo -e "${BLUE}Components:${NC} $([ "$DEPLOY_BACKEND" == "true" ] && echo "Backend ") $([ "$DEPLOY_FRONTEND" == "true" ] && echo "Frontend ") $([ "$DEPLOY_CONTRACTS" == "true" ] && echo "Contracts")"

# Validate inputs
validate_environment
validate_networks

# Check prerequisites
check_prerequisites

# Run tests
run_tests

# Confirm deployment
if [[ "$SKIP_CONFIRMATION" != "true" ]]; then
    read -p "Proceed with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
fi

# Perform deployment
if [[ "$DEPLOY_BACKEND" == "true" ]]; then
    deploy_backend
fi

if [[ "$DEPLOY_FRONTEND" == "true" ]]; then
    deploy_frontend
fi

if [[ "$DEPLOY_CONTRACTS" == "true" ]]; then
    deploy_contracts
fi

# Update deployment registry
update_deployment_registry

echo -e "${GREEN}Deployment to $ENVIRONMENT environment completed successfully${NC}"
