#!/bin/bash
# AI/ML Pipeline Orchestration Script for Fluxion
# This script automates the training, evaluation, and deployment of AI/ML models
# used in Fluxion's liquidity prediction, market making, and risk management.

# Exit immediately if a command exits with a non-zero status
set -e

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default values
MODEL_TYPES=("liquidity_prediction" "price_forecasting" "volatility_modeling" "arbitrage_detection")
DATA_SOURCE="production"
OUTPUT_DIR="./models"
# Base directory for ML code. The repository keeps ML code under code/ml_models;
# override with AI_DIR if your layout differs.
AI_DIR="${AI_DIR:-./code/ml_models}"
CONFIG_DIR="${AI_DIR}/configs"
FORCE_RETRAIN=false
DEPLOY_MODELS=false
GPU_ENABLED=false
DISTRIBUTED=false
HYPERPARAMETER_TUNING=false

# Function to display usage information
function show_usage {
    echo -e "${BLUE}Fluxion AI/ML Pipeline Orchestration Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -m, --models MODEL1,MODEL2  Comma-separated list of models to process"
    echo "  -d, --data-source SOURCE    Data source to use (production, staging, synthetic)"
    echo "  -o, --output-dir DIR        Directory to store trained models"
    echo "  -c, --config-dir DIR        Directory containing model configurations"
    echo "  -f, --force-retrain         Force retraining even if recent models exist"
    echo "  --deploy                    Deploy models after training and evaluation"
    echo "  --gpu                       Enable GPU acceleration"
    echo "  --distributed               Enable distributed training"
    echo "  --tune                      Perform hyperparameter tuning"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Available models: liquidity_prediction, price_forecasting, volatility_modeling,"
    echo "                 arbitrage_detection, market_making, risk_assessment"
    echo ""
    echo "Example: $0 -m liquidity_prediction,price_forecasting --gpu --deploy"
}

# Function to validate model types
function validate_model_types {
    local valid_models=("liquidity_prediction" "price_forecasting" "volatility_modeling" "arbitrage_detection" "market_making" "risk_assessment")

    for model in "${MODEL_TYPES[@]}"; do
        local valid=false
        for valid_model in "${valid_models[@]}"; do
            if [[ "$model" == "$valid_model" ]]; then
                valid=true
                break
            fi
        done

        if [[ "$valid" == "false" ]]; then
            echo -e "${RED}Error: Invalid model type '$model'${NC}"
            echo "Valid model types are: ${valid_models[*]}"
            exit 1
        fi
    done
}

# Function to validate data source
function validate_data_source {
    local valid_sources=("production" "staging" "synthetic" "historical")

    local valid=false
    for source in "${valid_sources[@]}"; do
        if [[ "$DATA_SOURCE" == "$source" ]]; then
            valid=true
            break
        fi
    done

    if [[ "$valid" == "false" ]]; then
        echo -e "${RED}Error: Invalid data source '$DATA_SOURCE'${NC}"
        echo "Valid data sources are: ${valid_sources[*]}"
        exit 1
    fi
}

# Function to check prerequisites
function check_prerequisites {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check for required tools
    command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: Python 3 is required but not installed${NC}"; exit 1; }
    command -v pip >/dev/null 2>&1 || { echo -e "${RED}Error: pip is required but not installed${NC}"; exit 1; }

    # Check for configuration directory
    if [[ ! -d "$CONFIG_DIR" ]]; then
        echo -e "${RED}Error: Configuration directory '$CONFIG_DIR' not found${NC}"
        exit 1
    fi

    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"

    # Check for GPU if enabled
    if [[ "$GPU_ENABLED" == "true" ]]; then
        if ! python3 -c "import torch; print(torch.cuda.is_available())" | grep -q "True"; then
            echo -e "${YELLOW}Warning: GPU acceleration requested but CUDA is not available${NC}"
            echo -e "${YELLOW}Falling back to CPU processing${NC}"
            GPU_ENABLED=false
        fi
    fi

    # Check for Ray if distributed training is enabled
    if [[ "$DISTRIBUTED" == "true" ]]; then
        if ! python3 -c "import ray" &>/dev/null; then
            echo -e "${RED}Error: Distributed training requires Ray but it's not installed${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}All prerequisites satisfied${NC}"
}

# Function to setup AI/ML environment
function setup_environment {
    echo -e "${BLUE}Setting up AI/ML environment...${NC}"

    # Create Python virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        echo -e "${BLUE}Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install AI/ML dependencies
    echo -e "${BLUE}Installing AI/ML dependencies...${NC}"
    pip install -r ${AI_DIR}/requirements.txt

    # Install additional packages based on options
    if [[ "$GPU_ENABLED" == "true" ]]; then
        echo -e "${BLUE}Installing GPU dependencies...${NC}"
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    fi

    if [[ "$DISTRIBUTED" == "true" ]]; then
        echo -e "${BLUE}Installing distributed training dependencies...${NC}"
        pip install ray[tune] ray[train]
    fi

    if [[ "$HYPERPARAMETER_TUNING" == "true" ]]; then
        echo -e "${BLUE}Installing hyperparameter tuning dependencies...${NC}"
        pip install optuna hyperopt
    fi

    echo -e "${GREEN}AI/ML environment setup completed${NC}"
}

# Function to fetch and prepare data
function fetch_data {
    echo -e "${BLUE}Fetching and preparing data from $DATA_SOURCE source...${NC}"

    # Create data directory if it doesn't exist
    mkdir -p data

    # Run data fetching script with appropriate parameters
    python3 ${AI_DIR}/data/fetch_data.py \
        --source "$DATA_SOURCE" \
        --output-dir "data" \
        --models "${MODEL_TYPES[@]}"

    echo -e "${GREEN}Data fetching and preparation completed${NC}"
}

# Function to train models
function train_models {
    echo -e "${BLUE}Training AI/ML models...${NC}"

    # For each model type, run training
    for model_type in "${MODEL_TYPES[@]}"; do
        echo -e "${BLUE}Training $model_type model...${NC}"

        # Check if recent model exists and skip if not forced to retrain
        if [[ "$FORCE_RETRAIN" == "false" ]] && [[ -f "$OUTPUT_DIR/$model_type/latest.pt" ]]; then
            model_date=$(stat -c %Y "$OUTPUT_DIR/$model_type/latest.pt")
            current_date=$(date +%s)
            days_old=$(( (current_date - model_date) / 86400 ))

            if [[ $days_old -lt 7 ]]; then
                echo -e "${YELLOW}Recent $model_type model found (${days_old} days old)${NC}"
                echo -e "${YELLOW}Skipping training. Use --force-retrain to override.${NC}"
                continue
            fi
        fi

        # Create model output directory
        mkdir -p "$OUTPUT_DIR/$model_type"

        # Determine training script based on model type
        case "$model_type" in
            liquidity_prediction)
                script="liquidity_prediction.py"
                ;;
            price_forecasting)
                script="price_forecasting.py"
                ;;
            volatility_modeling)
                script="volatility_modeling.py"
                ;;
            arbitrage_detection)
                script="arbitrage_detection.py"
                ;;
            market_making)
                script="market_making.py"
                ;;
            risk_assessment)
                script="risk_assessment.py"
                ;;
        esac

        # Build training command
        cmd="python3 ${AI_DIR}/training/$script \
            --config $CONFIG_DIR/$model_type.yaml \
            --data-dir data/$model_type \
            --output-dir $OUTPUT_DIR/$model_type"

        # Add optional parameters
        if [[ "$GPU_ENABLED" == "true" ]]; then
            cmd="$cmd --gpu"
        fi

        if [[ "$DISTRIBUTED" == "true" ]]; then
            cmd="$cmd --distributed"
        fi

        if [[ "$HYPERPARAMETER_TUNING" == "true" ]]; then
            cmd="$cmd --tune"
        fi

        # Run training command
        eval $cmd

        echo -e "${GREEN}$model_type model training completed${NC}"
    done

    echo -e "${GREEN}All model training completed${NC}"
}

# Function to evaluate models
function evaluate_models {
    echo -e "${BLUE}Evaluating AI/ML models...${NC}"

    # For each model type, run evaluation
    for model_type in "${MODEL_TYPES[@]}"; do
        echo -e "${BLUE}Evaluating $model_type model...${NC}"

        # Check if model exists
        if [[ ! -f "$OUTPUT_DIR/$model_type/latest.pt" ]]; then
            echo -e "${YELLOW}No $model_type model found to evaluate${NC}"
            continue
        fi

        # Create evaluation output directory
        mkdir -p "$OUTPUT_DIR/$model_type/evaluation"

        # Run evaluation script
        python3 ${AI_DIR}/evaluation/evaluate.py \
            --model-type "$model_type" \
            --model-path "$OUTPUT_DIR/$model_type/latest.pt" \
            --data-dir "data/$model_type" \
            --output-dir "$OUTPUT_DIR/$model_type/evaluation"

        echo -e "${GREEN}$model_type model evaluation completed${NC}"
    done

    echo -e "${GREEN}All model evaluations completed${NC}"
}

# Function to deploy models
function deploy_models {
    if [[ "$DEPLOY_MODELS" != "true" ]]; then
        echo -e "${YELLOW}Model deployment skipped (use --deploy to enable)${NC}"
        return
    fi

    echo -e "${BLUE}Deploying AI/ML models...${NC}"

    # For each model type, run deployment
    for model_type in "${MODEL_TYPES[@]}"; do
        echo -e "${BLUE}Deploying $model_type model...${NC}"

        # Check if model exists
        if [[ ! -f "$OUTPUT_DIR/$model_type/latest.pt" ]]; then
            echo -e "${YELLOW}No $model_type model found to deploy${NC}"
            continue
        fi

        # Check if evaluation exists and model meets quality threshold
        if [[ -f "$OUTPUT_DIR/$model_type/evaluation/metrics.json" ]]; then
            # Extract evaluation metrics
            accuracy=$(jq '.accuracy' "$OUTPUT_DIR/$model_type/evaluation/metrics.json")
            threshold=$(jq ".$model_type.threshold" "$CONFIG_DIR/deployment_thresholds.json")

            if (( $(echo "$accuracy < $threshold" | bc -l) )); then
                echo -e "${YELLOW}$model_type model accuracy ($accuracy) below threshold ($threshold)${NC}"
                echo -e "${YELLOW}Skipping deployment${NC}"
                continue
            fi
        fi

        # Convert model to ONNX format for deployment
        echo -e "${BLUE}Converting $model_type model to ONNX format...${NC}"
        python3 ${AI_DIR}/deployment/convert_to_onnx.py \
            --model-type "$model_type" \
            --model-path "$OUTPUT_DIR/$model_type/latest.pt" \
            --output-path "$OUTPUT_DIR/$model_type/model.onnx"

        # Deploy model to serving infrastructure
        echo -e "${BLUE}Deploying $model_type model to serving infrastructure...${NC}"
        python3 ${AI_DIR}/deployment/deploy.py \
            --model-type "$model_type" \
            --model-path "$OUTPUT_DIR/$model_type/model.onnx" \
            --config "$CONFIG_DIR/deployment.yaml"

        echo -e "${GREEN}$model_type model deployment completed${NC}"
    done

    echo -e "${GREEN}All model deployments completed${NC}"
}

# Function to generate model documentation
function generate_documentation {
    echo -e "${BLUE}Generating model documentation...${NC}"

    # Create documentation directory
    mkdir -p "$OUTPUT_DIR/documentation"

    # Generate overall documentation
    echo -e "${BLUE}Generating overall model documentation...${NC}"
    python3 ${AI_DIR}/documentation/generate_docs.py \
        --models "${MODEL_TYPES[@]}" \
        --output-dir "$OUTPUT_DIR/documentation"

    # For each model type, generate specific documentation
    for model_type in "${MODEL_TYPES[@]}"; do
        echo -e "${BLUE}Generating documentation for $model_type model...${NC}"

        # Check if model exists
        if [[ ! -f "$OUTPUT_DIR/$model_type/latest.pt" ]]; then
            echo -e "${YELLOW}No $model_type model found for documentation${NC}"
            continue
        fi

        # Generate model-specific documentation
        python3 ${AI_DIR}/documentation/generate_model_card.py \
            --model-type "$model_type" \
            --model-path "$OUTPUT_DIR/$model_type/latest.pt" \
            --evaluation-path "$OUTPUT_DIR/$model_type/evaluation" \
            --output-path "$OUTPUT_DIR/documentation/$model_type.md"
    done

    echo -e "${GREEN}Model documentation generation completed${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--models)
            IFS=',' read -ra MODEL_TYPES <<< "$2"
            shift 2
            ;;
        -d|--data-source)
            DATA_SOURCE="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -c|--config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        -f|--force-retrain)
            FORCE_RETRAIN=true
            shift
            ;;
        --deploy)
            DEPLOY_MODELS=true
            shift
            ;;
        --gpu)
            GPU_ENABLED=true
            shift
            ;;
        --distributed)
            DISTRIBUTED=true
            shift
            ;;
        --tune)
            HYPERPARAMETER_TUNING=true
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
echo -e "${BLUE}Fluxion AI/ML Pipeline Orchestration${NC}"
echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}Models:${NC} ${MODEL_TYPES[*]}"
echo -e "${BLUE}Data Source:${NC} $DATA_SOURCE"
echo -e "${BLUE}Output Directory:${NC} $OUTPUT_DIR"
echo -e "${BLUE}Force Retrain:${NC} $FORCE_RETRAIN"
echo -e "${BLUE}Deploy Models:${NC} $DEPLOY_MODELS"
echo -e "${BLUE}GPU Enabled:${NC} $GPU_ENABLED"
echo -e "${BLUE}Distributed Training:${NC} $DISTRIBUTED"
echo -e "${BLUE}Hyperparameter Tuning:${NC} $HYPERPARAMETER_TUNING"

# Validate inputs
validate_model_types
validate_data_source

# Check prerequisites
check_prerequisites

# Setup environment
setup_environment

# Fetch and prepare data
fetch_data

# Train models
train_models

# Evaluate models
evaluate_models

# Deploy models if requested
deploy_models

# Generate documentation
generate_documentation

# Deactivate virtual environment
deactivate

echo -e "${GREEN}AI/ML pipeline orchestration completed successfully${NC}"
echo -e "${GREEN}Model outputs available at: $OUTPUT_DIR${NC}"
