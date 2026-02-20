"""
NF-Subway: Git-graph style visualization for Nextflow pipelines.

Provides real-time monitoring and visualization of Nextflow pipeline execution
with a clean, subway-map inspired aesthetic.
"""

__version__ = "0.1.0"

from .graph import SubwayGraph, ProcessNode
from .colors import ProcessStatus, GitGraphColors, BlinkEffect
from .parser import NextflowOutputParser, NextflowTraceParser
from .renderer import SubwayRenderer, SubwayLiveRenderer
from .monitor import NextflowMonitor, FileMonitor, monitor_nextflow_stdout, monitor_nextflow_logfile

__all__ = [
    # Core classes
    'SubwayGraph',
    'ProcessNode',
    'ProcessStatus',
    'GitGraphColors',
    'BlinkEffect',
    
    # Parsing
    'NextflowOutputParser',
    'NextflowTraceParser',
    
    # Rendering
    'SubwayRenderer',
    'SubwayLiveRenderer',
    
    # Monitoring
    'NextflowMonitor',
    'FileMonitor',
    'monitor_nextflow_stdout',
    'monitor_nextflow_logfile',
]
