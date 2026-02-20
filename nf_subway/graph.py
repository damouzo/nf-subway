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
                       annotation: Optional[str] = None):
        """Update the status of an existing process."""
        if name in self.nodes:
            self.nodes[name].status = status
            if duration is not None:
                self.nodes[name].duration = duration
            if annotation is not None:
                self.nodes[name].annotation = annotation
        else:
            # Process not yet seen, create it
            node = self.add_process(name, status)
            if annotation is not None:
                node.annotation = annotation
    
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
        Assign horizontal lanes to processes using git-graph inspired algorithm.
        
        Key principles:
        1. Processes in sequence stay in the same lane
        2. Parallel processes get different lanes  
        3. Lanes are reused when branches complete
        4. Minimize lane switching
        
        This creates a more compact, readable visualization.
        """
        if self.lanes_assigned:
            return
        
        # Reset all lanes
        for node in self.nodes.values():
            node.lane = 0
        
        # Track which lanes are currently "active" (have uncommitted work)
        # Maps lane_id -> process_name occupying it
        active_lanes: Dict[int, str] = {}
        reserved_lanes: Dict[str, int] = {}  # child_name -> reserved lane number
        
        # Build reverse map: process -> its position in execution order
        exec_positions = {name: idx for idx, name in enumerate(self.execution_order)}
        
        for process_name in self.execution_order:
            node = self.nodes[process_name]
            
            # Check if this node has a pre-reserved lane from a parent split
            if process_name in reserved_lanes:
                node.lane = reserved_lanes[process_name]
                active_lanes[node.lane] = process_name
                del reserved_lanes[process_name]
                
            else:
                # Get parent lanes
                parent_lanes = [
                    self.nodes[p].lane 
                    for p in node.parents 
                    if p in self.nodes
                ]
                
                if not parent_lanes:
                    # Root process: use lane 0 or first available
                    if 0 not in active_lanes:
                        node.lane = 0
                        active_lanes[0] = process_name
                    else:
                        # Find first available lane
                        lane = 0
                        while lane in active_lanes:
                            lane += 1
                        node.lane = lane
                        active_lanes[lane] = process_name
                
                elif len(parent_lanes) == 1:
                    # Single parent: inherit its lane
                    parent_lane = parent_lanes[0]
                    node.lane = parent_lane
                    active_lanes[parent_lane] = process_name
                
                else:
                    # Multiple parents (merge): use the leftmost parent's lane
                    node.lane = min(parent_lanes)
                    active_lanes[node.lane] = process_name
                    
                    # Free up the other parent lanes if they're done
                    for p_lane in parent_lanes:
                        if p_lane != node.lane:
                            # Check if this lane has any other active children
                            parent_name = active_lanes.get(p_lane)
                            if parent_name:
                                parent_node = self.nodes.get(parent_name)
                                if parent_node:
                                    # Is this the last child of that lane?
                                    is_last = all(
                                        c == process_name or 
                                        exec_positions.get(c, 999999) < exec_positions[process_name]
                                        for c in parent_node.children
                                    )
                                    if is_last and p_lane in active_lanes:
                                        del active_lanes[p_lane]
            
            # If this node has multiple children, reserve lanes for non-first children
            if len(node.children) > 1:
                # Sort children by execution order for consistency
                sorted_children = sorted(node.children, key=lambda c: exec_positions.get(c, 999999))
                
                # First child will inherit this node's lane (handled above)
                # Other children need new lanes
                for i, child_name in enumerate(sorted_children):
                    if i == 0:
                        continue  # First child inherits lane normally
                    
                    if child_name in self.nodes:
                        # Find a free lane for this child
                        lane = 0
                        used_lanes = set(active_lanes.keys()) | set(reserved_lanes.values())
                        while lane in used_lanes:
                            lane += 1
                        reserved_lanes[child_name] = lane
        
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
