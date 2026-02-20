#!/bin/bash
# Helper script to run Nextflow demos with nf-subway visualization
# Nextflow sends output to stderr, so we need to redirect it properly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if nf-subway is available
if ! python -c "import nf_subway" 2>/dev/null; then
    echo -e "${RED}Error: nf-subway not installed${NC}"
    echo "Please install it first:"
    echo "  cd .. && pip install -e ."
    exit 1
fi

# Check if nextflow is available
if ! command -v nextflow &> /dev/null; then
    echo -e "${RED}Error: nextflow not found${NC}"
    echo "Please install Nextflow first"
    exit 1
fi

# Determine which demo to run
DEMO_FILE="${1:-demo.nf}"

if [[ ! -f "$DEMO_FILE" ]]; then
    echo -e "${RED}Error: Demo file not found: $DEMO_FILE${NC}"
    echo "Usage: $0 [demo.nf|demo_with_subworkflows.nf]"
    exit 1
fi

echo -e "${GREEN}Running Nextflow demo with nf-subway visualization${NC}"
echo -e "${YELLOW}Pipeline: $DEMO_FILE${NC}"
echo ""

# Create a temporary file for the log
LOGFILE=$(mktemp /tmp/nextflow-log-XXXXXX.txt)
trap "rm -f $LOGFILE" EXIT

# Run Nextflow in background, redirecting both stdout and stderr to the log
nextflow run "$DEMO_FILE" 2>&1 | tee "$LOGFILE" | python -m nf_subway.cli

# Clean up
echo ""
echo -e "${GREEN}Pipeline completed!${NC}"
