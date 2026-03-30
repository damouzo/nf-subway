# nf-subway

Terminal visualization for Nextflow pipelines, enabling easy interpretation of different processes across multiple subworkflows simultaneously.

https://github.com/user-attachments/assets/cc8790a0-91c2-400a-8efa-67c0c9cef67a

![nf-subway preview](docs/images/Image.png)

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
--refresh

https://github.com/user-attachments/assets/51c383a0-7d48-4101-8d67-8b98bd4ff4a7

 N     Refresh rate in Hz (default: 4)
--version       Show version
```

## Status indicators

| Symbol | Color | Meaning |
|--------|-------|---------|
| `●` (blinking) | blue | running |
| `●` | green | completed |
| `○` | yellow | cached (`-resume`) |
| `X` | red | failed |

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by the clean aesthetics of git-graph visualizations
- Built with [Rich](https://github.com/Textualize/rich) for terminal rendering
- Designed for the [Nextflow](https://www.nextflow.io/) workflow system
