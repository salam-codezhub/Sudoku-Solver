"""
utils.py - Miscellaneous utility helpers for the Sudoku Solver backend.
"""

import copy
from typing import List, Dict, Any


def deep_copy_board(board: List[List[int]]) -> List[List[int]]:
    """
    Return a deep copy of a 2D board array.

    Args:
        board: 2D list of integers.

    Returns:
        Independent deep copy.
    """
    return copy.deepcopy(board)


def board_to_string(board: List[List[int]]) -> str:
    """
    Convert a 2D board to a human-readable multi-line string with subgrid separators.

    Args:
        board: 2D list of integers.

    Returns:
        Formatted string representation.
    """
    size = len(board)
    from solver import get_subgrid_dims
    sr, sc = get_subgrid_dims(size)

    lines = []
    for r, row in enumerate(board):
        if r > 0 and r % sr == 0:
            lines.append("-" * (size * 3 + sc - 1))
        parts = []
        for c, val in enumerate(row):
            if c > 0 and c % sc == 0:
                parts.append("|")
            parts.append(f"{val:2d}" if val != 0 else " .")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def summarise_steps(steps: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Summarise solver step counts.

    Args:
        steps: List of step dictionaries from the solver.

    Returns:
        Dict with keys 'placements', 'backtracks', 'total'.
    """
    placements = sum(1 for s in steps if s.get("action") == "place")
    backtracks = sum(1 for s in steps if s.get("action") == "backtrack")
    return {"placements": placements, "backtracks": backtracks, "total": len(steps)}


def cache_key(board: List[List[int]]) -> str:
    """
    Generate a stable string cache key from a board.

    Args:
        board: 2D list of integers.

    Returns:
        String key suitable for use in a dictionary.
    """
    return "|".join(",".join(str(v) for v in row) for row in board)
