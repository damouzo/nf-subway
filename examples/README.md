# NF-Subway Examples

This directory contains example pipelines and data for testing NF-Subway visualization.

## Available Demo Pipelines

### 1. Basic Demo (`demo.nf`)
A simple pipeline with two parallel branches demonstrating basic branching patterns:
- Preprocessing: Quality check → Trimming
- Branch 1: Alignment-based quantification
- Branch 2: Salmon pseudoalignment
- Merge: MultiQC report

### 2. Advanced Demo with Subworkflows (`demo_with_subworkflows.nf`)
A more complex pipeline showcasing **three parallel subworkflows** for interesting visualizations:
- Preprocessing: Quality check → Trimming
- **Branch 1**: ALIGNMENT_BASED_QUANTIFICATION subworkflow
  - ALIGN_READS → COUNT_FEATURES → NORMALIZE_COUNTS
- **Branch 2**: PSEUDOALIGNMENT_QUANTIFICATION subworkflow
  - BUILD_INDEX → PSEUDOALIGN_QUANT → ADJUST_QUANT
- **Branch 3**: ASSEMBLY_ANALYSIS subworkflow
  - ASSEMBLE_TRANSCRIPTS → ANNOTATE_ASSEMBLY
- Merge: MERGE_RESULTS → MULTIQC

This creates a beautiful three-way branching pattern perfect for testing the subway visualization!

## Setup

Run the setup script to create demo data:

```bash
bash setup_demo.sh
```

## Running the Examples

### ⚠️ Important: Nextflow Output Redirection

**Nextflow sends its output to stderr, not stdout**. To capture it properly with nf-subway, use one of these methods:

#### Method 1: Helper Script (Easiest)
```bash
bash run_demo_with_subway.sh demo.nf
bash run_demo_with_subway.sh demo_with_subworkflows.nf
```

#### Method 2: Redirect stderr to stdout
```bash
# Basic demo
nextflow run demo.nf 2>&1 | python -m nf_subway.cli

# Advanced demo with three subworkflows
nextflow run demo_with_subworkflows.nf 2>&1 | python -m nf_subway.cli
```

#### Method 3: Monitor log file (two terminals)
```bash
# Terminal 1: Start pipeline
nextflow run demo_with_subworkflows.nf

# Terminal 2: Monitor with nf-subway
python -m nf_subway.cli --log .nextflow.log
```

## Visualization Features

The visualization now uses **simple colored dots** instead of emoji icons:
- **Gray dot (dim)**: Pending process
- **Blue dot (blinking)**: Running process
- **Green dot**: Completed process
- **Red X**: Failed process
- **Secondary dot**: Cached process

The subway graph shows process dependencies and parallel execution paths using git-graph style branching with multiple colored lanes.
