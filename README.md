# nf-subway

Terminal visualization for Nextflow pipelines, enabling easy interpretation of different processes across multiple subworkflows simultaneously.



## Install

```bash
pip install git+https://github.com/damouzo/nf-subway.git
```

## Usage

```bash
nextflow run pipeline.nf | nf-subway
```

That's it. By default the original Nextflow output is hidden. Add `--original` to show both:

```bash
nextflow run pipeline.nf | nf-subway --original
```

Other options:

```
--log FILE      Monitor a .nextflow.log file instead of stdin
--refresh N     Refresh rate in Hz (default: 4)
--version       Show version
```

## Status indicators

| Symbol | Color | Meaning |
|--------|-------|---------|
| `●` (blinking) | blue | running |
| `●` | green | completed |
| `○` | yellow | cached (`-resume`) |
| `X` | red | failed |

## Develop

```bash
git clone https://github.com/damouzo/nf-subway.git
cd nf-subway
pip install -e ".[dev]"
```

│   └── cli.py           # Command-line interface
├── examples/
│   ├── demo.nf          # Demo pipeline
│   └── setup_demo.sh    # Demo setup script
├── test_subway.py       # Test suite
├── pyproject.toml       # Package configuration
└── README.md            # This file
```


## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by the clean aesthetics of git-graph visualizations
- Built with [Rich](https://github.com/Textualize/rich) for terminal rendering
- Designed for the [Nextflow](https://www.nextflow.io/) workflow system
