"""
models.py - Pydantic request/response models for the Sudoku Solver API.
"""

from typing import List, Any, Optional
from pydantic import BaseModel, Field, field_validator


class ManualSolveRequest(BaseModel):
    """Request body for POST /solve/manual."""

    board: List[List[int]] = Field(
        ...,
        description="2D array representing the Sudoku board. Use 0 for empty cells.",
        example=[
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ],
    )

    @field_validator("board")
    @classmethod
    def board_must_be_square(cls, v: List[List[int]]) -> List[List[int]]:
        """Ensure the board is a non-empty square grid."""
        if not v:
            raise ValueError("Board cannot be empty.")
        size = len(v)
        for i, row in enumerate(v):
            if len(row) != size:
                raise ValueError(
                    f"Row {i} has {len(row)} elements but expected {size} (board must be square)."
                )
        return v


class SolveStep(BaseModel):
    """A single step in the solving process."""

    action: str = Field(..., description="'place' or 'backtrack'")
    row: int = Field(..., description="Zero-indexed row")
    col: int = Field(..., description="Zero-indexed column")
    value: int = Field(..., description="Digit placed or removed")
    backtracks_total: Optional[int] = Field(
        None, description="Cumulative backtrack count (only present on backtrack steps)"
    )


class SolveResponse(BaseModel):
    """Unified response body for both solve endpoints."""

    status: str = Field(..., description="'success' or 'error'")
    solution: Optional[List[List[int]]] = Field(
        None, description="Solved board (null if no solution exists)"
    )
    steps: List[Any] = Field(
        default_factory=list,
        description="Step-by-step log of the solving process",
    )
    difficulty: Optional[str] = Field(
        None, description="Estimated difficulty: Easy, Medium, Hard, or Expert"
    )
    difficulty_description: Optional[str] = Field(
        None, description="Human-friendly explanation of the difficulty"
    )
    total_steps: int = Field(0, description="Total number of solver steps taken")
    backtrack_count: int = Field(0, description="Number of backtracking steps")
    message: Optional[str] = Field(None, description="Error or informational message")
