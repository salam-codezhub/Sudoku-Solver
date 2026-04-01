"""
difficulty.py - Estimate Sudoku puzzle difficulty based on filled-cell ratio
and backtrack count from the solver.
"""

from typing import List


# Difficulty thresholds per grid size.
# Each entry: (min_filled_ratio, max_filled_ratio) -> label
# Ratios represent the proportion of filled cells in the INITIAL puzzle.
_DIFFICULTY_THRESHOLDS = {
    4:  [(0.75, 1.01, "Easy"), (0.50, 0.75, "Medium"), (0.25, 0.50, "Hard"), (0.0, 0.25, "Expert")],
    6:  [(0.70, 1.01, "Easy"), (0.50, 0.70, "Medium"), (0.30, 0.50, "Hard"), (0.0, 0.30, "Expert")],
    9:  [(0.60, 1.01, "Easy"), (0.45, 0.60, "Medium"), (0.30, 0.45, "Hard"), (0.0, 0.30, "Expert")],
    16: [(0.55, 1.01, "Easy"), (0.40, 0.55, "Medium"), (0.25, 0.40, "Hard"), (0.0, 0.25, "Expert")],
}


def estimate_difficulty(board: List[List[int]], backtrack_count: int = 0) -> str:
    """
    Estimate the difficulty of a Sudoku puzzle.

    Primary signal: ratio of filled cells to total cells in the initial board.
    Secondary signal: number of backtracks needed during solving (upgrades difficulty
    when solver had to backtrack heavily even on a seemingly filled board).

    Args:
        board: The INITIAL (unsolved) board as a 2D list (0 = empty).
        backtrack_count: Number of backtracks the solver performed.

    Returns:
        Difficulty label: "Easy", "Medium", "Hard", or "Expert".
    """
    size = len(board)
    total_cells = size * size
    filled = sum(1 for row in board for cell in row if cell != 0)
    ratio = filled / total_cells

    thresholds = _DIFFICULTY_THRESHOLDS.get(size, _DIFFICULTY_THRESHOLDS[9])

    label = "Expert"
    for low, high, name in thresholds:
        if low <= ratio < high:
            label = name
            break

    # Upgrade difficulty if solver required extensive backtracking
    if backtrack_count > 500 and label in ("Easy", "Medium"):
        label = "Hard"
    elif backtrack_count > 2000 and label != "Expert":
        label = "Expert"

    return label


def difficulty_description(label: str) -> str:
    """
    Return a human-friendly description for a difficulty label.

    Args:
        label: One of "Easy", "Medium", "Hard", "Expert".

    Returns:
        Descriptive string.
    """
    descriptions = {
        "Easy":   "Plenty of given digits — straightforward for beginners.",
        "Medium": "Requires some logical deduction beyond direct elimination.",
        "Hard":   "Few givens; demands chaining strategies and careful analysis.",
        "Expert": "Minimal clues — may require advanced techniques or heavy backtracking.",
    }
    return descriptions.get(label, "Unknown difficulty.")
