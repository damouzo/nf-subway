#!/usr/bin/env python3
"""
Quick visual test of grid rendering with parallel branches.
"""

import sys
sys.path.insert(0, '/home/user/nf-subway')

from nf_subway.graph import ProcessNode, ProcessStatus, SubwayGraph
from nf_subway.renderer import SubwayRenderer
from rich.console import Console

def create_parallel_workflow():
    """Create a workflow with parallel branches for testing."""
    graph = SubwayGraph()
    
    # Initial QC
    graph.add_process("FASTQC_RAW", status=ProcessStatus.COMPLETED, task_id="1")
    graph.nodes["FASTQC_RAW"].duration = 1500.0
    
    # Split into two parallel branches
    graph.add_process("TRIM_READS", status=ProcessStatus.COMPLETED, task_id="2")
    graph.nodes["TRIM_READS"].duration = 3200.0
    graph.add_dependency("FASTQC_RAW", "TRIM_READS")
    
    # Branch 1: RNA-seq quantification
    graph.add_process("SALMON_INDEX", status=ProcessStatus.COMPLETED, task_id="3")
    graph.nodes["SALMON_INDEX"].duration = 8500.0
    graph.add_dependency("TRIM_READS", "SALMON_INDEX")
    
    graph.add_process("SALMON_QUANT", status=ProcessStatus.COMPLETED, task_id="4")
    graph.nodes["SALMON_QUANT"].duration = 12000.0
    graph.add_dependency("SALMON_INDEX", "SALMON_QUANT")
    
    # Branch 2: Alignment-based analysis
    graph.add_process("BWA_INDEX", status=ProcessStatus.CACHED, task_id="5")
    graph.nodes["BWA_INDEX"].duration = 9000.0
    graph.add_dependency("TRIM_READS", "BWA_INDEX")
    
    graph.add_process("BWA_ALIGN", status=ProcessStatus.RUNNING, task_id="6")
    graph.nodes["BWA_ALIGN"].duration = 15000.0
    graph.add_dependency("BWA_INDEX", "BWA_ALIGN")
    
    graph.add_process("SAMTOOLS_SORT", status=ProcessStatus.PENDING, task_id="7")
    graph.add_dependency("BWA_ALIGN", "SAMTOOLS_SORT")
    
    # Merge both branches
    graph.add_process("MULTIQC", status=ProcessStatus.PENDING, task_id="8")
    graph.add_dependency("SALMON_QUANT", "MULTIQC")
    graph.add_dependency("SAMTOOLS_SORT", "MULTIQC")
    
    return graph

def main():
    console = Console()
    graph = create_parallel_workflow()
    renderer = SubwayRenderer(graph)
    
    console.print("\n[bold cyan]🧪 Testing Grid Rendering with Parallel Branches[/bold cyan]\n")
    
    # Render and display
    lines = renderer.render_to_lines(orientation='vertical')
    for line in lines:
        console.print(line)
    
    console.print("\n[bold green]✓ Visual test complete![/bold green]\n")

if __name__ == '__main__':
    main()
