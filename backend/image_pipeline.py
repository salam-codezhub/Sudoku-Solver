"""
image_pipeline.py - OpenCV-based image processing pipeline for Sudoku grid extraction.

Pipeline stages:
    1. Load and preprocess image (grayscale, denoise, threshold)
    2. Detect the largest quadrilateral contour (the grid border)
    3. Apply perspective transform to produce a top-down view
    4. Split the warped grid into individual cells
    5. Run OCR (pytesseract) on each cell to extract digits
    6. Return a 2D board array
"""

import re
import math
import io
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import pytesseract


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def image_to_board(image_bytes: bytes) -> List[List[int]]:
    """
    Convert raw image bytes containing a Sudoku puzzle into a 2D board array.

    Args:
        image_bytes: Raw bytes of a JPEG or PNG image.

    Returns:
        2D list of integers (0 = empty cell).

    Raises:
        ValueError: If the grid cannot be detected or the OCR produces no digits.
    """
    img = _load_image(image_bytes)
    gray = _to_grayscale(img)
    thresh = _adaptive_threshold(gray)
    corners = _find_grid_corners(thresh)
    warped = _perspective_transform(gray, corners)
    size, cells = _split_into_cells(warped)
    board = _ocr_cells(cells, size)
    return board


# ---------------------------------------------------------------------------
# Stage 1 – Load
# ---------------------------------------------------------------------------

def _load_image(image_bytes: bytes) -> np.ndarray:
    """
    Decode image bytes into an OpenCV BGR array.

    Args:
        image_bytes: Raw image data.

    Returns:
        np.ndarray in BGR colour format.

    Raises:
        ValueError: If decoding fails.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image. Ensure the file is a valid JPEG or PNG.")
    return img


# ---------------------------------------------------------------------------
# Stage 2 – Grayscale
# ---------------------------------------------------------------------------

def _to_grayscale(img: np.ndarray) -> np.ndarray:
    """
    Convert a BGR image to grayscale and apply Gaussian blur.

    Args:
        img: BGR OpenCV image.

    Returns:
        Grayscale image with slight blur applied.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 0)
    return gray


# ---------------------------------------------------------------------------
# Stage 3 – Threshold
# ---------------------------------------------------------------------------

def _adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """
    Apply adaptive binary thresholding to highlight grid lines.

    Args:
        gray: Grayscale image.

    Returns:
        Binary (thresholded) image.
    """
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=11,
        C=2,
    )
    # Dilate slightly to close gaps in grid lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.dilate(thresh, kernel, iterations=1)
    return thresh


# ---------------------------------------------------------------------------
# Stage 4 – Grid corner detection
# ---------------------------------------------------------------------------

def _find_grid_corners(thresh: np.ndarray) -> np.ndarray:
    """
    Find the four corners of the Sudoku grid using contour detection.

    Selects the largest quadrilateral contour in the thresholded image.

    Args:
        thresh: Binary thresholded image.

    Returns:
        4×2 numpy array of corner coordinates (float32), ordered:
        [top-left, top-right, bottom-right, bottom-left].

    Raises:
        ValueError: If no suitable quadrilateral is found.
    """
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No contours found in image. Ensure the Sudoku grid is clearly visible.")

    # Sort contours by area descending; the grid should be the largest object
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours[:5]:  # Check top-5 largest
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            return _order_corners(approx.reshape(4, 2).astype(np.float32))

    raise ValueError(
        "Could not detect a rectangular Sudoku grid. "
        "Try a clearer photo with better lighting and less tilt."
    )


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """
    Re-order four corner points to [top-left, top-right, bottom-right, bottom-left].

    Args:
        pts: 4×2 array of (x, y) corner coordinates.

    Returns:
        Re-ordered 4×2 array.
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]   # bottom-right: largest sum
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]   # top-right: smallest diff
    rect[3] = pts[np.argmax(diff)]   # bottom-left: largest diff
    return rect


# ---------------------------------------------------------------------------
# Stage 5 – Perspective transform
# ---------------------------------------------------------------------------

def _perspective_transform(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """
    Warp the grid region to a square top-down view.

    Args:
        gray: Original grayscale image.
        corners: 4×2 ordered corner array.

    Returns:
        Warped grayscale image (square, 450×450 or similar).
    """
    tl, tr, br, bl = corners

    # Compute output side length from the detected corner distances
    width_top = np.linalg.norm(tr - tl)
    width_bot = np.linalg.norm(br - bl)
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)
    side = int(max(width_top, width_bot, height_left, height_right))
    side = max(side, 252)  # Minimum size to ensure cells are readable

    dst = np.array(
        [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(gray, M, (side, side))
    return warped


# ---------------------------------------------------------------------------
# Stage 6 – Cell extraction
# ---------------------------------------------------------------------------

def _split_into_cells(warped: np.ndarray) -> Tuple[int, List[np.ndarray]]:
    """
    Divide the warped grid image into individual cell images.

    Attempts to detect grid size as 4, 6, 9, or 16 by finding the size
    that produces cells of the most uniform size. Defaults to 9×9.

    Args:
        warped: Square grayscale top-down grid image.

    Returns:
        (size, cells) where size is the grid dimension and cells is a
        flattened list of cell images in row-major order.
    """
    h, w = warped.shape
    # Try to auto-detect grid size
    size = _detect_grid_size(warped)
    cell_h = h // size
    cell_w = w // size

    cells: List[np.ndarray] = []
    margin = max(2, min(cell_h, cell_w) // 8)  # Trim grid lines from edges

    for r in range(size):
        for c in range(size):
            y0 = r * cell_h + margin
            y1 = (r + 1) * cell_h - margin
            x0 = c * cell_w + margin
            x1 = (c + 1) * cell_w - margin
            cell = warped[y0:y1, x0:x1]
            cells.append(cell)

    return size, cells


def _detect_grid_size(warped: np.ndarray) -> int:
    """
    Attempt to detect whether the grid is 4×4, 6×6, 9×9, or 16×16
    by counting internal lines via Hough line detection.

    Falls back to 9 if detection is ambiguous.

    Args:
        warped: Warped grid image.

    Returns:
        Detected grid size (4, 6, 9, or 16).
    """
    edges = cv2.Canny(warped, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=int(warped.shape[0] * 0.4))

    if lines is None:
        return 9

    # Count distinct horizontal and vertical lines
    h_lines: List[float] = []
    v_lines: List[float] = []
    for line in lines:
        rho, theta = line[0]
        if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:
            v_lines.append(rho)
        elif abs(theta - np.pi / 2) < 0.1:
            h_lines.append(rho)

    def count_unique(positions: List[float], gap: int) -> int:
        if not positions:
            return 0
        positions = sorted(positions)
        count = 1
        for i in range(1, len(positions)):
            if positions[i] - positions[i - 1] > gap:
                count += 1
        return count

    gap = warped.shape[0] // 20
    h_count = count_unique(h_lines, gap)
    v_count = count_unique(v_lines, gap)
    internal = max(h_count, v_count)

    # Internal lines = size - 1 (borders + inner grid lines)
    # Map detected line count to grid size
    if 3 <= internal <= 5:
        return 4
    elif 5 < internal <= 7:
        return 6
    elif 8 <= internal <= 11:
        return 9
    elif internal >= 15:
        return 16
    return 9


# ---------------------------------------------------------------------------
# Stage 7 – OCR
# ---------------------------------------------------------------------------

def _ocr_cells(cells: List[np.ndarray], size: int) -> List[List[int]]:
    """
    Run Tesseract OCR on each cell image and assemble the board.

    Args:
        cells: Flattened list of cell images (row-major order).
        size: Grid dimension (number of cells per row/column).

    Returns:
        2D list of integers (0 = empty / unrecognised cell).

    Raises:
        ValueError: If all cells are empty (complete OCR failure).
    """
    board: List[List[int]] = [[0] * size for _ in range(size)]
    recognised = 0

    # Tesseract config: single character, digits only
    if size <= 9:
        tess_config = "--psm 10 -c tessedit_char_whitelist=0123456789"
    else:
        # 16×16 uses hex digits A–F or 1–16; we support digit-only variant
        tess_config = "--psm 10 -c tessedit_char_whitelist=0123456789ABCDEF"

    for idx, cell_img in enumerate(cells):
        r, c = divmod(idx, size)
        digit = _extract_digit_from_cell(cell_img, tess_config, size)
        if digit is not None:
            board[r][c] = digit
            recognised += 1

    if recognised == 0:
        raise ValueError(
            "OCR could not extract any digits from the image. "
            "Ensure the image is clear, well-lit, and the grid is fully visible."
        )

    return board


def _extract_digit_from_cell(
    cell: np.ndarray, config: str, size: int
) -> Optional[int]:
    """
    Extract a single digit from a cell image using pytesseract.

    Preprocessing steps applied to improve OCR accuracy:
        - Resize to 64×64
        - Binary threshold (Otsu)
        - Invert if background is dark
        - Add white padding

    Args:
        cell: Grayscale cell image.
        config: Tesseract configuration string.
        size: Grid size (used to validate the digit range).

    Returns:
        Extracted integer digit, or None if the cell appears empty.
    """
    if cell.size == 0:
        return None

    # Resize for OCR
    cell_resized = cv2.resize(cell, (64, 64), interpolation=cv2.INTER_CUBIC)

    # Otsu threshold
    _, thresh = cv2.threshold(cell_resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Ensure digits are dark on white background
    if np.mean(thresh) < 128:
        thresh = cv2.bitwise_not(thresh)

    # Add padding so Tesseract doesn't clip edge digits
    padded = cv2.copyMakeBorder(thresh, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

    # Check if cell is mostly empty (background) — skip OCR
    filled_ratio = np.sum(padded < 128) / padded.size
    if filled_ratio < 0.02:
        return None

    pil_img = Image.fromarray(padded)
    raw = pytesseract.image_to_string(pil_img, config=config).strip()

    # Parse result
    raw_clean = re.sub(r"[^0-9A-Fa-f]", "", raw)
    if not raw_clean:
        return None

    try:
        # For sizes ≤ 9 use decimal; for 16 allow hex
        if size <= 9:
            val = int(raw_clean[0])
        else:
            val = int(raw_clean[0], 16) if raw_clean[0].upper() in "ABCDEF" else int(raw_clean[0])
    except (ValueError, IndexError):
        return None

    if val < 1 or val > size:
        return None

    return val
