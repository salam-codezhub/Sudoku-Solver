"""
main.py - FastAPI application entry point.

Endpoints:
    POST /solve/image   - Accept image upload, run OCR + solver
    POST /solve/manual  - Accept JSON board, run solver directly
    GET  /health        - Health check
"""

import copy
import functools
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import ManualSolveRequest, SolveResponse
from solver import solve
from validator import validate_board
from difficulty import estimate_difficulty, difficulty_description
from image_pipeline import image_to_board
from utils import deep_copy_board, summarise_steps, cache_key

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Sudoku Solver API",
    description=(
        "Solve Sudoku puzzles (4×4, 6×6, 9×9, 16×16) via image upload "
        "or manual JSON input. Returns the solution, step-by-step log, "
        "and difficulty estimate."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory LRU cache (size 128)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=128)
def _cached_solve(key: str, board_tuple: tuple) -> Dict[str, Any]:
    """
    Internal cached solver wrapper.

    Args:
        key: Unique cache key string (unused in body, used by lru_cache).
        board_tuple: Immutable tuple-of-tuples representation of the board.

    Returns:
        Dict with solution, steps, difficulty info.
    """
    board = [list(row) for row in board_tuple]
    initial_board = copy.deepcopy(board)
    solved, steps = solve(board)
    summary = summarise_steps(steps)
    diff_label = estimate_difficulty(initial_board, summary["backtracks"])
    diff_desc = difficulty_description(diff_label)
    return {
        "solved": solved,
        "solution": board if solved else None,
        "steps": steps,
        "summary": summary,
        "difficulty": diff_label,
        "difficulty_description": diff_desc,
    }


def _run_solve(board: list) -> SolveResponse:
    """
    Validate, solve, and package the result for a given board.

    Args:
        board: 2D list of integers.

    Returns:
        SolveResponse instance.

    Raises:
        HTTPException 400: On validation failure.
        HTTPException 422: On unsolvable puzzle.
    """
    is_valid, msg = validate_board(board)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    ck = cache_key(board)
    board_tuple = tuple(tuple(row) for row in board)
    result = _cached_solve(ck, board_tuple)

    if not result["solved"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No solution exists for the provided Sudoku puzzle.",
        )

    summary = result["summary"]
    return SolveResponse(
        status="success",
        solution=result["solution"],
        steps=result["steps"],
        difficulty=result["difficulty"],
        difficulty_description=result["difficulty_description"],
        total_steps=summary["total"],
        backtrack_count=summary["backtracks"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
async def health_check() -> Dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok", "service": "sudoku-solver"}


@app.post("/solve/manual", response_model=SolveResponse, tags=["Solve"])
async def solve_manual(request: ManualSolveRequest) -> SolveResponse:
    """
    Solve a Sudoku puzzle provided as a JSON board.

    The board must be a square 2D array with size 4, 6, 9, or 16.
    Empty cells should be represented as 0.

    Args:
        request: JSON body containing the board.

    Returns:
        SolveResponse with solution, steps, and difficulty.
    """
    return _run_solve(request.board)


@app.post("/solve/image", response_model=SolveResponse, tags=["Solve"])
async def solve_image(file: UploadFile = File(...)) -> SolveResponse:
    """
    Solve a Sudoku puzzle from an uploaded image.

    The image must clearly show the entire Sudoku grid.
    Supports JPEG and PNG formats.

    Args:
        file: Uploaded image file.

    Returns:
        SolveResponse with extracted board, solution, steps, and difficulty.
    """
    # Validate MIME type
    allowed = {"image/jpeg", "image/jpg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Upload a JPEG or PNG.",
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        board = image_to_board(image_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image processing failed: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during image processing: {exc}",
        ) from exc

    return _run_solve(board)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server errors."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {type(exc).__name__}: {exc}",
        },
    )
