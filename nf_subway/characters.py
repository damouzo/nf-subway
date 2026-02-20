class Characters:
    """Character sets for graph rendering (inspired by git-graph)"""

    @staticmethod
    def thin():
        return {
            'space': ' ',
            'dot': '●',           # Main commit/process node
            'circle': '○',        # Secondary node (merge point)
            'vertical': '│',      # Vertical line
            'horizontal': '─',    # Horizontal line
            'cross': '┼',         # Cross intersection
            'corner_rd': '└',     # Round down (bottom-left)
            'corner_ru': '┌',     # Round up (top-left)
            'corner_ld': '┐',     # Left down (top-right)
            'corner_lu': '┘',     # Left up (bottom-right)
            'split_right': '├',   # Split to right
            'split_left': '┤',    # Split to left
            'merge_down': '┬',    # Merge downward
            'merge_up': '┴',      # Merge upward
        }

    @staticmethod
    def round():
        chars = Characters.thin()
        chars.update({
            'corner_rd': '╰',
            'corner_ru': '╭',
            'corner_ld': '╮',
            'corner_lu': '╯',
        })
        return chars
