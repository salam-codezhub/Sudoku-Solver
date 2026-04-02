# 🧩 AI-Based Sudoku Solver

A full-stack application that solves Sudoku puzzles from image uploads or manual input — powered by **FastAPI**, **OpenCV**, **Pytesseract**, and a **backtracking + constraint-propagation solver**.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Grid sizes** | 4×4, 6×6, 9×9, 16×16 |
| **Image input** | JPEG / PNG; full OpenCV pipeline (threshold → contour → perspective warp → OCR) |
| **Manual input** | Editable grid with keyboard navigation |
| **Solver** | Backtracking + MRV heuristic + constraint propagation (arc consistency) |
| **Difficulty** | Estimated from filled-cell ratio and backtrack count |
| **Step logging** | Every placement and backtrack returned in the API response |
| **Caching** | `functools.lru_cache` on the backend for repeated puzzle solves |
| **Validation** | Row / column / subgrid duplicate checks before solving |

---

## 📁 Project Structure

```
sudoku_solver/
├── backend/
│   ├── main.py            # FastAPI app, endpoints, caching
│   ├── solver.py          # Backtracking solver + MRV + constraint propagation
│   ├── validator.py       # Board validation (rows, cols, subgrids)
│   ├── difficulty.py      # Difficulty estimation
│   ├── image_pipeline.py  # OpenCV + Tesseract OCR pipeline
│   ├── models.py          # Pydantic request/response models
│   └── utils.py           # Cache key, board printer, step summariser
├── frontend/
│   ├── index.html         # Single-page UI
│   ├── style.css          # Editorial-themed styles
│   └── script.js          # Grid rendering, API calls, result display
├── run.py                 # Convenience launcher
└── README.md
```

---

## ⚙️ Installation

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.9+ |
| Tesseract OCR | 4.x or 5.x |

#### Install Tesseract

**macOS (Homebrew):**
```bash
brew install tesseract
```

**Ubuntu / Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**  
Download the installer from https://github.com/UB-Mannheim/tesseract/wiki and add it to `PATH`.

### Python dependencies

```bash
cd sudoku_solver
pip install fastapi uvicorn opencv-python-headless numpy pytesseract Pillow pydantic
```

Or create a virtual environment first:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install fastapi uvicorn opencv-python-headless numpy pytesseract Pillow pydantic
```

---

## 🚀 How to Run

### 1. Start the backend

```bash
# From the sudoku_solver/ root directory:
python run.py

# Or directly:
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 2. Open the frontend

Simply open `frontend/index.html` in your browser:

```bash
open frontend/index.html          # macOS
xdg-open frontend/index.html      # Linux
start frontend/index.html         # Windows
```

> The frontend makes API calls to `http://localhost:8000` by default.  
> To change this, edit `API_BASE` at the top of `frontend/script.js`.

---

## 📖 API Documentation

### `GET /health`

Returns service status.

**Response:**
```json
{ "status": "ok", "service": "sudoku-solver" }
```

---

### `POST /solve/manual`

Solve a puzzle provided as a JSON board.

**Request body:**
```json
{
  "board": [
    [5,3,0,0,7,0,0,0,0],
    [6,0,0,1,9,5,0,0,0],
    [0,9,8,0,0,0,0,6,0],
    [8,0,0,0,6,0,0,0,3],
    [4,0,0,8,0,3,0,0,1],
    [7,0,0,0,2,0,0,0,6],
    [0,6,0,0,0,0,2,8,0],
    [0,0,0,4,1,9,0,0,5],
    [0,0,0,0,8,0,0,7,9]
  ]
}
```

**Success response (200):**
```json
{
  "status": "success",
  "solution": [[5,3,4,6,7,8,9,1,2], ...],
  "steps": [
    {"action": "place",    "row": 0, "col": 2, "value": 4},
    {"action": "backtrack","row": 0, "col": 2, "value": 4, "backtracks_total": 1}
  ],
  "difficulty": "Medium",
  "difficulty_description": "Requires some logical deduction beyond direct elimination.",
  "total_steps": 84,
  "backtrack_count": 0
}
```

**Error responses:**
| Code | Reason |
|---|---|
| 400 | Board failed validation (duplicates, wrong size, bad values) |
| 422 | No solution exists |
| 500 | Internal server error |

---

### `POST /solve/image`

Solve a puzzle from an image upload.

**Request:** `multipart/form-data` with a `file` field (JPEG or PNG).

**Response:** Same format as `/solve/manual`.

**Error responses:**
| Code | Reason |
|---|---|
| 400 | OCR failure, grid not detected, empty file |
| 415 | Unsupported file type |
| 422 | No solution found |
| 500 | Internal server error |

---

## 🖼️ Image Processing Pipeline

1. **Load** — Decode JPEG/PNG bytes with OpenCV.
2. **Grayscale + Blur** — Gaussian blur to reduce noise.
3. **Adaptive Threshold** — `cv2.ADAPTIVE_THRESH_GAUSSIAN_C` to binarise the image; dilation closes grid-line gaps.
4. **Contour Detection** — Find the largest quadrilateral in the thresholded image.
5. **Perspective Transform** — Warp the detected quad to a flat top-down square.
6. **Cell Splitting** — Divide the warped image into N² equal cells with a margin to remove grid lines.
7. **Grid Size Detection** — Hough line counting to distinguish 4×4 / 6×6 / 9×9 / 16×16.
8. **OCR** — Each cell is resized, thresholded, and fed to Pytesseract with `--psm 10` (single character mode).

---

## 🔢 Solver Algorithm

The solver in `solver.py` uses three techniques:

1. **Backtracking** — Try each valid digit; undo on contradiction.
2. **MRV (Minimum Remaining Values)** — Always pick the empty cell with the fewest candidates first, dramatically reducing the search tree.
3. **Constraint Propagation** — When placing a digit, remove it from all peers' candidate sets immediately; undo on backtrack. Detect contradictions early (a peer cell with zero candidates).

This combination typically solves 9×9 puzzles in microseconds and hard 16×16 puzzles in well under a second.

---

## 🎯 Difficulty Estimation

| Level  | 9×9 filled-cell ratio |
|--------|----------------------|
| Easy   | ≥ 60 % |
| Medium | 45 – 60 % |
| Hard   | 30 – 45 % |
| Expert | < 30 % |

Difficulty is also upgraded if the solver needed more than 500 (→ Hard) or 2 000 (→ Expert) backtracks.

---

## ⚠️ Known Limitations

- **Image OCR accuracy** depends heavily on image quality. Poor lighting, skewed photos, or printed grids with decorative fonts may produce incorrect digit reads. Post-processing validation will catch most invalid boards.
- **16×16 image OCR** is challenging; manual input is more reliable for this size.
- The frontend uses a static `localhost:8000` API URL — update `API_BASE` in `script.js` for deployment.
- No authentication or rate limiting is implemented (intended for local use).

---

## 🔮 Future Improvements

- [ ] Serve the frontend from FastAPI (static files) to avoid CORS issues.
- [ ] Add a "Hint" mode that reveals one cell at a time.
- [ ] Human-strategy solver (naked singles, hidden singles, X-wing) alongside backtracking.
- [ ] WebSocket endpoint for streaming step-by-step solving animations.
- [ ] Docker Compose setup for one-command deployment.
- [ ] Puzzle generator with guaranteed unique solutions.
- [ ] Mobile-optimised touch input.
