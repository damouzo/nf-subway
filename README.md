# NF-Subway 🚇

Git-graph style visualization for Nextflow pipelines.

## Overview

NF-Subway provides a clean, real-time visualization of Nextflow pipeline execution inspired by git-graph aesthetics. Watch your pipeline processes flow through a beautiful subway-map style terminal interface.

## Features

-  **Git-graph inspired aesthetics** - Clean, minimal, beautiful
-  **Real-time monitoring** - See processes update as they run
-  **Subway-style layout** - Vertical flow with clean lines
-  **Live animation** - Blinking colored dots for running processes
-  **Progress tracking** - Duration display for completed processes
-  **Colored status indicators** - Simple dots (no emoji icons):
   - Gray: pending
   - Blue (blinking): running
   - Green: completed
   - Red: failed
   - Yellow: cached

## Installation

### From Source

```bash
git clone https://github.com/damouzo/nf-subway.git
cd nf-subway
pip install -e .
```

### Dependencies

- Python >= 3.8
- rich >= 13.0.0

## Usage

### Pipe Mode (Real-time)

The most straightforward way - pipe Nextflow output directly:

```bash
nextflow run pipeline.nf | nf-subway
```

### Log File Monitoring

Monitor an existing log file (like `tail -f`):

```bash
# Start monitoring (will wait for log file to be created)
nf-subway --log .nextflow.log

# In another terminal, run your pipeline
nextflow run pipeline.nf
```

### Command-line Options

```bash
nf-subway --help

Options:
  --version              Show version and exit
  --log FILE            Monitor a Nextflow log file
  --refresh RATE        Refresh rate in updates per second (default: 4)
  --no-original         Hide original Nextflow output
```

### Python API

Use NF-Subway in your Python code:

```python
from nf_subway import SubwayGraph, SubwayRenderer, ProcessStatus

# Create graph
graph = SubwayGraph()

# Add processes
graph.add_process("FASTQC", ProcessStatus.COMPLETED)
graph.add_process("TRIMGALORE", ProcessStatus.RUNNING)
graph.add_process("STAR_ALIGN", ProcessStatus.PENDING)

# Add dependencies
graph.add_dependency("FASTQC", "TRIMGALORE")
graph.add_dependency("TRIMGALORE", "STAR_ALIGN")

# Render
renderer = SubwayRenderer(graph)
renderer.render_inline()
```

## Demo

Try the included demo pipeline:

```bash
cd examples
bash setup_demo.sh
nextflow run demo.nf | nf-subway
```

This will run a simulated bioinformatics pipeline with multiple processes and show the live visualization.

## How It Works

NF-Subway consists of several components working together:

1. **Parser** (`parser.py`) - Extracts process information from Nextflow output
2. **Graph** (`graph.py`) - Maintains the pipeline DAG structure
3. **Renderer** (`renderer.py`) - Generates beautiful terminal output using Rich
4. **Monitor** (`monitor.py`) - Coordinates real-time updates
5. **Colors** (`colors.py`) - Defines the git-graph inspired color scheme

The visualization updates in real-time as your pipeline executes, showing:
- Process execution order (top to bottom)
- Current status with color-coded icons
- Execution duration for completed processes
- Overall pipeline statistics

## Color Scheme

Inspired by git-graph's clean aesthetics:

-  **Pending** - Dim gray (waiting to execute)
-  **Running** - Bright blue with blink effect (currently executing)
-  **Completed** - Bright green (successfully finished)
-  **Failed** - Bright red (execution failed)
-  **Cached** - Yellow (result from cache)

## Development

### Running Tests

```bash
python test_subway.py
```

This runs a comprehensive test suite that verifies:
- Graph creation and management
- Output parsing
- Live rendering
- Animation effects
- All status types

### Project Structure

```
nf-subway/
├── nf_subway/
│   ├── __init__.py      # Package initialization
│   ├── colors.py        # Color scheme and styling
│   ├── graph.py         # DAG data structure
│   ├── parser.py        # Nextflow output parsing
│   ├── renderer.py      # Terminal rendering
│   ├── monitor.py       # Real-time monitoring
│   └── cli.py           # Command-line interface
├── examples/
│   ├── demo.nf          # Demo pipeline
│   └── setup_demo.sh    # Demo setup script
├── test_subway.py       # Test suite
├── pyproject.toml       # Package configuration
└── README.md            # This file
```

## Future Enhancements

- [ ] Horizontal layout option for wide terminals
- [ ] Resource usage visualization (CPU, memory)
- [ ] Interactive mode with process inspection
- [ ] Export to HTML for sharing
- [ ] Integration with Nextflow Tower
- [ ] Support for complex branching workflows
- [ ] Real-time log filtering and search

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by the clean aesthetics of git-graph visualizations
- Built with [Rich](https://github.com/Textualize/rich) for terminal rendering
- Designed for the [Nextflow](https://www.nextflow.io/) workflow system
