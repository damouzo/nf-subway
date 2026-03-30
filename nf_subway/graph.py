"""
Graph data structure for representing the Nextflow pipeline DAG.

Inspired by git-graph's approach to commit graph visualization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from .colors import ProcessStatus


@dataclass
class ProcessNode:
    """Represents a single process in the pipeline."""
    name: str
    status: ProcessStatus = ProcessStatus.PENDING
    task_id: Optional[str] = None
    submit_time: Optional[float] = None
    complete_time: Optional[float] = None
    duration: Optional[float] = None
    children: List[str] = field(default_factory=list)
    parents: List[str] = field(default_factory=list)
    lane: int = 0  # For parallel process visualization
    # git-graph style visual fields
    job_id: Optional[str] = None
    progress: Optional[str] = None
    annotation: Optional[str] = None  # Used for right-side info (job id, label, progress)
    branch_color: Optional[int] = None  # Index into the branch color palette
    workflow_prefix: Optional[str] = None  # Subworkflow name, or None for top-level processes
    base_name: Optional[str] = None        # Base process name without instance number

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal node (no children)."""
        return len(self.children) == 0
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root node (no parents)."""
        return len(self.parents) == 0


class SubwayGraph:
    """
    Represents the pipeline execution as a directed acyclic graph (DAG).
    
    Visualized as a subway map with vertical flow:
    - Processes flow from top to bottom
    - Parallel processes occupy different "lanes"
    - Connections shown with vertical lines and branches
    """
    
    def __init__(self):
        self.nodes: Dict[str, ProcessNode] = {}
        self.execution_order: List[str] = []  # Order processes appear
        self.lanes_assigned = False
    
    def add_process(self, name: str, status: ProcessStatus = ProcessStatus.PENDING,
                    task_id: Optional[str] = None) -> ProcessNode:
        """Add a new process to the graph."""
        if name not in self.nodes:
            node = ProcessNode(name=name, status=status, task_id=task_id)
            self.nodes[name] = node
            self.execution_order.append(name)
            self.lanes_assigned = False  # Need to recalculate lanes
            return node
        return self.nodes[name]
    
    def update_process(self, name: str, status: ProcessStatus,
                       duration: Optional[float] = None,
                       annotation: Optional[str] = None,
                       workflow_prefix: Optional[str] = None,
                       base_name: Optional[str] = None):
        """Update the status of an existing process."""
        if name in self.nodes:
            node = self.nodes[name]
            node.status = status
            if duration is not None:
                node.duration = duration
            if annotation is not None:
                node.annotation = annotation
            if workflow_prefix is not None and node.workflow_prefix is None:
                node.workflow_prefix = workflow_prefix
                self.lanes_assigned = False
        else:
            # Process not yet seen, create it
            node = self.add_process(name, status)
            if annotation is not None:
                node.annotation = annotation
            if workflow_prefix is not None:
                node.workflow_prefix = workflow_prefix
            if base_name is not None:
                node.base_name = base_name
    
    def add_dependency(self, parent: str, child: str):
        """Add a dependency relationship between two processes."""
        # Ensure both nodes exist
        if parent not in self.nodes:
            self.add_process(parent)
        if child not in self.nodes:
            self.add_process(child)
        
        # Add the relationship
        parent_node = self.nodes[parent]
        child_node = self.nodes[child]
        
        if child not in parent_node.children:
            parent_node.children.append(child)
        if parent not in child_node.parents:
            child_node.parents.append(parent)
        
        self.lanes_assigned = False
    
    def assign_lanes(self):
        """
        Assign lanes by workflow prefix.

        - Main-branch (no subworkflow prefix) → lane 0
        - Each distinct subworkflow prefix → its own unique lane

        Nextflow truncates long subworkflow names differently depending on
        terminal width, so the same workflow can appear as both its full name
        (e.g. "alignment_based_quantification") and a short prefix
        (e.g. "ali").  We unify them by checking whether any known prefix is
        a leading substring of the incoming prefix, or vice versa.
        """
        if self.lanes_assigned:
            return

        prefix_to_lane: Dict[str, int] = {"": 0}  # main branch always lane 0
        next_lane = [1]

        def canonical(prefix: str) -> str:
            """Return the already-known key that matches prefix, or prefix itself."""
            if not prefix:
                return ""  # main branch always maps to itself; "" starts every string
            for known in prefix_to_lane:
                if not known:
                    continue
                if known.startswith(prefix) or prefix.startswith(known):
                    return known
            return prefix

        def get_lane(prefix: str) -> int:
            key = canonical(prefix)
            if key not in prefix_to_lane:
                prefix_to_lane[key] = next_lane[0]
                next_lane[0] += 1
            return prefix_to_lane[key]

        for name in self.execution_order:
            node = self.nodes[name]
            node.lane = get_lane(node.workflow_prefix or "")

        self.lanes_assigned = True
    
    def get_ordered_processes(self) -> List[ProcessNode]:
        """Get processes in execution order."""
        return [self.nodes[name] for name in self.execution_order if name in self.nodes]
    
    def get_root_processes(self) -> List[ProcessNode]:
        """Get all root processes (no parents)."""
        return [node for node in self.nodes.values() if node.is_root]
    
    def get_terminal_processes(self) -> List[ProcessNode]:
        """Get all terminal processes (no children)."""
        return [node for node in self.nodes.values() if node.is_terminal]
    
    def get_active_processes(self) -> List[ProcessNode]:
        """Get all currently running processes."""
        return [
            node for node in self.nodes.values() 
            if node.status == ProcessStatus.RUNNING
        ]
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the pipeline execution."""
        stats = {
            'total': len(self.nodes),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cached': 0,
        }
        
        for node in self.nodes.values():
            stats[node.status.value] += 1
        
        return stats
    
    def clear(self):
        """Clear all processes from the graph."""
        self.nodes.clear()
        self.execution_order.clear()
        self.lanes_assigned = False
