"""
Color scheme inspired by git-graph aesthetics.

Provides color definitions and styling for different process states.
"""

from enum import Enum
from typing import Dict


class ProcessStatus(Enum):
    """Process execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class GitGraphColors:
    """
    Color scheme inspired by git-graph.
    
    Uses Rich markup for terminal colors:
    - Pending: dim gray
    - Running: bright blue (with blink effect)
    - Completed: bright green
    - Failed: bright red
    - Cached: yellow
    
    For git-graph lines/branches, uses a fixed palette:
    - blue, yellow, magenta, green, cyan, red, bright_white, bright_cyan, bright_magenta, bright_yellow
    """
    
    # Status colors (Rich markup format)
    PENDING = "dim white"
    RUNNING = "bright_blue bold"
    COMPLETED = "bright_green"
    FAILED = "bright_red bold"
    CACHED = "yellow"
    
    # Graph elements
    LINE_VERTICAL = "bright_black"
    LINE_CONNECTOR = "bright_black"
    SEPARATOR = "bright_blue"

    # Fixed git-graph palette for branch/lane colors
    BRANCH_PALETTE = [
        "bright_blue",
        "bright_yellow",
        "bright_magenta",
        "bright_green",
        "bright_cyan",
        "bright_red",
        "bright_white",
        "cyan",
        "magenta",
        "yellow",
    ]
    
    @classmethod
    def branch_color(cls, lane: int) -> str:
        """Return color from palette for a given branch/lane index (cycled)."""
        return cls.BRANCH_PALETTE[lane % len(cls.BRANCH_PALETTE)]
    
    @classmethod
    def get_process_style(cls, status: ProcessStatus) -> str:
        """Get the Rich style string for a process status."""
        if status == ProcessStatus.PENDING:
            return cls.PENDING
        elif status == ProcessStatus.RUNNING:
            return cls.RUNNING
        elif status == ProcessStatus.COMPLETED:
            return cls.COMPLETED
        elif status == ProcessStatus.FAILED:
            return cls.FAILED
        elif status == ProcessStatus.CACHED:
            return cls.CACHED
        return "white"
    
    @classmethod
    def get_icon(cls, status: ProcessStatus) -> str:
        """Get a simple dot for a process status (no emojis, just colored dots)."""
        # Return empty string - we'll use the dots in the grid already
        return ""


class BlinkEffect:
    """
    Manages blinking animation for running processes.
    
    Alternates between bright and dim versions of the running color.
    """
    
    def __init__(self):
        self.frame = 0
        self.frames_per_blink = 3  # Number of frames before toggle
    
    def tick(self):
        """Advance the animation by one frame."""
        self.frame += 1
    
    def should_show_bright(self) -> bool:
        """Determine if current frame should show bright color."""
        cycle = (self.frame // self.frames_per_blink) % 2
        return cycle == 0
    
    def get_running_style(self) -> str:
        """Get the current running process style (blinking effect)."""
        if self.should_show_bright():
            return GitGraphColors.RUNNING
        else:
            return "blue dim"  # Dimmer version for blink effect
