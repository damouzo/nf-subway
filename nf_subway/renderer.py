from .characters import Characters
from .colors import GitGraphColors, ProcessStatus
from rich.console import Console
from .graph import SubwayGraph
import time
import threading

class GridRenderer:
    """Renders the subway graph on a character grid with consistent column width, allowing true git-graph style connectors."""
    COLUMN_WIDTH = 4

    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.grid = [
            [Characters.thin()['space']] * (num_cols * self.COLUMN_WIDTH)
            for _ in range(num_rows)
        ]
        self.chars = Characters.thin()

    def set_char(self, row, col, char, color=None):
        """Set character at grid position, maintaining 4-char spacing per col."""
        x = col * self.COLUMN_WIDTH
        while len(self.grid) <= row:
            self.grid.append([self.chars['space']] * (self.num_cols * self.COLUMN_WIDTH))
        for i, c in enumerate(char):
            if x+i < len(self.grid[row]):
                self.grid[row][x + i] = c

    def draw_vertical(self, row_from, row_to, col):
        char = self.chars['vertical']
        for row in range(row_from, row_to+1):
            self.set_char(row, col, char)

    def draw_horizontal(self, row, col_from, col_to):
        char = self.chars['horizontal']
        for col in range(col_from, col_to+1):
            for i in range(self.COLUMN_WIDTH):
                self.set_char(row, col, char)

    def to_grid_lines(self):
        all_lines = []
        for row in self.grid:
            line_char_str = ''.join(row).rstrip()
            all_lines.append(line_char_str)
        return all_lines

class SubwayRenderer:
    """Static renderer for SubwayGraph using GridRenderer, supporting vertical/horizontal orientation."""
    def __init__(self, graph: SubwayGraph):
        self.graph = graph
        self.console = Console()

    def render_to_lines(self, orientation='vertical', max_width=100):
        self.graph.assign_lanes()
        nodes = self.graph.get_ordered_processes()
        if not nodes:
            return ["No processes yet..."]
        num_rows = len(nodes)
        num_lanes = max(node.lane for node in nodes) + 1 if nodes else 1
        grid = GridRenderer(num_rows, num_lanes)

        lane_map = {i: None for i in range(num_lanes)}
        for row, node in enumerate(nodes):
            lane = node.lane
            grid.set_char(row, lane, Characters.thin()['dot'])
            for parent in node.parents:
                parent_node = self.graph.nodes[parent]
                if parent_node.lane == lane and row > 0:
                    grid.draw_vertical(row-1, row, lane)

        lines = []
        for row, node in enumerate(nodes):
            gridline = ''.join(grid.grid[row])
            ann_str = (node.annotation or node.name)[:max(0, max_width-len(gridline)-4)]
            status_icon = GitGraphColors.get_icon(node.status)
            line = f"{gridline} {status_icon} {ann_str}"
            lines.append(line.rstrip())
        return lines

    def render_inline(self, orientation='vertical'):
        lines = self.render_to_lines(orientation)
        for l in lines:
            self.console.print(l)

class SubwayLiveRenderer:
    """Live/animated renderer for SubwayGraph using GridRenderer and Console."""
    def __init__(self, graph: SubwayGraph, refresh_per_second=4, orientation='vertical'):
        self.graph = graph
        self.refresh_rate = refresh_per_second
        self.orientation = orientation
        self.console = Console()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def update(self):
        self.render_frame()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def _run(self):
        try:
            while not self._stop_event.is_set():
                self.render_frame(clear_screen=True)
                time.sleep(1 / self.refresh_rate)
        except KeyboardInterrupt:
            return

    def render_frame(self, clear_screen=False):
        if clear_screen:
            print("\033c", end="")
        renderer = SubwayRenderer(self.graph)
        lines = renderer.render_to_lines(self.orientation)
        for l in lines:
            self.console.print(l)
