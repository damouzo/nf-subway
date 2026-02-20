#!/bin/bash

# Setup script to create demo data for the example pipeline

echo "Setting up demo data..."

# Create demo_data directory
mkdir -p demo_data

# Create sample files
echo "Sample 1 data content" > demo_data/sample1.txt
echo "Sample 2 data content" > demo_data/sample2.txt
echo "Sample 3 data content" > demo_data/sample3.txt

echo "✅ Demo data created in demo_data/"
echo ""
echo "To run the demo pipeline with NF-Subway:"
echo "  nextflow run demo.nf | nf-subway"
echo ""
echo "Or monitor the log file:"
echo "  nextflow run demo.nf & nf-subway --log .nextflow.log"
