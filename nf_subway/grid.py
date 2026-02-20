"""
Grid-based layout system inspired by git-graph.

This module provides a character grid system for rendering pipeline
visualizations with consistent spacing and professional box-drawing characters.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class GridCell:
    """A single cell in the character grid."""
    char: str = ' '
    color: Optional[str] = None


class CharacterSet:
    """
    Box-drawing characters for graph visualization.
    
    Inspired by git-graph's character sets (thin, round, bold, double).
    This implementation provides the 'thin' style by default.
    """
    
    # Basic elements
    DOT = '●'
    DOT_SECONDARY = '○'
    SPACE = ' '
    
    # Lines
    VERTICAL = '│'
    HORIZONTAL = '─'
    
    # Corners
    CORNER_RD = '└'  # Round down (bottom-left)
    CORNER_RU = '┌'  # Round up (top-left)
    CORNER_LD = '┐'  # Left down (top-right)
    CORNER_LU = '┘'  # Left up (bottom-right)
    
    # Splits and merges
    SPLIT_RIGHT = '├'
    SPLIT_LEFT = '┤'
    MERGE_DOWN = '┬'
    MERGE_UP = '┴'
    CROSS = '┼'
    
    @classmethod
    def thin(cls):
        """Default thin lines (same as base class)."""
        return cls()
    
    @classmethod
    def round(cls):
        """Rounded corners for softer appearance."""
        chars = cls()
        chars.CORNER_RD = '╰'
        chars.CORNER_RU = '╭'
        chars.CORNER_LD = '╮'
        chars.CORNER_LU = '╯'
        return chars


class GridRenderer:
    """
    Renders a graph on a character grid with consistent spacing.
    
    Inspired by git-graph's layout engine, this provides:
    - Consistent column width (4 characters, like git-graph)
    - Professional box-drawing characters
    - Methods for drawing lines, merges, and splits
    
    Example:
        grid = GridRenderer(num_columns=3, num_rows=5)
        grid.set_char(0, 1, '●', color='bright_blue')
        grid.draw_vertical_line(0, 2, 1, color='bright_blue')
        text = grid.to_rich_text()
    """
    
    COLUMN_WIDTH = 4  # Same as git-graph
    
    def __init__(self, num_columns: int, num_rows: int, chars: Optional[CharacterSet] = None):
        """
        Initialize a new grid.
        
        Args:
            num_columns: Number of columns (lanes)
            num_rows: Number of rows
            chars: Character set to use (defaults to thin)
        """
        self.num_columns = num_columns
        self.num_rows = num_rows
        self.width = num_columns * self.COLUMN_WIDTH
        self.chars = chars or CharacterSet.thin()
        
        # Initialize empty grid
        self.grid: List[List[GridCell]] = [
            [GridCell() for _ in range(self.width)]
            for _ in range(num_rows)
        ]
    
    def _col_to_x(self, col: int) -> int:
        """Convert column index to x position in grid."""
        return col * self.COLUMN_WIDTH
    
    def set_char(self, row: int, col: int, char: str, color: Optional[str] = None):
        """
        Set a character at a grid position.
        
        Args:
            row: Row index (0-based)
            col: Column index (0-based)
            char: Character to place
            color: Optional color style (Rich markup)
        """
        if row < 0 or row >= self.num_rows:
            return
        if col < 0 or col >= self.num_columns:
            return
        
        x = self._col_to_x(col)
        self.grid[row][x] = GridCell(char=char, color=color)
    
    def get_char(self, row: int, col: int) -> Optional[GridCell]:
        """Get the character at a grid position."""
        if row < 0 or row >= self.num_rows:
            return None
        if col < 0 or col >= self.num_columns:
            return None
        
        x = self._col_to_x(col)
        return self.grid[row][x]
    
    def draw_vertical_line(self, row_start: int, row_end: int, col: int, 
                          color: Optional[str] = None):
        """
        Draw a vertical line connecting two rows in a column.
        
        Args:
            row_start: Starting row
            row_end: Ending row  
            col: Column to draw in
            color: Optional color style
        """
        for row in range(row_start + 1, row_end):
            self.set_char(row, col, self.chars.VERTICAL, color)
    
    def draw_horizontal_line(self, row: int, col_start: int, col_end: int,
                            color: Optional[str] = None):
        """
        Draw a horizontal line connecting two columns in a row.
        
        Args:
            row: Row to draw in
            col_start: Starting column
            col_end: Ending column
            color: Optional color style
        """
        x_start = self._col_to_x(col_start)
        x_end = self._col_to_x(col_end)
        
        # Ensure start < end
        if x_start > x_end:
            x_start, x_end = x_end, x_start
        
        for x in range(x_start + 1, x_end):
            if self.grid[row][x].char == ' ':
                self.grid[row][x] = GridCell(char=self.chars.HORIZONTAL, color=color)
    
    def draw_connector(self, row: int, col: int, from_dirs: List[str], to_dirs: List[str],
                      color: Optional[str] = None):
        """
        Draw a connector character based on incoming and outgoing directions.
        
        Args:
            row: Row position
            col: Column position
            from_dirs: List of directions lines come from ('up', 'left', 'right')
            to_dirs: List of directions lines go to ('down', 'left', 'right')
            color: Optional color style
        """
        # Determine appropriate connector character
        has_up = 'up' in from_dirs
        has_down = 'down' in to_dirs
        has_left = 'left' in from_dirs or 'left' in to_dirs
        has_right = 'right' in from_dirs or 'right' in to_dirs
        
        # Simple vertical line
        if has_up and has_down and not has_left and not has_right:
            char = self.chars.VERTICAL
        # Corner cases
        elif has_up and has_right and not has_down and not has_left:
            char = self.chars.CORNER_RD
        elif has_up and has_left and not has_down and not has_right:
            char = self.chars.CORNER_LU
        elif has_down and has_right and not has_up and not has_left:
            char = self.chars.CORNER_RU
        elif has_down and has_left and not has_up and not has_right:
            char = self.chars.CORNER_LD
        # Splits and merges
        elif has_up and has_down and has_right:
            char = self.chars.SPLIT_RIGHT
        elif has_up and has_down and has_left:
            char = self.chars.SPLIT_LEFT
        elif has_left and has_right and has_down:
            char = self.chars.MERGE_DOWN
        elif has_left and has_right and has_up:
            char = self.chars.MERGE_UP
        # Cross
        elif has_up and has_down and has_left and has_right:
            char = self.chars.CROSS
        # Just horizontal
        elif has_left and has_right:
            char = self.chars.HORIZONTAL
        else:
            char = self.chars.VERTICAL  # Default
        
        self.set_char(row, col, char, color)
    
    def draw_merge(self, row: int, from_cols: List[int], to_col: int,
                  color: Optional[str] = None):
        """
        Draw a merge from multiple columns to a single column.
        
        Example:
            │ │      (row-1)
            ├─┘      (row)
            │        (row+1)
        
        Args:
            row: Row to draw merge at
            from_cols: Source columns
            to_col: Destination column
            color: Optional color style
        """
        if not from_cols:
            return
        
        from_cols = sorted(from_cols)
        
        # Simple 2-column merge
        if len(from_cols) == 2:
            left_col = min(from_cols)
            right_col = max(from_cols)
            
            if to_col == left_col:
                # Merging right into left
                self.set_char(row, left_col, self.chars.SPLIT_RIGHT, color)
                self.draw_horizontal_line(row, left_col, right_col, color)
                self.set_char(row, right_col, self.chars.CORNER_LU, color)
            elif to_col == right_col:
                # Merging left into right
                self.set_char(row, left_col, self.chars.CORNER_LD, color)
                self.draw_horizontal_line(row, left_col, right_col, color)
                self.set_char(row, right_col, self.chars.SPLIT_LEFT, color)
            else:
                # Merging to middle column
                self.set_char(row, to_col, self.chars.MERGE_UP, color)
                for col in from_cols:
                    if col != to_col:
                        self.draw_horizontal_line(row, min(col, to_col), max(col, to_col), color)
        else:
            # Complex merge (3+ columns)
            self.set_char(row, to_col, self.chars.MERGE_UP, color)
            for col in from_cols:
                if col != to_col:
                    self.draw_horizontal_line(row, min(col, to_col), max(col, to_col), color)
    
    def draw_split(self, row: int, from_col: int, to_cols: List[int],
                  color: Optional[str] = None):
        """
        Draw a split from a single column to multiple columns.
        
        Example:
            │        (row)
            ├─┐      (row+1)
            │ │      (row+2)
        
        Args:
            row: Row to draw split at
            from_col: Source column
            to_cols: Destination columns
            color: Optional color style
        """
        if not to_cols:
            return
        
        to_cols = sorted(to_cols)
        
        # Simple 2-column split
        if len(to_cols) == 2:
            left_col = min(to_cols)
            right_col = max(to_cols)
            
            if from_col == left_col:
                # Splitting left to right
                self.set_char(row, left_col, self.chars.SPLIT_RIGHT, color)
                self.draw_horizontal_line(row, left_col, right_col, color)
                self.set_char(row, right_col, self.chars.CORNER_RU, color)
            elif from_col == right_col:
                # Splitting right to left
                self.set_char(row, left_col, self.chars.CORNER_RD, color)
                self.draw_horizontal_line(row, left_col, right_col, color)
                self.set_char(row, right_col, self.chars.SPLIT_LEFT, color)
            else:
                # Splitting from middle
                self.set_char(row, from_col, self.chars.MERGE_DOWN, color)
                for col in to_cols:
                    if col != from_col:
                        self.draw_horizontal_line(row, min(col, from_col), max(col, from_col), color)
        else:
            # Complex split (3+ columns)
            self.set_char(row, from_col, self.chars.MERGE_DOWN, color)
            for col in to_cols:
                if col != from_col:
                    self.draw_horizontal_line(row, min(col, from_col), max(col, from_col), color)
    
    def to_rich_text(self):
        """
        Convert grid to Rich Text object with proper styling.
        
        Returns:
            Rich Text object with colored characters
        """
        from rich.text import Text
        
        result = Text()
        for row in self.grid:
            for cell in row:
                if cell.color:
                    result.append(cell.char, style=cell.color)
                else:
                    result.append(cell.char)
            result.append('\n')
        
        # Remove trailing newline
        if result.plain.endswith('\n'):
            result = Text(result.plain[:-1])
        
        return result
    
    def to_string(self) -> str:
        """Convert grid to plain string (no colors)."""
        lines = []
        for row in self.grid:
            line = ''.join(cell.char for cell in row)
            lines.append(line.rstrip())  # Remove trailing spaces
        return '\n'.join(lines)
