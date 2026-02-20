#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/user/nf-subway')

from nf_subway.monitor import StreamMonitor

# Create monitor
monitor = StreamMonitor(orientation='vertical')

# Simulate Nextflow output
test_lines = [
    "[bb/01f98e] QUALITY_CHECK (3)  [100%] 3 of 3 ✔",
    "[7f/5e5301] TRIM_SEQUENCES (2) [100%] 3 of 3 ✔",
    "[ef/63e587] ALIGN_READS (3)    [100%] 3 of 3 ✔",
]

for line in test_lines:
    monitor._process_line(line)

# Render
from nf_subway.renderer import SubwayRenderer
renderer = SubwayRenderer(monitor.graph)
lines = renderer.render_to_lines('vertical')
for line in lines:
    print(line)

# Show processes
print("\nProcesses in graph:")
for name, node in monitor.graph.nodes.items():
    print(f"  {name}: annotation='{node.annotation}'")
