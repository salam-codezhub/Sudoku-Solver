"""
validator.py - Sudoku board validation utilities.

Checks row, column, and subgrid constraints for any supported board size.
"""

from typing import List, Tuple
from solver import get_subgrid_dims


def validate_board(board: List[List[int]]) -> Tuple[bool, str]:
    """
    Validate a Sudoku board for structural and constraint correctness.

    Checks:
        - Board is a non-empty square grid.
        - Size is supported (4, 6, 9, or 16).
        - All values are integers in [0, size].
        - No duplicate non-zero values in any row.
        - No duplicate non-zero values in any column.
        - No duplicate non-zero values in any subgrid.

    Args:
        board: 2D list of integers (0 = empty cell).

    Returns:
        (is_valid: bool, message: str)
    """
    if not board or not isinstance(board, list):
        return False, "Board is empty or not a list."

    size = len(board)
    supported = {4, 6, 9, 16}
    if size not in supported:
        return False, f"Unsupported board size: {size}. Must be one of {sorted(supported)}."

    # Check all rows have correct length
    for i, row in enumerate(board):
        if not isinstance(row, list) or len(row) != size:
            return False, f"Row {i} has incorrect length {len(row) if isinstance(row, list) else 'N/A'} (expected {size})."

    # Check all values are valid integers
    for r in range(size):
        for c in range(size):
            v = board[r][c]
            if not isinstance(v, int) or v < 0 or v > size:
                return False, f"Invalid value '{v}' at ({r}, {c}). Values must be integers in [0, {size}]."

    # Check row duplicates
    for r in range(size):
        seen: set = set()
        for c in range(size):
            v = board[r][c]
            if v != 0:
                if v in seen:
                    return False, f"Duplicate value {v} found in row {r}."
                seen.add(v)

    # Check column duplicates
    for c in range(size):
        seen = set()
        for r in range(size):
            v = board[r][c]
            if v != 0:
                if v in seen:
                    return False, f"Duplicate value {v} found in column {c}."
                seen.add(v)

    # Check subgrid duplicates
    sr, sc = get_subgrid_dims(size)
    for br in range(0, size, sr):
        for bc in range(0, size, sc):
            seen = set()
            for dr in range(sr):
                for dc in range(sc):
                    v = board[br + dr][bc + dc]
                    if v != 0:
                        if v in seen:
                            return False, (
                                f"Duplicate value {v} found in subgrid "
                                f"starting at ({br}, {bc})."
                            )
                        seen.add(v)

    return True, "Board is valid."


def is_completely_filled(board: List[List[int]]) -> bool:
    """
    Check if every cell in the board has a non-zero value.

    Args:
        board: 2D list of integers.

    Returns:
        True if no empty cells remain.
    """
    return all(cell != 0 for row in board for cell in row)


def count_filled_cells(board: List[List[int]]) -> int:
    """
    Count the number of non-zero (filled) cells.

    Args:
        board: 2D list of integers.

    Returns:
        Count of filled cells.
    """
    return sum(1 for row in board for cell in row if cell != 0)
