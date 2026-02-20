import sys
sys.path.insert(0, '/home/user/nf-subway')

from nf_subway.graph import SubwayGraph
from nf_subway.colors import ProcessStatus
from nf_subway.renderer import SubwayRenderer

# Create a test graph
graph = SubwayGraph()

# Add processes simulating the subworkflow structure
graph.add_process("QUALITY_CHECK", status=ProcessStatus.COMPLETED)
graph.add_process("TRIM_SEQUENCES", status=ProcessStatus.COMPLETED)
graph.add_dependency("QUALITY_CHECK", "TRIM_SEQUENCES")

# Branch 1: Alignment
graph.add_process("ALIGN_READS", status=ProcessStatus.COMPLETED)
graph.add_dependency("TRIM_SEQUENCES", "ALIGN_READS")
graph.add_process("COUNT_FEATURES", status=ProcessStatus.RUNNING)
graph.add_dependency("ALIGN_READS", "COUNT_FEATURES")

# Branch 2: Pseudoalignment
graph.add_process("BUILD_INDEX", status=ProcessStatus.COMPLETED)
graph.add_dependency("TRIM_SEQUENCES", "BUILD_INDEX")
graph.add_process("PSEUDOALIGN_QUANT", status=ProcessStatus.RUNNING)
graph.add_dependency("BUILD_INDEX", "PSEUDOALIGN_QUANT")

# Branch 3: Assembly
graph.add_process("ASSEMBLE_TRANSCRIPTS", status=ProcessStatus.COMPLETED)
graph.add_dependency("TRIM_SEQUENCES", "ASSEMBLE_TRANSCRIPTS")
graph.add_process("ANNOTATE_ASSEMBLY", status=ProcessStatus.PENDING)
graph.add_dependency("ASSEMBLE_TRANSCRIPTS", "ANNOTATE_ASSEMBLY")

# Merge point
graph.add_process("MERGE_RESULTS", status=ProcessStatus.PENDING)
graph.add_dependency("COUNT_FEATURES", "MERGE_RESULTS")
graph.add_dependency("PSEUDOALIGN_QUANT", "MERGE_RESULTS")
graph.add_dependency("ANNOTATE_ASSEMBLY", "MERGE_RESULTS")

# Render
renderer = SubwayRenderer(graph)
renderer.render_static()

print("\n" + "="*70)
print("✓ Visualization test completed!")
print("="*70)
print("\n📊 Graph structure:")
stats = graph.get_stats()
print(f"  • Total processes: {stats['total']}")
print(f"  • Running: {stats['running']}")
print(f"  • Completed: {stats['completed']}")
print(f"  • Pending: {stats['pending']}")
print("\n✨ Features demonstrated:")
print("  • No emoji icons - only colored dots")
print("  • Three parallel branches from TRIM_SEQUENCES")
print("  • Blue blinking dots for running processes (COUNT_FEATURES, PSEUDOALIGN_QUANT)")
print("  • Gray dots for pending processes (ANNOTATE_ASSEMBLY, MERGE_RESULTS)")
print("  • Clean merge point at MERGE_RESULTS")
