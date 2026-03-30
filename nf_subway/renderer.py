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
    
    def render_to_lines(self, max_rows: int = 0) -> List[Text]:
        """
        Render the graph (vertical, git-graph style).
        If max_rows > 0, only the last rows are returned (sliding window — prevents
        Rich Live clipping when the pipeline is larger than the terminal height).
        """
        processes = self.graph.get_ordered_processes()
        if not processes:
            return [Text("No processes yet...", style="dim")]

        self.graph.assign_lanes()
        max_lane = max((node.lane for node in processes), default=0)
        lines = self._render_vertical_grid(processes, max_lane)

        if max_rows > 0 and len(lines) > max_rows:
            lines = lines[-max_rows:]
        return lines
    
    def _render_vertical_grid(self, processes: List[ProcessNode], max_lane: int) -> List[Text]:
        """
        Render vertical layout (git-graph style).

        Connector-row rules:
        - Between every pair of consecutive processes, exactly ONE connector row
          is emitted — showing │ for each active lane plus fork/merge characters
          when the branch topology changes.
        - EXCEPTION: when a new lane opens as the very first branch (only ONE
          lane was active before), the fork is shown INLINE in the new process's
          dot row (├──●) and the preceding connector row is skipped.  This keeps
          the first branch opening compact while still connecting all other dots.
        """
        from .grid import CharacterSet

        chars = CharacterSet.round()
        num_lanes = max_lane + 1
        n = len(processes)
        CW = 3

        lane_first: dict = {}
        lane_last: dict = {}
        for i, node in enumerate(processes):
            if node.lane not in lane_first:
                lane_first[node.lane] = i
            lane_last[node.lane] = i

        def lane_active(lane, row):
            return lane_first.get(lane, n) <= row <= lane_last.get(lane, -1)

        def dot_ch(node):
            if node.status == ProcessStatus.FAILED:
                return "X"
            if node.status in (ProcessStatus.PENDING, ProcessStatus.CACHED):
                return chars.DOT_SECONDARY
            return chars.DOT

        def dot_cl(node):
            base = self.colors.branch_color(node.lane)
            if node.status == ProcessStatus.FAILED:
                return "bright_red bold"
            if node.status == ProcessStatus.RUNNING:
                return f"{base} bold" if self.blink.should_show_bright() else f"dim {base}"
            if node.status == ProcessStatus.PENDING:
                return "dim white"
            if node.status == ProcessStatus.CACHED:
                return "yellow"
            return base

        # Inline-fork map: process_idx -> source_lane
        # Condition: exactly ONE new lane, at least one lane to the left to
        # act as source — fold the fork ├── directly into the dot row.
        # Two sub-cases:
        #   a) Normal: source lane is still active (passing) — no dying lanes
        #   b) Transient: source lane ends AT THIS STEP (dying) — e.g. last
        #      top-level process ends while first subworkflow starts.  Without
        #      this case a bare ╯──╮ connector row appears during live render.
        inline_fork: dict = {}
        for i, node in enumerate(processes):
            if i == 0 or i != lane_first.get(node.lane, -1):
                continue
            above = frozenset(l for l in range(num_lanes) if lane_active(l, i - 1))
            below = frozenset(l for l in range(num_lanes) if lane_active(l, i))
            new_here = below - above
            dying_here = above - below
            passing_here = above & below
            if len(new_here) == 1 and not dying_here:
                # (a) source is passing
                src_cands = [l for l in passing_here if l < node.lane]
                if src_cands:
                    inline_fork[i] = min(src_cands)
            elif len(new_here) == 1 and not passing_here:
                # (b) source is dying — all previous lanes end here
                src_cands = [l for l in dying_here if l < node.lane]
                if src_cands:
                    inline_fork[i] = min(src_cands)

        # Inline-merge map: process_idx -> target_lane
        # Mirrors inline_fork: the LAST dot on a side lane shows ┤──...──●
        # (pointing back leftward to the main lane) instead of a stray ╯ suffix.
        inline_merge: dict = {}
        for i, node in enumerate(processes):
            if node.lane == 0 or i != lane_last.get(node.lane, -1) or i == n - 1:
                continue
            tgt_cands = [l for l in range(num_lanes) if lane_active(l, i) and l < node.lane]
            if tgt_cands:
                inline_merge[i] = min(tgt_cands)

        max_ann = max(20, self.console.width - num_lanes * CW - 2)

        # Pre-compute name_width: the width of the longest "[id] NAME" prefix
        # across all annotations that contain a " | " separator.  This makes
        # the progress column (N of M ✔) align vertically like Nextflow's display.
        name_width = 0
        for node in processes:
            ann = node.annotation or node.name
            if " | " in ann:
                left = ann.split(" | ", 1)[0]
                if len(left) > name_width:
                    name_width = len(left)

        result = []

        for i, node in enumerate(processes):
            # ── Process (dot) row ──────────────────────────────────────────
            src = inline_fork.get(i)   # fork: render ├──...──● inline
            mrg = inline_merge.get(i)  # merge: render ┤──...──● inline
            line = Text()
            for lane in range(num_lanes):
                is_active = lane_active(lane, i)
                if src is not None and src <= lane <= node.lane:
                    # ── inline fork zone ──────────────────────────────────
                    if lane == node.lane:
                        line.append(dot_ch(node), style=dot_cl(node))
                        line.append("  ")
                    elif lane == src:
                        line.append("├", style=self.colors.branch_color(src))
                        line.append("──", style=self.colors.branch_color(node.lane))
                    else:
                        cross = "┼" if is_active else "─"
                        col = self.colors.branch_color(lane) if is_active else self.colors.branch_color(node.lane)
                        line.append(cross, style=col)
                        line.append("──", style=self.colors.branch_color(node.lane))
                elif mrg is not None and mrg <= lane <= node.lane:
                    # ── inline merge zone ─────────────────────────────────
                    # Dashed line (╌╌) in the closing branch color signals
                    # "this branch is returning to main". Perfectly centered
                    # because ╌ is a pure box-drawing character.
                    branch_col = self.colors.branch_color(node.lane)
                    if lane == node.lane:
                        line.append(dot_ch(node), style=dot_cl(node))
                        line.append("  ")
                    elif lane == mrg:
                        line.append(chars.VERTICAL, style=self.colors.branch_color(mrg))
                        line.append("──", style=branch_col)
                    else:
                        cross = "┼" if is_active else "─"
                        col = self.colors.branch_color(lane) if is_active else branch_col
                        line.append(cross, style=col)
                        line.append("──", style=branch_col)
                elif lane == node.lane:
                    line.append(dot_ch(node), style=dot_cl(node))
                    line.append("  ")
                elif is_active:
                    line.append(chars.VERTICAL, style=self.colors.branch_color(lane))
                    line.append("  ")
                else:
                    line.append("   ")

            ann = self._format_annotation(node, name_width=name_width)
            if len(ann) > max_ann:
                ann = ann[: max_ann - 1] + "…"
            line.append(ann, style=self._get_style(node))
            result.append(line)

            if i >= n - 1:
                continue

            # ── Connector row ──────────────────────────────────────────────
            # Skip when the next process will show an inline fork —
            # the ├── in that dot row is the visual connector.
            if i + 1 in inline_fork:
                continue

            above = {l for l in range(num_lanes) if lane_active(l, i)}
            below = {l for l in range(num_lanes) if lane_active(l, i + 1)}
            passing = above & below
            new_lanes = sorted(below - above)
            dying = sorted(above - below)

            # Only emit connector rows when new lanes open.
            # Merges are implicit: side lanes simply stop appearing after their last process.
            if not new_lanes:
                continue

            cs = [" "] * (num_lanes * CW)
            co: list = [None] * (num_lanes * CW)

            def sx(x, ch, cl):
                cs[x] = ch
                co[x] = cl

            # Continuing lanes → │
            for lane in passing:
                sx(lane * CW, chars.VERTICAL, self.colors.branch_color(lane))

            # Dying lanes (merge back) — right-to-left so leftmost corner wins
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

            # New lanes — fork from leftmost passing lane
            for new_l in new_lanes:
                color = self.colors.branch_color(new_l)
                new_x = new_l * CW
                src_cands = [l for l in passing if l < new_l]
                src2 = min(src_cands) if src_cands else (min(above) if above else 0)
                src_color = self.colors.branch_color(src2)
                src_x = src2 * CW
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
            # Blink the annotation text in sync with the dot
            base = self.colors.branch_color(node.lane)
            return f"{base} bold" if self.blink.should_show_bright() else f"dim {base}"
        if node.status == ProcessStatus.PENDING:
            return "dim"
        if node.status == ProcessStatus.CACHED:
            return f"dim {self.colors.branch_color(node.lane)}"
        return self.colors.branch_color(node.lane)  # COMPLETED
    
    def _format_annotation(self, node: ProcessNode, name_width: int = 0) -> str:
        """Format the annotation text for a process.
        
        If name_width > 0, the process-name portion is padded to that width
        so the progress column (N of M) lines up across all rows.
        """
        annotation = node.annotation or node.name

        # Split on " | " to separate name part from progress part
        if " | " in annotation and name_width > 0:
            left, right = annotation.split(" | ", 1)
            annotation = f"{left:<{name_width}} | {right}"

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

    
    def render_panel(self) -> Panel:
        """Render the graph as a Rich Panel, fitting within the terminal height."""
        available = max(4, (self.console.height or 40) - 4)
        lines = self.render_to_lines(max_rows=available)

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
        self.renderer = SubwayRenderer(graph)
        self.refresh_per_second = refresh_per_second
        self.live = None
    
    def start(self):
        """Start the live rendering."""
        self.live = Live(
            self.renderer.render_panel(),
            refresh_per_second=self.refresh_per_second,
            console=self.renderer.console
        )
        self.live.start()

    def update(self):
        """Update the display with current graph state."""
        if self.live:
            self.renderer.tick_animation()
            self.live.update(self.renderer.render_panel())

    def render_final(self):
        """Force a final render with blink in the bright phase, then stop."""
        if self.live:
            self.renderer.blink.frame = 0  # pin to bright state permanently
            self.live.update(self.renderer.render_panel())

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
