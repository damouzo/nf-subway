#!/usr/bin/env python3
"""Quick visual test of the new dot-only style"""

import sys
sys.path.insert(0, '/home/user/nf-subway')

from nf_subway.graph import SubwayGraph, ProcessNode
from nf_subway.renderer import SubwayRenderer
from nf_subway.colors import ProcessStatus

# Create a simple graph with different statuses
graph = SubwayGraph()

# Add processes with different statuses
graph.add_process("QUALITY_CHECK", status=ProcessStatus.COMPLETED)
graph.update_process("QUALITY_CHECK", ProcessStatus.COMPLETED, duration=2.5)

graph.add_process("TRIM_SEQUENCES", status=ProcessStatus.COMPLETED)
graph.add_dependency("QUALITY_CHECK", "TRIM_SEQUENCES")
graph.update_process("TRIM_SEQUENCES", ProcessStatus.COMPLETED, duration=3.2)

graph.add_process("ALIGN_READS", status=ProcessStatus.RUNNING)
graph.add_dependency("TRIM_SEQUENCES", "ALIGN_READS")

graph.add_process("SALMON_INDEX", status=ProcessStatus.RUNNING)
graph.add_dependency("TRIM_SEQUENCES", "SALMON_INDEX")

graph.add_process("COUNT_FEATURES", status=ProcessStatus.PENDING)
graph.add_dependency("ALIGN_READS", "COUNT_FEATURES")

graph.add_process("SALMON_QUANT", status=ProcessStatus.PENDING)
graph.add_dependency("SALMON_INDEX", "SALMON_QUANT")

# Render
renderer = SubwayRenderer(graph)
print("\n" + "="*60)
print("NF-Subway Visual Test - Dot-Only Style (No Emojis)")
print("="*60 + "\n")

# Print panel
renderer.render_inline()

print("\n" + "="*60)
print("Legend:")
print("  • Green dot: Completed process")
print("  • Blue dot: Running process (would blink in live mode)")
print("  • Gray dot: Pending process")
print("="*60 + "\n")
