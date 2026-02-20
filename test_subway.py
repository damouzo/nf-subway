#!/usr/bin/env python3
"""
Simple test script to verify NF-Subway works without a real Nextflow pipeline.

Simulates Nextflow output and tests the visualization components.
"""

import time
import sys
from nf_subway import SubwayGraph, SubwayRenderer, ProcessStatus
from nf_subway.parser import NextflowOutputParser


def test_basic_graph():
    """Test basic graph creation and rendering."""
    print("=" * 60)
    print("TEST 1: Basic Graph Creation")
    print("=" * 60)
    
    graph = SubwayGraph()
    
    # Add some processes
    graph.add_process("FASTQC", ProcessStatus.COMPLETED)
    graph.add_process("TRIMGALORE", ProcessStatus.RUNNING)
    graph.add_process("STAR_ALIGN", ProcessStatus.PENDING)
    graph.add_process("FEATURECOUNTS", ProcessStatus.PENDING)
    
    # Add dependencies
    graph.add_dependency("FASTQC", "TRIMGALORE")
    graph.add_dependency("TRIMGALORE", "STAR_ALIGN")
    graph.add_dependency("STAR_ALIGN", "FEATURECOUNTS")
    
    # Render
    renderer = SubwayRenderer(graph)
    renderer.render_inline()
    
    print("✅ Basic graph test passed!\n")


def test_parser():
    """Test the Nextflow output parser."""
    print("=" * 60)
    print("TEST 2: Output Parser")
    print("=" * 60)
    
    parser = NextflowOutputParser()
    
    # Test lines from actual Nextflow output
    test_lines = [
        "executor >  local (4)",
        "[4c/d3a7e8] process > FASTQC (1) [100%] 1 of 1 ✔",
        "[a1/b2c3d4] process > TRIMGALORE (sample1) [  0%] 0 of 1",
        "[a1/b2c3d4] process > TRIMGALORE (sample1) [ 50%] 1 of 2",
        "[5f/abc123] CACHED: STAR_ALIGN",
        "ERROR ~ Error executing process > 'FEATURECOUNTS'",
    ]
    
    for line in test_lines:
        print(f"Input:  {line}")
        result = parser.parse_line(line)
        if result:
            print(f"Output: {result}")
        print()
    
    print("✅ Parser test passed!\n")


def test_live_rendering():
    """Test live rendering with animation."""
    print("=" * 60)
    print("TEST 3: Live Rendering (5 seconds)")
    print("=" * 60)
    
    from nf_subway.renderer import SubwayLiveRenderer
    
    graph = SubwayGraph()
    
    # Initial processes
    graph.add_process("FASTQC", ProcessStatus.COMPLETED)
    graph.add_process("TRIMGALORE", ProcessStatus.RUNNING)
    graph.add_process("STAR_ALIGN", ProcessStatus.PENDING)
    graph.add_process("FEATURECOUNTS", ProcessStatus.PENDING)
    
    # Start live rendering
    with SubwayLiveRenderer(graph, refresh_per_second=4) as live_renderer:
        # Simulate progression
        time.sleep(1.5)
        graph.update_process("TRIMGALORE", ProcessStatus.COMPLETED, duration=12.3)
        graph.update_process("STAR_ALIGN", ProcessStatus.RUNNING)
        live_renderer.update()
        
        time.sleep(1.5)
        graph.update_process("STAR_ALIGN", ProcessStatus.COMPLETED, duration=45.8)
        graph.update_process("FEATURECOUNTS", ProcessStatus.RUNNING)
        live_renderer.update()
        
        time.sleep(1.5)
        graph.update_process("FEATURECOUNTS", ProcessStatus.COMPLETED, duration=8.1)
        live_renderer.update()
        
        time.sleep(0.5)
    
    print("\n✅ Live rendering test passed!\n")


def test_orientation_rendering():
    """Test both vertical and horizontal orientation rendering."""
    print("=" * 60)
    print("TEST 0: Orientation Flag Rendering")
    print("=" * 60)

    graph = SubwayGraph()
    # Build a multi-branch workflow
    graph.add_process("A", ProcessStatus.COMPLETED)
    graph.add_process("B1", ProcessStatus.COMPLETED)
    graph.add_process("B2", ProcessStatus.PENDING)
    graph.add_dependency("A", "B1")
    graph.add_dependency("A", "B2")

    renderer = SubwayRenderer(graph)
    print("--VERTICAL--")
    for line in renderer.render_to_lines(orientation="vertical"):
        print(line)
    print("--HORIZONTAL--")
    for line in renderer.render_to_lines(orientation="horizontal"):
        print(line)
    print("✅ Orientation rendering test passed!\n")

def test_parallel_processes():
    """Test rendering of parallel processes."""
    print("=" * 60)
    print("TEST 4: Parallel Processes")
    print("=" * 60)
    
    graph = SubwayGraph()
    
    # Create a branching workflow
    graph.add_process("SPLIT_INPUT", ProcessStatus.COMPLETED)
    graph.add_process("PROCESS_A1", ProcessStatus.COMPLETED)
    graph.add_process("PROCESS_A2", ProcessStatus.RUNNING)
    graph.add_process("PROCESS_B1", ProcessStatus.COMPLETED)
    graph.add_process("PROCESS_B2", ProcessStatus.PENDING)
    graph.add_process("MERGE_OUTPUT", ProcessStatus.PENDING)
    
    # Dependencies
    graph.add_dependency("SPLIT_INPUT", "PROCESS_A1")
    graph.add_dependency("SPLIT_INPUT", "PROCESS_B1")
    graph.add_dependency("PROCESS_A1", "PROCESS_A2")
    graph.add_dependency("PROCESS_B1", "PROCESS_B2")
    graph.add_dependency("PROCESS_A2", "MERGE_OUTPUT")
    graph.add_dependency("PROCESS_B2", "MERGE_OUTPUT")
    
    # Render
    renderer = SubwayRenderer(graph)
    renderer.render_inline()
    
    print("✅ Parallel processes test passed!\n")


def test_all_statuses():
    """Test all process status types."""
    print("=" * 60)
    print("TEST 5: All Process Statuses")
    print("=" * 60)
    
    graph = SubwayGraph()
    
    graph.add_process("COMPLETED_PROCESS", ProcessStatus.COMPLETED)
    graph.add_process("RUNNING_PROCESS", ProcessStatus.RUNNING)
    graph.add_process("PENDING_PROCESS", ProcessStatus.PENDING)
    graph.add_process("FAILED_PROCESS", ProcessStatus.FAILED)
    graph.add_process("CACHED_PROCESS", ProcessStatus.CACHED)
    
    renderer = SubwayRenderer(graph)
    renderer.render_inline()
    
    # Show stats
    stats = graph.get_stats()
    print(f"\nStats: {stats}")
    
    print("✅ All statuses test passed!\n")


def main():
    """Run all tests."""
    print("\n🚇 NF-SUBWAY TEST SUITE 🚇\n")
    
    try:
        test_orientation_rendering()
        test_basic_graph()
        test_parser()
        test_all_statuses()
        test_parallel_processes()
        test_live_rendering()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNF-Subway is ready to use!")
        print("\nTry it with:")
        print("  nextflow run pipeline.nf | nf-subway")
        print("  nf-subway --log .nextflow.log")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
