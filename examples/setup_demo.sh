#!/bin/bash

# Setup script to create demo data for the example pipeline

echo "Setting up demo data..."

# Create demo_data directory
mkdir -p demo_data

# Create sample files
echo "Sample 1 data content" > demo_data/sample1.txt
echo "Sample 2 data content" > demo_data/sample2.txt
echo "Sample 3 data content" > demo_data/sample3.txt

echo "Demo data created in demo_data/"
echo ""
echo "Available demo pipelines:"
echo ""
echo "1. Basic demo with two parallel branches:"
echo "   nextflow run demo.nf | python -m nf_subway.cli"
echo ""
echo "2. Advanced demo with three subworkflows (shows complex branching):"
echo "   nextflow run demo_with_subworkflows.nf | python -m nf_subway.cli"
echo ""
echo "Or monitor the log file:"
echo "   nextflow run demo.nf & python -m nf_subway.cli --log .nextflow.log"
echo "   nextflow run demo_with_subworkflows.nf & python -m nf_subway.cli --log .nextflow.log"
