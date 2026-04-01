"""
solver.py - Optimized backtracking Sudoku solver with step logging.

Supports grid sizes: 4x4, 6x6, 9x9, 16x16
"""

from typing import List, Optional, Tuple, Dict, Any
import math


StepLog = Dict[str, Any]


def get_subgrid_dims(size: int) -> Tuple[int, int]:
    """
    Return (rows, cols) dimensions of each subgrid for a given board size.

    Args:
        size: Board size (4, 6, 9, or 16)

    Returns:
        Tuple of (subgrid_rows, subgrid_cols)

    Raises:
        ValueError: If size is not supported.
    """
    dims = {4: (2, 2), 6: (2, 3), 9: (3, 3), 16: (4, 4)}
    if size not in dims:
        raise ValueError(f"Unsupported board size: {size}. Supported sizes: 4, 6, 9, 16")
    return dims[size]


def build_candidates(board: List[List[int]], size: int) -> List[List[set]]:
    """
    Pre-compute candidate sets for every empty cell.

    Args:
        board: 2D list representing the current board state (0 = empty).
        size: Board size.

    Returns:
        2D list of sets; each set contains valid candidate digits for that cell.
    """
    sr, sc = get_subgrid_dims(size)
    candidates: List[List[set]] = [[set() for _ in range(size)] for _ in range(size)]

    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                used: set = set()
                # Row
                used.update(board[r])
                # Column
                used.update(board[i][c] for i in range(size))
                # Subgrid
                br, bc = (r // sr) * sr, (c // sc) * sc
                for dr in range(sr):
                    for dc in range(sc):
                        used.add(board[br + dr][bc + dc])
                used.discard(0)
                candidates[r][c] = set(range(1, size + 1)) - used

    return candidates


def find_mrv_cell(
    board: List[List[int]], candidates: List[List[set]], size: int
) -> Optional[Tuple[int, int]]:
    """
    Find the empty cell with the Minimum Remaining Values (MRV heuristic).

    Args:
        board: Current board state.
        candidates: Candidate sets for each cell.
        size: Board size.

    Returns:
        (row, col) of the cell with fewest candidates, or None if board is full.
    """
    min_opts = size + 1
    best: Optional[Tuple[int, int]] = None
    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                n = len(candidates[r][c])
                if n < min_opts:
                    min_opts = n
                    best = (r, c)
                    if n == 1:
                        return best  # Can't do better
    return best


def propagate(
    board: List[List[int]],
    candidates: List[List[set]],
    r: int,
    c: int,
    val: int,
    size: int,
) -> List[Tuple[int, int, int]]:
    """
    Place `val` at (r, c) and propagate constraints to peers, returning
    a list of (row, col, removed_value) tuples for undo purposes.

    Args:
        board: Mutable board state.
        candidates: Mutable candidate sets.
        r: Row index.
        c: Column index.
        val: Digit being placed.
        size: Board size.

    Returns:
        List of (row, col, removed_val) tuples representing removed candidates.
    """
    sr, sc = get_subgrid_dims(size)
    board[r][c] = val
    candidates[r][c] = set()
    removed: List[Tuple[int, int, int]] = []

    peers: set = set()
    # Row peers
    for cc in range(size):
        if cc != c:
            peers.add((r, cc))
    # Column peers
    for rr in range(size):
        if rr != r:
            peers.add((rr, c))
    # Subgrid peers
    br, bc = (r // sr) * sr, (c // sc) * sc
    for dr in range(sr):
        for dc in range(sc):
            pr, pc = br + dr, bc + dc
            if (pr, pc) != (r, c):
                peers.add((pr, pc))

    for pr, pc in peers:
        if board[pr][pc] == 0 and val in candidates[pr][pc]:
            candidates[pr][pc].discard(val)
            removed.append((pr, pc, val))

    return removed


def undo_propagate(
    board: List[List[int]],
    candidates: List[List[set]],
    r: int,
    c: int,
    val: int,
    removed: List[Tuple[int, int, int]],
) -> None:
    """
    Undo a placement at (r, c), restoring candidate sets.

    Args:
        board: Mutable board state.
        candidates: Mutable candidate sets.
        r: Row index.
        c: Column index.
        val: Digit being removed.
        removed: Previously removed candidates to restore.
    """
    board[r][c] = 0
    for pr, pc, pv in removed:
        candidates[pr][pc].add(pv)


def solve(
    board: List[List[int]],
    size: Optional[int] = None,
    max_steps: int = 100_000,
) -> Tuple[bool, List[StepLog]]:
    """
    Solve a Sudoku board in-place using backtracking + MRV + constraint propagation.

    Args:
        board: 2D list (0 = empty). Modified in-place on success.
        size: Board dimension. If None, inferred from board.
        max_steps: Safety cap on iterations to prevent infinite loops.

    Returns:
        (solved: bool, steps: List[StepLog])
        steps entries have keys: action, row, col, value, (optional) backtracks
    """
    if size is None:
        size = len(board)

    # Validate board dimensions
    for row in board:
        if len(row) != size:
            raise ValueError("Board rows have inconsistent lengths.")

    get_subgrid_dims(size)  # raises if unsupported

    candidates = build_candidates(board, size)
    steps: List[StepLog] = []
    backtracks = 0
    iterations = 0

    def backtrack() -> bool:
        nonlocal backtracks, iterations
        iterations += 1
        if iterations > max_steps:
            return False  # Safety exit

        cell = find_mrv_cell(board, candidates, size)
        if cell is None:
            return True  # All cells filled — solved!

        r, c = cell
        for val in sorted(candidates[r][c]):  # Sorted for determinism
            removed = propagate(board, candidates, r, c, val, size)

            steps.append({
                "action": "place",
                "row": r,
                "col": c,
                "value": val,
            })

            # Check if any peer now has zero candidates (contradiction)
            contradiction = any(
                board[pr][pc] == 0 and len(candidates[pr][pc]) == 0
                for pr, pc, _ in removed
            )

            if not contradiction and backtrack():
                return True

            # Undo
            undo_propagate(board, candidates, r, c, val, removed)
            backtracks += 1
            steps.append({
                "action": "backtrack",
                "row": r,
                "col": c,
                "value": val,
                "backtracks_total": backtracks,
            })

        return False

    solved = backtrack()
    return solved, steps
