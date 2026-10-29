#!/bin/bash
# Cross-Chain Testing Script for Fluxion
# This script automates testing of Fluxion's cross-chain functionality
# across multiple blockchain networks.

# Exit immediately if a command exits with a non-zero status
set -e

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default values
TEST_NETWORKS=("ethereum" "polygon" "arbitrum" "optimism")
TEST_TYPES=("unit" "integration" "e2e")
PARALLEL=false
REPORT_DIR="./test-reports"
VERBOSE=false
TIMEOUT=300 # seconds
CONFIG_DIR="./infrastructure/test/configs"

# Function to display usage information
function show_usage {
    echo -e "${BLUE}Fluxion Cross-Chain Testing Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -n, --networks NET1,NET2 Comma-separated list of blockchain networks to test"
    echo "  -t, --test-types TYPE1,TYPE2 Comma-separated list of test types to run"
    echo "  -p, --parallel         Run tests in parallel across networks"
    echo "  -r, --report-dir DIR   Directory to store test reports"
    echo "  -v, --verbose          Enable verbose output"
    echo "  --timeout SECONDS      Timeout for each test in seconds"
    echo "  -c, --config-dir DIR   Directory containing test configuration files"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Available networks: ethereum, polygon, arbitrum, optimism, avalanche, binance"
    echo "                   zksync, starknet, base, linea, scroll"
    echo ""
    echo "Available test types: unit, integration, e2e, liquidity, messaging, settlement"
    echo ""
    echo "Example: $0 -n ethereum,polygon -t unit,integration -p"
}

# Function to validate networks
function validate_networks {
    local valid_networks=("ethereum" "polygon" "arbitrum" "optimism" "avalanche" "binance" "zksync" "starknet" "base" "linea" "scroll")

    for network in "${TEST_NETWORKS[@]}"; do
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

# Function to validate test types
function validate_test_types {
    local valid_types=("unit" "integration" "e2e" "liquidity" "messaging" "settlement")

    for type in "${TEST_TYPES[@]}"; do
        local valid=false
        for valid_type in "${valid_types[@]}"; do
            if [[ "$type" == "$valid_type" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "false" ]]; then
            echo -e "${RED}Error: Invalid test type '$type'${NC}"
            echo "Valid test types are: ${valid_types[*]}"
            exit 1
        fi
    done
}

# Function to check prerequisites
function check_prerequisites {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check for required tools
    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: Python 3 is required but not installed${NC}"; exit 1; }
    command -v forge >/dev/null 2>&1 || { echo -e "${RED}Error: Foundry is required but not installed${NC}"; exit 1; }
    command -v npm >/dev/null 2>&1 || { echo -e "${RED}Error: npm is required but not installed${NC}"; exit 1; }

    # Check for configuration directory
    if [[ ! -d "$CONFIG_DIR" ]]; then
        echo -e "${RED}Error: Configuration directory '$CONFIG_DIR' not found${NC}"
        exit 1
    fi

    # Create report directory if it doesn't exist
    mkdir -p "$REPORT_DIR"

    echo -e "${GREEN}All prerequisites satisfied${NC}"
}

# Function to setup test environment
function setup_test_environment {
    echo -e "${BLUE}Setting up test environment...${NC}"

    # Create Python virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        echo -e "${BLUE}Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install test dependencies
    echo -e "${BLUE}Installing test dependencies...${NC}"
    if [ -f code/backend/requirements-test.txt ]; then
        pip install -r code/backend/requirements-test.txt
    else
        pip install -r code/backend/requirements.txt
    fi

    # Install Ganache for local blockchain testing
    npm install -g ganache

    echo -e "${GREEN}Test environment setup completed${NC}"
}

# Function to start local blockchain nodes
function start_local_blockchains {
    echo -e "${BLUE}Starting local blockchain nodes...${NC}"

    # Create directory for blockchain data
    mkdir -p .blockchain-data

    # Start local blockchain nodes for each network
    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Starting local $network node...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Start Ganache with network-specific parameters
        PORT="${NETWORK_PORT:-8545}"
        CHAIN_ID="${NETWORK_CHAIN_ID:-1337}"

        ganache --port "$PORT" --chain.chainId "$CHAIN_ID" --wallet.mnemonic "$NETWORK_MNEMONIC" --database.dbPath ".blockchain-data/$network" > ".blockchain-data/$network.log" 2>&1 &
        BLOCKCHAIN_PIDS+=($!)

        echo -e "${GREEN}Local $network node started on port $PORT with chain ID $CHAIN_ID${NC}"
    done

    # Wait for nodes to initialize
    echo -e "${BLUE}Waiting for blockchain nodes to initialize...${NC}"
    sleep 5
}

# Function to run unit tests
function run_unit_tests {
    echo -e "${BLUE}Running unit tests...${NC}"

    # Run smart contract unit tests
    echo -e "${BLUE}Running smart contract unit tests...${NC}"
    cd code/blockchain

    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Testing on $network...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Run Foundry tests with network-specific parameters
        FOUNDRY_PROFILE="$network" forge test --match-path "test/unit/**/*.sol" -vv
    done

    cd ../..

    # Run backend unit tests
    echo -e "${BLUE}Running backend unit tests...${NC}"
    cd code/backend
    python -m pytest tests/unit -v
    cd ../..

    echo -e "${GREEN}Unit tests completed successfully${NC}"
}

# Function to run integration tests
function run_integration_tests {
    echo -e "${BLUE}Running integration tests...${NC}"

    # Run smart contract integration tests
    echo -e "${BLUE}Running smart contract integration tests...${NC}"
    cd code/blockchain

    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Testing on $network...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Run Foundry tests with network-specific parameters
        FOUNDRY_PROFILE="$network" forge test --match-path "test/integration/**/*.sol" -vv
    done

    cd ../..

    # Run backend integration tests
    echo -e "${BLUE}Running backend integration tests...${NC}"
    cd code/backend
    python -m pytest tests/integration -v
    cd ../..

    echo -e "${GREEN}Integration tests completed successfully${NC}"
}

# Function to run end-to-end tests
function run_e2e_tests {
    echo -e "${BLUE}Running end-to-end tests...${NC}"

    # Start backend services
    echo -e "${BLUE}Starting backend services...${NC}"
    cd code/backend
    python app.py --test-mode &
    BACKEND_PID=$!
    cd ../..

    # Wait for backend to start
    echo -e "${BLUE}Waiting for backend to start...${NC}"
    sleep 5

    # Run end-to-end tests
    echo -e "${BLUE}Running end-to-end tests...${NC}"
    if [ ! -d code/e2e ]; then
        echo -e "${YELLOW}Warning: code/e2e directory not found; skipping end-to-end tests.${NC}"
        return 0
    fi
    cd code/e2e

    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Testing on $network...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Run end-to-end tests with network-specific parameters
        NETWORK="$network" npm test
    done

    cd ../..

    # Stop backend services
    echo -e "${BLUE}Stopping backend services...${NC}"
    kill $BACKEND_PID

    echo -e "${GREEN}End-to-end tests completed successfully${NC}"
}

# Function to run cross-chain messaging tests
function run_messaging_tests {
    echo -e "${BLUE}Running cross-chain messaging tests...${NC}"

    # Need at least two networks for cross-chain testing
    if [[ ${#TEST_NETWORKS[@]} -lt 2 ]]; then
        echo -e "${YELLOW}Warning: Cross-chain messaging tests require at least two networks${NC}"
        echo -e "${YELLOW}Skipping messaging tests${NC}"
        return
    fi

    # Run cross-chain messaging tests
    cd code/blockchain

    # For each pair of networks, test messaging
    for ((i=0; i<${#TEST_NETWORKS[@]}; i++)); do
        for ((j=i+1; j<${#TEST_NETWORKS[@]}; j++)); do
            source_network="${TEST_NETWORKS[$i]}"
            target_network="${TEST_NETWORKS[$j]}"

            echo -e "${BLUE}Testing messaging from $source_network to $target_network...${NC}"

            # Load network-specific configurations
            # shellcheck source=/dev/null
            source "$CONFIG_DIR/$source_network.env"
            # shellcheck source=/dev/null
            source "$CONFIG_DIR/$target_network.env"

            # Run cross-chain messaging tests
            SOURCE_NETWORK="$source_network" TARGET_NETWORK="$target_network" forge test --match-path "test/crosschain/messaging/**/*.sol" -vv
        done
    done

    cd ../..

    echo -e "${GREEN}Cross-chain messaging tests completed successfully${NC}"
}

# Function to run liquidity pool tests
function run_liquidity_tests {
    echo -e "${BLUE}Running liquidity pool tests...${NC}"

    # Run liquidity pool tests for each network
    cd code/blockchain

    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Testing on $network...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Run liquidity pool tests with network-specific parameters
        FOUNDRY_PROFILE="$network" forge test --match-path "test/liquidity/**/*.sol" -vv
    done

    cd ../..

    echo -e "${GREEN}Liquidity pool tests completed successfully${NC}"
}

# Function to run settlement tests
function run_settlement_tests {
    echo -e "${BLUE}Running settlement tests...${NC}"

    # Run settlement tests for each network
    cd code/blockchain

    for network in "${TEST_NETWORKS[@]}"; do
        echo -e "${BLUE}Testing on $network...${NC}"

        # Load network-specific configuration
        # shellcheck source=/dev/null
        source "$CONFIG_DIR/$network.env"

        # Run settlement tests with network-specific parameters
        FOUNDRY_PROFILE="$network" forge test --match-path "test/settlement/**/*.sol" -vv
    done

    cd ../..

    echo -e "${GREEN}Settlement tests completed successfully${NC}"
}

# Function to generate test report
function generate_test_report {
    echo -e "${BLUE}Generating test report...${NC}"

    # Create report directory if it doesn't exist
    mkdir -p "$REPORT_DIR"

    # Generate timestamp
    TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

    # Create report file
    REPORT_FILE="$REPORT_DIR/cross_chain_test_report_$TIMESTAMP.md"

    # Write report header
    cat > "$REPORT_FILE" << EOF
# Fluxion Cross-Chain Test Report

- **Date:** $(date +"%Y-%m-%d %H:%M:%S")
- **Networks:** ${TEST_NETWORKS[*]}
- **Test Types:** ${TEST_TYPES[*]}

## Summary

EOF

    # Collect test results
    echo -e "${BLUE}Collecting test results...${NC}"

    # Add test results to report
    for network in "${TEST_NETWORKS[@]}"; do
        echo "### $network Network" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        for type in "${TEST_TYPES[@]}"; do
            echo "#### $type Tests" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"

            # Add test results based on type
            case "$type" in
                unit)
                    if [[ -f "code/blockchain/forge-test-unit-$network.json" ]]; then
                        echo "- Smart Contract Tests: $(jq '.testResults | length' "code/blockchain/forge-test-unit-$network.json") tests, $(jq '.testResults | map(select(.status == "success")) | length' "code/blockchain/forge-test-unit-$network.json") passed" >> "$REPORT_FILE"
                    fi
                    if [[ -f "code/backend/pytest-unit.xml" ]]; then
                        echo "- Backend Tests: $(grep -c "<testcase" "code/backend/pytest-unit.xml") tests, $(grep -c "<testcase.*status=\"passed\"" "code/backend/pytest-unit.xml") passed" >> "$REPORT_FILE"
                    fi
                    ;;
                integration)
                    if [[ -f "code/blockchain/forge-test-integration-$network.json" ]]; then
                        echo "- Smart Contract Tests: $(jq '.testResults | length' "code/blockchain/forge-test-integration-$network.json") tests, $(jq '.testResults | map(select(.status == "success")) | length' "code/blockchain/forge-test-integration-$network.json") passed" >> "$REPORT_FILE"
                    fi
                    if [[ -f "code/backend/pytest-integration.xml" ]]; then
                        echo "- Backend Tests: $(grep -c "<testcase" "code/backend/pytest-integration.xml") tests, $(grep -c "<testcase.*status=\"passed\"" "code/backend/pytest-integration.xml") passed" >> "$REPORT_FILE"
                    fi
                    ;;
                e2e)
                    if [[ -f "code/e2e/test-results-$network.json" ]]; then
                        echo "- End-to-End Tests: $(jq '.numTotalTests' "code/e2e/test-results-$network.json") tests, $(jq '.numPassedTests' "code/e2e/test-results-$network.json") passed" >> "$REPORT_FILE"
                    fi
                    ;;
                messaging)
                    # For messaging, we need to check pairs of networks
                    for target_network in "${TEST_NETWORKS[@]}"; do
                        if [[ "$network" != "$target_network" ]]; then
                            if [[ -f "code/blockchain/forge-test-messaging-$network-$target_network.json" ]]; then
                                echo "- Messaging to $target_network: $(jq '.testResults | length' "code/blockchain/forge-test-messaging-$network-$target_network.json") tests, $(jq '.testResults | map(select(.status == "success")) | length' "code/blockchain/forge-test-messaging-$network-$target_network.json") passed" >> "$REPORT_FILE"
                            fi
                        fi
                    done
                    ;;
                liquidity)
                    if [[ -f "code/blockchain/forge-test-liquidity-$network.json" ]]; then
                        echo "- Liquidity Tests: $(jq '.testResults | length' "code/blockchain/forge-test-liquidity-$network.json") tests, $(jq '.testResults | map(select(.status == "success")) | length' "code/blockchain/forge-test-liquidity-$network.json") passed" >> "$REPORT_FILE"
                    fi
                    ;;
                settlement)
                    if [[ -f "code/blockchain/forge-test-settlement-$network.json" ]]; then
                        echo "- Settlement Tests: $(jq '.testResults | length' "code/blockchain/forge-test-settlement-$network.json") tests, $(jq '.testResults | map(select(.status == "success")) | length' "code/blockchain/forge-test-settlement-$network.json") passed" >> "$REPORT_FILE"
                    fi
                    ;;
            esac

            echo "" >> "$REPORT_FILE"
        done
    done

    echo -e "${GREEN}Test report generated: $REPORT_FILE${NC}"
}

# Function to cleanup test environment
function cleanup {
    echo -e "${BLUE}Cleaning up test environment...${NC}"

    # Stop local blockchain nodes
    for pid in "${BLOCKCHAIN_PIDS[@]}"; do
        if ps -p $pid > /dev/null; then
            echo -e "${BLUE}Stopping blockchain node with PID $pid...${NC}"
            kill $pid
        fi
    done

    # Deactivate virtual environment
    deactivate 2>/dev/null || true

    echo -e "${GREEN}Cleanup completed${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--networks)
            IFS=',' read -ra TEST_NETWORKS <<< "$2"
            shift 2
            ;;
        -t|--test-types)
            IFS=',' read -ra TEST_TYPES <<< "$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -r|--report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -c|--config-dir)
            CONFIG_DIR="$2"
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

# Array to store blockchain node PIDs
BLOCKCHAIN_PIDS=()

# Set up trap to ensure cleanup on exit
trap cleanup EXIT

# Main execution
echo -e "${BLUE}Fluxion Cross-Chain Testing${NC}"
echo -e "${BLUE}==========================${NC}"
echo -e "${BLUE}Networks:${NC} ${TEST_NETWORKS[*]}"
echo -e "${BLUE}Test Types:${NC} ${TEST_TYPES[*]}"
echo -e "${BLUE}Parallel:${NC} $PARALLEL"
echo -e "${BLUE}Report Directory:${NC} $REPORT_DIR"
echo -e "${BLUE}Verbose:${NC} $VERBOSE"
echo -e "${BLUE}Timeout:${NC} $TIMEOUT seconds"

# Validate inputs
validate_networks
validate_test_types

# Check prerequisites
check_prerequisites

# Setup test environment
setup_test_environment

# Start local blockchain nodes
start_local_blockchains

# Run tests based on selected types
for type in "${TEST_TYPES[@]}"; do
    case "$type" in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        messaging)
            run_messaging_tests
            ;;
        liquidity)
            run_liquidity_tests
            ;;
        settlement)
            run_settlement_tests
            ;;
    esac
done

# Generate test report
generate_test_report

echo -e "${GREEN}Cross-chain testing completed successfully${NC}"
echo -e "${GREEN}Test report available at: $REPORT_DIR${NC}"
