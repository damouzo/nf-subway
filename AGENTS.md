# AGENTS.md

## Agent Guidelines — Git-Graph Style Terminal Visualization (NF-Subway)

This document serves as a detailed operational and code reference for all contributors to the nf-subway project, ensuring visual clarity, reliability, and maintainability while achieving a true, dynamic git-graph experience for Nextflow pipelines.

---

### 1. Core Concepts

- **Main Goal:**  
  Render Nextflow pipelines as an animated terminal graph that mirrors git-graph/git-bahn:  
    - Distinct colored lanes/branches, branching/merging, process status dots  
    - Annotations (job ID, process name, progress) right-aligned next to each process  
    - Both vertical and horizontal layout support (selectable via `--orientation` argument)

- **Design Principles:**  
  - Minimalist, clean, and informative  
  - Icons and color-coding communicate status instantly  
  - Truncation with ellipsis for long process names or stats  
  - Layout must remain readable regardless of pipeline complexity or terminal size

---

### 2. Directory & File Structure

- **Key modules:**
  - `nf_subway/renderer.py`: All rendering logic (vertical/horizontal, lane assignment, color)
  - `nf_subway/graph.py`: Manages DAG structure, node data (lane/color assignment)
  - `nf_subway/parser.py`: Extracts process state annotations from Nextflow output
  - `nf_subway/colors.py`: Fixed branch palette, color constants, status colors
  - `nf_subway/monitor.py`: Integration and live update loop (UI refresh)
  - `nf_subway/cli.py`: CLI argument parsing (`--orientation`, `--log`, etc.)

- **Tests:**  
  - `test_subway.py`: Must exercise both vertical/horizontal layouts and all edge cases

---

### 3. Coding Standards

- **Language:** Python 3.8+
- **Formatting:** Black (line-length=100), double quotes, trailing commas
- **Naming:**  
  - Functions/variables: `snake_case`  
  - Classes/types: `CamelCase`  
  - Constants: `UPPER_CASE`
- **Modules:**  
  - Imports grouped: stdlib, third-party, then local modules  
  - Rich is primary rendering dependency

- **Type Annotations:**  
  - Strongly encouraged in interfaces and public functions  
  - Use `dataclasses` for nodes

- **Status Handling:**  
  - Use `enum` ProcessStatus (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CACHED`)  
  - Never rely on exit codes for in-UI state

---

### 4. Visualization & Aesthetics

- **Graph Layout:**
  - Each process = colored dot in a distinct branch lane
  - Lane/branch color is persistent for timeline of branch
  - Connectors: Unicode pipes, splits, merges (│, ─, ├, ┤, ┼)

- **Annotation panel:**  
  - Right of each dot: `[job_id] process name (progress)`  
  - Truncate with `...` if space is insufficient

- **Animation:**  
  - Running nodes must animate (blink effect on blue dots)
  - UI must update at 4Hz by default

- **CLI**:  
  - `--orientation [vertical|horizontal|auto]`
  - `--log FILE`
  - `--refresh N`
  - `--no-original` (suppress Nextflow log echo)

---

### 5. Extensibility & Contribution

- **Branch Visualization:**  
  - Always use a fixed palette for branch/lanes (match git-bahn/git-graph for consistency)
- **Additions/changes:**  
  - All UI/graph/renderer enhancements documented and justified with git-bahn or Rich reference
  - When adding new visual features, preserve clarity and test both layouts
  
- **Testing:**  
  - Every feature covered in `test_subway.py`  
  - Test: pipeline with true branching & merging, both output formats, large workflow edge case

- **Documentation:**  
  - Update this file and all inline docs for each new feature

---

### 6. Error Handling

- **"No processes yet..."**: Show in dim if parser sees no processes
- **Log file missing**: Warn, wait for creation (do not crash)
- **Line parse fail**: Show count of skipped lines in panel subtitle if relevant
- **Status fallback**: Unknown/missing = dim gray (pending)
- **Process annotation too long**: Truncate to fit, keep suffix ellipsis

---

### 7. Inspiration & Reference

- Git-bahn / git-graph: https://github.com/git-bahn/git-graph  
- Rich Terminal: https://github.com/Textualize/rich  
- Nextflow: https://www.nextflow.io/docs/latest/

---

### 8. Etiquette

- Write concise, descriptive commits/PRs (focus on “why” not just “what”)
- Ensure tests pass and UI is clean before merging
- Discuss big UI changes with reference screenshots or diagrams
- Remove dead code, keep API/documentation current

---

**If in doubt, ask visually: maintain the git-graph spirit—clean, colorful, minimal, and useful.**
