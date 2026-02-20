#!/usr/bin/env python3
"""
Test visual for a more complex RNA-seq pipeline.
"""

from nf_subway.graph import SubwayGraph
from nf_subway.renderer import SubwayRenderer
from nf_subway.colors import ProcessStatus

# Create a graph for a complex RNA-seq pipeline
graph = SubwayGraph()

# Preprocessing stage
graph.add_process("DOWNLOAD_GENOME", status=ProcessStatus.COMPLETED)
graph.update_process("DOWNLOAD_GENOME", ProcessStatus.COMPLETED, duration=45.0)

graph.add_process("DOWNLOAD_ANNOTATION", status=ProcessStatus.COMPLETED)
graph.update_process("DOWNLOAD_ANNOTATION", ProcessStatus.COMPLETED, duration=30.0)

graph.add_process("FASTQC_RAW", status=ProcessStatus.COMPLETED)
graph.update_process("FASTQC_RAW", ProcessStatus.COMPLETED, duration=5.5)

# Index building (depends on genome)
graph.add_process("STAR_INDEX", status=ProcessStatus.COMPLETED)
graph.add_dependency("DOWNLOAD_GENOME", "STAR_INDEX")
graph.add_dependency("DOWNLOAD_ANNOTATION", "STAR_INDEX")
graph.update_process("STAR_INDEX", ProcessStatus.COMPLETED, duration=180.0)

graph.add_process("SALMON_INDEX", status=ProcessStatus.COMPLETED)
graph.add_dependency("DOWNLOAD_GENOME", "SALMON_INDEX")
graph.update_process("SALMON_INDEX", ProcessStatus.COMPLETED, duration=90.0)

# Quality control and trimming
graph.add_process("FASTP", status=ProcessStatus.COMPLETED)
graph.add_dependency("FASTQC_RAW", "FASTP")
graph.update_process("FASTP", ProcessStatus.COMPLETED, duration=12.5)

graph.add_process("FASTQC_TRIMMED", status=ProcessStatus.RUNNING)
graph.add_dependency("FASTP", "FASTQC_TRIMMED")

# Alignment branch
graph.add_process("STAR_ALIGN", status=ProcessStatus.RUNNING)
graph.add_dependency("FASTP", "STAR_ALIGN")
graph.add_dependency("STAR_INDEX", "STAR_ALIGN")

# Quantification branches
graph.add_process("SALMON_QUANT", status=ProcessStatus.PENDING)
graph.add_dependency("FASTP", "SALMON_QUANT")
graph.add_dependency("SALMON_INDEX", "SALMON_QUANT")

graph.add_process("FEATURECOUNTS", status=ProcessStatus.PENDING)
graph.add_dependency("STAR_ALIGN", "FEATURECOUNTS")

# Post-processing
graph.add_process("DESEQ2", status=ProcessStatus.PENDING)
graph.add_dependency("FEATURECOUNTS", "DESEQ2")

graph.add_process("MULTIQC", status=ProcessStatus.PENDING)
graph.add_dependency("FASTQC_RAW", "MULTIQC")
graph.add_dependency("FASTQC_TRIMMED", "MULTIQC")
graph.add_dependency("STAR_ALIGN", "MULTIQC")

# Render
renderer = SubwayRenderer(graph)
print("\n" + "="*80)
print("Complex RNA-seq Pipeline - NF-Subway Visualization")
print("="*80 + "\n")

renderer.render_inline()

print("\n" + "="*80)
print("Status Summary:")
print(f"  Completed: {sum(1 for n in graph.nodes.values() if n.status == ProcessStatus.COMPLETED)}")
print(f"  Running:   {sum(1 for n in graph.nodes.values() if n.status == ProcessStatus.RUNNING)}")
print(f"  Pending:   {sum(1 for n in graph.nodes.values() if n.status == ProcessStatus.PENDING)}")
print("="*80 + "\n")
