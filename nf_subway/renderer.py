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
        Render the graph as a git-graph subway with colored lanes and annotations.
        Supports vertical (default), horizontal, and auto.
        """
        lines: List[Text] = []
        processes = self.graph.get_ordered_processes()
        if not processes:
            return [Text("No processes yet...", style="dim")]

        self.graph.assign_lanes()  # Ensure lanes
        max_lane = max((node.lane for node in processes), default=0)
        lane_width = 2
        sep = " "
        if orientation == 'auto':
            orientation = 'horizontal' if self.console.width > 120 and len(processes) < 15 else 'vertical'

        if orientation == 'horizontal':
            # Horizontal: each lane is a row, dots left→right
            ann_col_width = max(len(node.annotation or node.name) for node in processes)
            grid = [['  ' for _ in range(len(processes))] for __ in range(max_lane+1)]
            for step, node in enumerate(processes):
                grid[node.lane][step] = f'●'
            for lane, row in enumerate(grid):
                line = Text()
                for s, col in enumerate(row):
                    proc = processes[s]
                    cell_style = self._dot_style(proc) if col == '●' and proc.lane == lane else self.colors.branch_color(lane)
                    if col == '●':
                        line.append(col, style=cell_style)
                    else:
                        # Check if this lane is active in the (s-1, s, s+1) neighborhood
                        neighbor_idx = [i for i in [s-1, s, s+1] if 0 <= i < len(row)]
                        neighbor_lanes = [processes[i].lane for i in neighbor_idx]
                        if lane in neighbor_lanes:
                            line.append('─', style=cell_style)
                        else:
                            line.append(' ', style="none")
                    line.append(sep)
                # Optional: show the annotation at the very end of the dot's row
                dot_indices = [s for s in range(len(row)) if processes[s].lane == lane]
                if dot_indices:
                    annotation_idx = dot_indices[-1]
                    annotation = processes[annotation_idx].annotation or processes[annotation_idx].name
                    max_ann_width = self.console.width - (lane_width*len(row)) - 10
                    if len(annotation) > max_ann_width:
                        annotation = annotation[:max_ann_width-3] + '...'
                    line.append(' ', style="none")
                    line.append(annotation, style="dim")
                lines.append(line)
            return lines

        # Default (vertical)
        max_ann_width = self.console.width - (lane_width * (max_lane+1)) - 3
        if max_ann_width < 20:
            max_ann_width = 20
        for idx, node in enumerate(processes):
            line = Text()
            for lane in range(max_lane+1):
                if lane == node.lane:
                    dot_style = self._dot_style(node)
                    if node.status == ProcessStatus.RUNNING:
                        dot_style = self.blink.get_running_style()
                    line.append("●", style=dot_style)
                else:
                    # For connector lines, look up node.lane of parents and children
                    parent_lanes = [self.graph.nodes[p].lane for p in getattr(node, 'parents', []) if p in self.graph.nodes]
                    child_lanes = [self.graph.nodes[c].lane for c in getattr(node, 'children', []) if c in self.graph.nodes]
                    if lane in parent_lanes or lane in child_lanes:
                        branch_col = self.colors.branch_color(lane)
                        line.append("│", style=branch_col)
                    else:
                        line.append(sep)
                line.append(sep)
            annotation = node.annotation or node.name
            if len(annotation) > max_ann_width:
                annotation = annotation[:max_ann_width-3] + "..."
            line.append(" ", style="none")
            line.append(annotation, style="dim")
            lines.append(line)
        return lines

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
            padding=(1, 2),
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
        
        parts = [f"🚇 NF-Subway ({total} processes)"]
        
        if running > 0:
            parts.append(f"⚡ {running} running")
        if completed > 0:
            parts.append(f"✅ {completed} done")
        if failed > 0:
            parts.append(f"❌ {failed} failed")
        
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
