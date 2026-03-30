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
            # Horizontal layout with GridRenderer
            return self._render_horizontal_grid(processes, max_lane)
        
        # Vertical layout with GridRenderer (git-graph style)
        return self._render_vertical_grid(processes, max_lane)
    
    def _render_vertical_grid(self, processes: List[ProcessNode], max_lane: int) -> List[Text]:
        """
        Render vertical layout (git-graph style).

        Uses an active-lanes approach:
        - Every lane draws │ continuously from its first to its last process
        - Fork connectors (├──╮) appear when new subworkflow lanes open
        - Merge connectors (╰──╯) appear when subworkflow lanes close
        - No arrow characters — only box-drawing corners and T-junctions
        """
        from .grid import CharacterSet

        chars = CharacterSet.round()
        num_lanes = max_lane + 1
        n = len(processes)
        CW = 3  # column width: dot-char + 2 padding spaces

        # First/last process index for each lane
        lane_first = {}
        lane_last = {}
        for i, node in enumerate(processes):
            if node.lane not in lane_first:
                lane_first[node.lane] = i
            lane_last[node.lane] = i

        def lane_active(lane, row):
            return lane_first.get(lane, n) <= row <= lane_last.get(lane, -1)

        def dot_char(node):
            if node.status == ProcessStatus.FAILED:
                return "X"
            if node.status == ProcessStatus.PENDING:
                return chars.DOT_SECONDARY  # ○
            return chars.DOT  # ●

        def dot_color(node):
            base = self.colors.branch_color(node.lane)
            if node.status == ProcessStatus.FAILED:
                return "bright_red bold"
            if node.status == ProcessStatus.RUNNING:
                return f"{base} bold" if self.blink.should_show_bright() else f"dim {base}"
            if node.status == ProcessStatus.PENDING:
                return "dim white"
            return base

        max_ann = max(20, self.console.width - num_lanes * CW - 2)
        result = []

        for i, node in enumerate(processes):
            # --- Process row ---
            line = Text()
            for lane in range(num_lanes):
                if lane == node.lane:
                    line.append(dot_char(node), style=dot_color(node))
                elif lane_active(lane, i):
                    line.append(chars.VERTICAL, style=self.colors.branch_color(lane))
                else:
                    line.append(" ")
                line.append("  ")  # 2-char padding → total COLUMN_WIDTH = 3

            ann = self._format_annotation(node)
            if len(ann) > max_ann:
                ann = ann[: max_ann - 1] + "…"
            line.append(ann, style=self._get_style(node))
            result.append(line)

            if i >= n - 1:
                continue

            # --- Connector row between process i and i+1 ---
            above = {l for l in range(num_lanes) if lane_active(l, i)}
            below = {l for l in range(num_lanes) if lane_active(l, i + 1)}
            passing = above & below
            new_lanes = sorted(below - above)
            dying = sorted(above - below)

            cs = [" "] * (num_lanes * CW)
            co = [None] * (num_lanes * CW)

            def sx(x, ch, cl):
                cs[x] = ch
                co[x] = cl

            # 1. Continuing lanes → │
            for lane in passing:
                sx(lane * CW, chars.VERTICAL, self.colors.branch_color(lane))

            # 2. Dying lanes (right-to-left so leftmost corner wins)
            for d in reversed(dying):
                color = self.colors.branch_color(d)
                d_x = d * CW
                sx(d_x, chars.CORNER_LU, color)  # ╯
                tgt_cands = [l for l in passing if l < d]
                tgt = min(tgt_cands) if tgt_cands else (min(below) if below else 0)
                tgt_color = self.colors.branch_color(tgt)
                tgt_x = tgt * CW
                for x in range(tgt_x + 1, d_x):
                    if cs[x] == " ":
                        sx(x, chars.HORIZONTAL, color)
                if cs[tgt_x] == chars.VERTICAL:
                    sx(tgt_x, chars.SPLIT_RIGHT, tgt_color)  # ├

            # 3. New lanes — fork from nearest passing lane to the left
            for new_l in new_lanes:
                color = self.colors.branch_color(new_l)
                new_x = new_l * CW
                src_cands = [l for l in passing if l < new_l]
                src = min(src_cands) if src_cands else (min(above) if above else 0)
                src_color = self.colors.branch_color(src)
                src_x = src * CW
                if cs[src_x] == chars.VERTICAL:
                    sx(src_x, chars.SPLIT_RIGHT, src_color)  # ├
                elif cs[src_x] == " ":
                    sx(src_x, chars.CORNER_RU, src_color)    # ╭
                for x in range(src_x + 1, new_x):
                    if cs[x] == " ":
                        sx(x, chars.HORIZONTAL, color)
                sx(new_x, chars.CORNER_LD, color)  # ╮

            conn = Text()
            for ch, cl in zip(cs, co):
                conn.append(ch, style=cl) if cl else conn.append(ch)
            result.append(conn)

        return result
    
    def _render_horizontal_grid(self, processes: List[ProcessNode], max_lane: int) -> List[Text]:
        """
        Render horizontal layout using grid system (git-graph style).
        
        In horizontal mode:
        - Each lane is a row (top to bottom)
        - Processes flow left to right
        - Annotations appear at the end of each row
        """
        from .grid import GridRenderer, CharacterSet
        
        # Calculate grid dimensions
        # Each process gets 1 column, plus connector columns between
        num_cols = len(processes) * 2 - 1
        num_rows = max_lane + 1
        
        grid = GridRenderer(num_cols, num_rows)
        chars = CharacterSet.round()
        
        # Build mapping of process names to column indices
        process_cols = {}
        for idx, node in enumerate(processes):
            col = idx * 2
            process_cols[node.name] = col
        
        # Draw each process
        for idx, node in enumerate(processes):
            col = idx * 2
            
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
            grid.set_char(node.lane, col, dot_char, dot_color)
            
            # Draw horizontal connections
            if idx < len(processes) - 1:
                connector_col = col + 1
                
                # Get children info for connections
                child_lanes = [
                    self.graph.nodes[c].lane 
                    for c in node.children 
                    if c in self.graph.nodes
                ]
                
                if len(child_lanes) == 1 and child_lanes[0] == node.lane:
                    # Simple horizontal continuation
                    grid.set_char(node.lane, connector_col, chars.HORIZONTAL, dot_color)
                elif len(child_lanes) > 0:
                    # Lane changes - draw appropriately
                    for child_lane in child_lanes:
                        if child_lane == node.lane:
                            grid.set_char(node.lane, connector_col, chars.HORIZONTAL, dot_color)
                        else:
                            # Vertical connection needed
                            min_lane = min(node.lane, child_lane)
                            max_lane = max(node.lane, child_lane)
                            for row in range(min_lane, max_lane + 1):
                                if row == node.lane:
                                    grid.set_char(row, connector_col, chars.SPLIT_RIGHT if node.lane < child_lane else chars.SPLIT_LEFT, dot_color)
                                elif row == child_lane:
                                    grid.set_char(row, connector_col, chars.ARROW_RIGHT if node.lane < child_lane else chars.ARROW_LEFT, dot_color)
                                else:
                                    grid.set_char(row, connector_col, chars.VERTICAL, dot_color)
        
        # Build result lines with annotations
        result = []
        for lane in range(num_rows):
            line = Text()
            
            # Build the grid line for this lane
            for col in range(num_cols):
                x = grid._col_to_x(col)
                for offset in range(grid.COLUMN_WIDTH):
                    grid_cell = grid.grid[lane][x + offset]
                    if grid_cell.color:
                        line.append(grid_cell.char, style=grid_cell.color)
                    else:
                        line.append(grid_cell.char)
            
            # Add annotation for this lane showing which processes are in it
            lane_processes = [p for p in processes if p.lane == lane]
            if lane_processes:
                annotations = []
                for p in lane_processes:
                    ann = self._format_annotation(p)
                    if len(ann) > 30:
                        ann = ann[:27] + "..."
                    annotations.append(ann)
                
                line.append("  ")
                line.append(" → ".join(annotations), style="dim")
            
            result.append(line)
        
        return result

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
        """Annotation text style: use lane color to match git-graph aesthetics."""
        if node.status == ProcessStatus.FAILED:
            return "bright_red bold"
        if node.status == ProcessStatus.RUNNING:
            return f"{self.colors.branch_color(node.lane)} bold"
        if node.status == ProcessStatus.PENDING:
            return "dim"
        if node.status == ProcessStatus.CACHED:
            return f"dim {self.colors.branch_color(node.lane)}"
        return self.colors.branch_color(node.lane)  # COMPLETED
    
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
