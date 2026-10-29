#!/bin/bash

# Test runner script for Fluxion backend
# This script provides various testing options and configurations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false
PARALLEL=false
MARKERS=""
OUTPUT_FORMAT="term"

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: unit, integration, e2e, all (default: all)"
    echo "  -m, --markers MARKERS  Run tests with specific markers (e.g., 'auth and not slow')"
    echo "  -c, --no-coverage      Disable coverage reporting"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -f, --format FORMAT    Output format: term, html, xml (default: term)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run all tests with coverage"
    echo "  $0 -t unit             # Run only unit tests"
    echo "  $0 -m auth             # Run only auth-related tests"
    echo "  $0 -t integration -v   # Run integration tests with verbose output"
    echo "  $0 -p -c               # Run all tests in parallel without coverage"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -c|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate test type
if [[ ! "$TEST_TYPE" =~ ^(unit|integration|e2e|all)$ ]]; then
    print_color $RED "Error: Invalid test type '$TEST_TYPE'. Must be one of: unit, integration, e2e, all"
    exit 1
fi

# Validate output format
if [[ ! "$OUTPUT_FORMAT" =~ ^(term|html|xml)$ ]]; then
    print_color $RED "Error: Invalid output format '$OUTPUT_FORMAT'. Must be one of: term, html, xml"
    exit 1
fi

print_color $BLUE "=== Fluxion Backend Test Runner ==="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_color $YELLOW "Warning: No virtual environment detected. Consider activating one."
fi

# Check if required packages are installed
print_color $BLUE "Checking dependencies..."
python -c "import pytest, pytest_asyncio, pytest_cov" 2>/dev/null || {
    print_color $RED "Error: Required test packages not installed."
    print_color $YELLOW "Please install with: pip install pytest pytest-asyncio pytest-cov"
    exit 1
}

# Set up test environment variables
export TESTING=true
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export JWT_SECRET_KEY="test-secret-key-for-testing-only"
export REDIS_URL="redis://localhost:6379/1"

print_color $GREEN "Dependencies OK"
echo ""

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add test path based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration"
        ;;
    e2e)
        PYTEST_CMD="$PYTEST_CMD tests/e2e"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests"
        ;;
esac

# Add markers if specified
if [[ -n "$MARKERS" ]]; then
    PYTEST_CMD="$PYTEST_CMD -m \"$MARKERS\""
fi

# Add verbose flag
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add parallel execution
if [[ "$PARALLEL" == true ]]; then
    # Check if pytest-xdist is available
    python -c "import xdist" 2>/dev/null && {
        PYTEST_CMD="$PYTEST_CMD -n auto"
    } || {
        print_color $YELLOW "Warning: pytest-xdist not installed. Running tests sequentially."
        print_color $YELLOW "Install with: pip install pytest-xdist"
    }
fi

# Add coverage options
if [[ "$COVERAGE" == true ]]; then
    case $OUTPUT_FORMAT in
        term)
            PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing"
            ;;
        html)
            PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=html:htmlcov --cov-report=term-missing"
            ;;
        xml)
            PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=xml --cov-report=term-missing"
            ;;
    esac
    PYTEST_CMD="$PYTEST_CMD --cov-fail-under=80"
fi

# Add other useful options
PYTEST_CMD="$PYTEST_CMD --tb=short --strict-markers --disable-warnings"

print_color $BLUE "Running tests..."
print_color $YELLOW "Command: $PYTEST_CMD"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the tests
eval $PYTEST_CMD 2>&1 | tee logs/test_output.log

# Capture exit code
TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""

# Show results
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    print_color $GREEN "=== All tests passed! ==="

    # Show coverage report location if HTML format was used
    if [[ "$COVERAGE" == true && "$OUTPUT_FORMAT" == "html" ]]; then
        print_color $BLUE "Coverage report available at: htmlcov/index.html"
    fi

    # Show XML report location if XML format was used
    if [[ "$COVERAGE" == true && "$OUTPUT_FORMAT" == "xml" ]]; then
        print_color $BLUE "Coverage XML report available at: coverage.xml"
    fi
else
    print_color $RED "=== Some tests failed ==="
    print_color $YELLOW "Check the output above or logs/test_output.log for details"
fi

# Show test summary
echo ""
print_color $BLUE "Test Summary:"
echo "  Test Type: $TEST_TYPE"
echo "  Coverage: $COVERAGE"
echo "  Verbose: $VERBOSE"
echo "  Parallel: $PARALLEL"
echo "  Output Format: $OUTPUT_FORMAT"
if [[ -n "$MARKERS" ]]; then
    echo "  Markers: $MARKERS"
fi
echo "  Log File: logs/test_output.log"

exit $TEST_EXIT_CODE
