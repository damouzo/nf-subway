"""
Terminal renderer for the subway graph using Rich.

Inspired by git-graph's clean and comprehensible visualization style.
"""

from typing import List
from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live

from .graph import SubwayGraph, ProcessNode
from .colors import GitGraphColors, BlinkEffect, ProcessStatus


class SubwayRenderer:
    """
    Renders the pipeline graph as a subway-style visualization.
    
    Features:
    - Vertical flow (top to bottom)
    - Clean git-graph inspired aesthetics
    - Color-coded status (gray/blue/green/red)
    - Blinking animation for running processes
    """
    
    def __init__(self, graph: SubwayGraph):
        self.graph = graph
        self.console = Console()
        self.blink = BlinkEffect()
        self.colors = GitGraphColors()
    
    def render_to_lines(self, orientation='vertical') -> List[Text]:
        """
        Render the graph using grid-based layout (git-graph style).
        Supports vertical (default), horizontal, and auto.
        """
        from .grid import GridRenderer, CharacterSet
        
        processes = self.graph.get_ordered_processes()
        if not processes:
            return [Text("No processes yet...", style="dim")]

        self.graph.assign_lanes()
        max_lane = max((node.lane for node in processes), default=0)
        
        if orientation == 'auto':
            orientation = 'horizontal' if self.console.width > 120 and len(processes) < 15 else 'vertical'
        
        if orientation == 'horizontal':
            # TODO: Implement horizontal layout with grid
            # For now, fall back to simple horizontal rendering
            return self._render_horizontal_simple(processes, max_lane)
        
        # Vertical layout with GridRenderer (git-graph style)
        return self._render_vertical_grid(processes, max_lane)
    
    def _render_vertical_grid(self, processes: List[ProcessNode], max_lane: int) -> List[Text]:
        """
        Render vertical layout using grid system.
        
        This creates a git-graph style visualization with:
        - Consistent 4-character column width
        - Box-drawing characters for connections
        - Color-coded lanes
        """
        from .grid import GridRenderer, CharacterSet
        
        # Calculate grid dimensions
        # Each process gets 1 row for the dot, plus connection rows between
        num_rows = len(processes) * 2 - 1  # dot rows + connector rows
        num_cols = max_lane + 1
        
        grid = GridRenderer(num_cols, num_rows)
        chars = CharacterSet.round()
        
        # Build a mapping of process names to their row indices
        process_rows = {}
        lane_rows = {}
        for idx, node in enumerate(processes):
            row = idx * 2
            process_rows[node.name] = row
            lane_rows.setdefault(node.lane, []).append(row)
        
        # Draw each process
        for idx, node in enumerate(processes):
            row = idx * 2
            
            # Determine dot character and color
            dot_color = self._lane_color(node)
            
            if node.status == ProcessStatus.COMPLETED:
                dot_char = chars.DOT
            elif node.status == ProcessStatus.FAILED:
                dot_char = 'X'
                dot_color = 'bright_red'
            elif node.status == ProcessStatus.RUNNING:
                dot_char = chars.DOT
                dot_color = self.blink.get_running_style()
            elif node.status == ProcessStatus.CACHED:
                dot_char = chars.DOT_SECONDARY
            else:  # PENDING
                dot_char = chars.DOT_SECONDARY
                dot_color = 'dim white'
            
            # Draw the dot
            grid.set_char(row, node.lane, dot_char, dot_color)
            
            # Get parent and child lanes
            parent_lanes = [
                self.graph.nodes[p].lane 
                for p in node.parents 
                if p in self.graph.nodes
            ]
            child_lanes = [
                self.graph.nodes[c].lane 
                for c in node.children 
                if c in self.graph.nodes
            ]
            
            # Draw connections from parents (if not first process)
            if idx > 0:
                connector_row = row - 1
                
                if len(parent_lanes) > 1:
                    # Merge from multiple parents
                    grid.draw_merge(connector_row, parent_lanes, node.lane, dot_color)
                elif len(parent_lanes) == 1:
                    parent_lane = parent_lanes[0]
                    if parent_lane == node.lane:
                        # Simple vertical continuation
                        grid.set_char(connector_row, node.lane, chars.VERTICAL, dot_color)
                    else:
                        # Lane change - draw corner
                        if parent_lane < node.lane:
                            grid.set_char(connector_row, parent_lane, chars.CORNER_LD, dot_color)
                            grid.draw_horizontal_line(connector_row, parent_lane, node.lane, dot_color)
                            grid.set_char(connector_row, node.lane, chars.ARROW_RIGHT, dot_color)
                        else:
                            grid.set_char(connector_row, node.lane, chars.ARROW_LEFT, dot_color)
                            grid.draw_horizontal_line(connector_row, node.lane, parent_lane, dot_color)
                            grid.set_char(connector_row, parent_lane, chars.CORNER_LU, dot_color)
            
            # Draw connections to children (if not last process)
            if idx < len(processes) - 1:
                connector_row = row + 1
                
                if len(child_lanes) > 1:
                    # Split to multiple children
                    grid.draw_split(connector_row, node.lane, child_lanes, dot_color)
                elif len(child_lanes) == 1:
                    child_lane = child_lanes[0]
                    if child_lane == node.lane:
                        # Simple vertical continuation
                        grid.set_char(connector_row, node.lane, chars.VERTICAL, dot_color)
                    # Lane changes will be drawn by the child process

        # Draw continuous vertical lane strokes between nodes in the same lane
        # to avoid broken/discontinuous branch appearance.
        for lane, rows in lane_rows.items():
            ordered_rows = sorted(set(rows))
            if len(ordered_rows) < 2:
                continue
            lane_color = self.colors.branch_color(lane)
            for row_start, row_end in zip(ordered_rows, ordered_rows[1:]):
                grid.draw_vertical_line(row_start, row_end, lane, lane_color)
        
        # Build result with annotations
        result = []
        max_ann_width = self.console.width - (grid.COLUMN_WIDTH * num_cols) - 3
        if max_ann_width < 20:
            max_ann_width = 20
        
        for idx, node in enumerate(processes):
            row = idx * 2
            
            # Build the grid line for this row
            line = Text()
            for col in range(num_cols):
                cell = grid.get_char(row, col)
                x = grid._col_to_x(col)
                
                # Add all characters for this column (width = COLUMN_WIDTH)
                for offset in range(grid.COLUMN_WIDTH):
                    grid_cell = grid.grid[row][x + offset]
                    if grid_cell.color:
                        line.append(grid_cell.char, style=grid_cell.color)
                    else:
                        line.append(grid_cell.char)
            
            # Add annotation
            annotation = self._format_annotation(node)
            if len(annotation) > max_ann_width:
                annotation = annotation[:max_ann_width-3] + "..."
            
            line.append(" ")
            line.append(annotation, style=self._get_style(node))
            
            result.append(line)
            
            # Add connector line if exists
            if idx < len(processes) - 1:
                connector_row = row + 1
                connector_line = Text()
                for col in range(num_cols):
                    x = grid._col_to_x(col)
                    for offset in range(grid.COLUMN_WIDTH):
                        grid_cell = grid.grid[connector_row][x + offset]
                        if grid_cell.color:
                            connector_line.append(grid_cell.char, style=grid_cell.color)
                        else:
                            connector_line.append(grid_cell.char)
                result.append(connector_line)
        
        return result
    
    def _render_horizontal_simple(self, processes: List[ProcessNode], max_lane: int) -> List[Text]:
        """Simple horizontal rendering (fallback)."""
        lines = []
        sep = " "
        
        # Horizontal: each lane is a row, dots left→right
        for lane in range(max_lane + 1):
            line = Text()
            for node in processes:
                if node.lane == lane:
                    dot_style = self._lane_color(node)
                    if node.status == ProcessStatus.RUNNING:
                        dot_style = self.blink.get_running_style()
                    line.append("●", style=dot_style)
                else:
                    # Check if lane is active at this position
                    parent_lanes = [
                        self.graph.nodes[p].lane 
                        for p in node.parents 
                        if p in self.graph.nodes
                    ]
                    child_lanes = [
                        self.graph.nodes[c].lane 
                        for c in node.children 
                        if c in self.graph.nodes
                    ]
                    if lane in parent_lanes or lane in child_lanes:
                        line.append("─", style=self.colors.branch_color(lane))
                    else:
                        line.append(" ")
                line.append(sep)
            lines.append(line)
        
        return lines

    def _lane_color(self, node: ProcessNode) -> str:
        """
        Get color for a node based on its lane (git-graph style).
        
        Failed nodes always get red, but otherwise we color by lane
        to create the multi-colored subway effect.
        """
        if node.status == ProcessStatus.FAILED:
            return "bright_red"
        
        # Color by lane (git-graph style)
        return self.colors.branch_color(node.lane)
    
    def _dot_style(self, node: ProcessNode) -> str:
        """Choose color for dot node: pending (gray), running (blink blue), complete (green), failed (red), by branch color border."""
        if node.status == ProcessStatus.COMPLETED:
            return "bright_green"
        elif node.status == ProcessStatus.PENDING:
            return "gray"
        elif node.status == ProcessStatus.FAILED:
            return "bright_red"
        elif node.status == ProcessStatus.RUNNING:
            return self.blink.get_running_style()
        return self.colors.branch_color(node.lane)
    
    def _get_icon(self, node: ProcessNode) -> str:
        """Get icon for process status - just returns empty string since we use colored dots."""
        return ""
    
    def _get_style(self, node: ProcessNode) -> str:
        """Get text style for process annotation."""
        if node.status == ProcessStatus.COMPLETED:
            return "dim green"
        elif node.status == ProcessStatus.FAILED:
            return "bright_red"
        elif node.status == ProcessStatus.RUNNING:
            return "bright_blue"
        elif node.status == ProcessStatus.CACHED:
            return "cyan"
        else:
            return "dim"
    
    def _format_annotation(self, node: ProcessNode) -> str:
        """Format the annotation text for a process."""
        annotation = node.annotation or node.name
        
        # Add duration if available
        if node.duration and node.status == ProcessStatus.COMPLETED:
            annotation += f" ({self._format_duration(node.duration)})"
        
        return annotation
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    
    def render_panel(self, orientation='vertical') -> Panel:
        """Render the graph as a Rich Panel."""
        lines = self.render_to_lines(orientation=orientation)
        
        # Combine lines into single text
        text = Text()
        for i, line in enumerate(lines):
            text.append_text(line)
            if i < len(lines) - 1:
                text.append("\n")
        
        # Get stats for the title
        stats = self.graph.get_stats()
        title = self._format_title(stats)
        
        return Panel(
            text,
            title=title,
            border_style=self.colors.SEPARATOR,
            padding=(0, 1),
        )
    
    def render_inline(self):
        """
        Render the graph inline (for integration with Nextflow output).
        
        Prints the graph with separators above and below.
        """
        width = self.console.width
        
        # Top separator
        self.console.print("━" * width, style=self.colors.SEPARATOR)
        stats = self.graph.get_stats()
        title = self._format_title(stats)
        self.console.print(title, justify="center", style="bold bright_blue")
        self.console.print("━" * width, style=self.colors.SEPARATOR)
        
        # Graph content
        lines = self.render_to_lines()
        for line in lines:
            self.console.print(line)
        
        # Bottom separator
        self.console.print("━" * width, style=self.colors.SEPARATOR)
        self.console.print()  # Extra newline
    
    def render_live(self, refresh_per_second: int = 4):
        """
        Start a live rendering session that updates automatically.
        
        Args:
            refresh_per_second: How many times per second to refresh
        """
        with Live(self.render_panel(), refresh_per_second=refresh_per_second,
                  console=self.console) as live:
            # This will be updated by the main loop
            return live
    
    def _get_icon(self, node: ProcessNode) -> str:
        """Get the icon for a process based on its status."""
        return self.colors.get_icon(node.status)
    
    def _get_style(self, node: ProcessNode) -> str:
        """Get the Rich style for a process based on its status."""
        if node.status == ProcessStatus.RUNNING:
            # Use blinking effect for running processes
            return self.blink.get_running_style()
        return self.colors.get_process_style(node.status)
    
    def _format_title(self, stats: dict) -> str:
        """Format the title with stats."""
        total = stats['total']
        running = stats['running']
        completed = stats['completed']
        failed = stats['failed']
        
        parts = [f"NF-Subway ({total} processes)"]
        
        if running > 0:
            parts.append(f"{running} running")
        if completed > 0:
            parts.append(f"{completed} done")
        if failed > 0:
            parts.append(f"{failed} failed")
        
        return " | ".join(parts)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def tick_animation(self):
        """Advance the animation by one frame (for blinking effect)."""
        self.blink.tick()


class SubwayLiveRenderer:
    """
    Manager for live rendering with automatic updates.
    
    Wraps Rich's Live display and provides convenient methods for
    updating the subway graph display.
    """
    
    def __init__(self, graph: SubwayGraph, refresh_per_second: int = 4, orientation: str = 'auto'):
        self.graph = graph
        self.orientation = orientation
        self.renderer = SubwayRenderer(graph)
        self.refresh_per_second = refresh_per_second
        self.live = None
    
    def start(self):
        """Start the live rendering."""
        self.live = Live(
            self.renderer.render_panel(orientation=self.orientation),
            refresh_per_second=self.refresh_per_second,
            console=self.renderer.console
        )
        self.live.start()
    
    def update(self):
        """Update the display with current graph state."""
        if self.live:
            self.renderer.tick_animation()  # Advance blink animation
            self.live.update(self.renderer.render_panel(orientation=self.orientation))
    
    def stop(self):
        """Stop the live rendering."""
        if self.live:
            self.live.stop()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
