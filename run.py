"""
run.py - Convenience launcher for the Sudoku Solver backend.

Run with:
    python run.py

Or directly:
    uvicorn backend.main:app --reload --port 8000
"""

import subprocess
import sys
import os


def main() -> None:
    """Launch the FastAPI development server."""
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]
    print("Starting Sudoku Solver API on http://localhost:8000")
    print("Swagger docs:  http://localhost:8000/docs")
    print("Press Ctrl+C to stop.\n")
    subprocess.run(cmd, cwd=backend_dir, check=True)


if __name__ == "__main__":
    main()
