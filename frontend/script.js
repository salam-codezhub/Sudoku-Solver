/**
 * script.js — Sudoku Solver Frontend
 * Handles: grid rendering, input validation, API calls, result display.
 */

"use strict";

// ── Config ──────────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";

/** Subgrid dimensions for each supported size. */
const SUBGRID = { 4: [2,2], 6: [2,3], 9: [3,3], 16: [4,4] };

/** Example puzzles for each size (0 = empty). */
const EXAMPLES = {
  4: [
    [0,0,3,0],
    [3,0,0,4],
    [1,0,0,2],
    [0,4,1,0],
  ],
  6: [
    [0,0,0,6,0,0],
    [0,6,0,0,2,0],
    [5,0,0,0,0,3],
    [3,0,0,0,0,5],
    [0,4,0,0,6,0],
    [0,0,6,0,0,0],
  ],
  9: [
    [5,3,0,0,7,0,0,0,0],
    [6,0,0,1,9,5,0,0,0],
    [0,9,8,0,0,0,0,6,0],
    [8,0,0,0,6,0,0,0,3],
    [4,0,0,8,0,3,0,0,1],
    [7,0,0,0,2,0,0,0,6],
    [0,6,0,0,0,0,2,8,0],
    [0,0,0,4,1,9,0,0,5],
    [0,0,0,0,8,0,0,7,9],
  ],
  16: Array.from({length:16}, (_,r) =>
    Array.from({length:16}, (_,c) => {
      // Sparse 16×16 example (valid givens only)
      const given = {
        "0,0":1,  "0,4":5,  "0,8":9,  "0,12":13,
        "1,1":6,  "1,5":10, "1,9":14, "1,13":2,
        "2,2":11, "2,6":15, "2,10":3, "2,14":7,
        "3,3":16, "3,7":4,  "3,11":8, "3,15":12,
        "4,4":2,  "4,8":6,  "4,12":10,"4,0":14,
        "5,5":7,  "5,9":11, "5,13":15,"5,1":3,
        "6,6":12, "6,10":16,"6,14":4, "6,2":8,
        "7,7":1,  "7,11":5, "7,15":9, "7,3":13,
      };
      return given[`${r},${c}`] || 0;
    })
  ),
};

// ── State ───────────────────────────────────────────────────────────────────

let currentSize = 9;
let uploadedFile = null;

// ── DOM refs ─────────────────────────────────────────────────────────────────

const inputGrid       = document.getElementById("input-grid");
const solutionGrid    = document.getElementById("solution-grid");
const tabBtns         = document.querySelectorAll(".tab-btn");
const tabContents     = document.querySelectorAll(".tab-content");
const pills           = document.querySelectorAll(".pill");
const btnClear        = document.getElementById("btn-clear");
const btnExample      = document.getElementById("btn-example");
const btnSolveManual  = document.getElementById("btn-solve-manual");
const btnSolveImage   = document.getElementById("btn-solve-image");
const btnRemoveImage  = document.getElementById("btn-remove-image");
const fileInput       = document.getElementById("file-input");
const dropZone        = document.getElementById("drop-zone");
const imagePreviewWrap= document.getElementById("image-preview-wrap");
const imagePreview    = document.getElementById("image-preview");
const resultEmpty     = document.getElementById("result-empty");
const resultContent   = document.getElementById("result-content");
const resultError     = document.getElementById("result-error");
const difficultyBadge = document.getElementById("difficulty-badge");
const metaSteps       = document.getElementById("meta-steps");
const metaBt          = document.getElementById("meta-bt");
const stepsList       = document.getElementById("steps-list");
const stepsCount      = document.getElementById("steps-count");
const errorMsg        = document.getElementById("error-msg");

// ── Grid builder ─────────────────────────────────────────────────────────────

/**
 * Render an editable input grid.
 * @param {HTMLElement} container
 * @param {number} size
 * @param {number[][]|null} prefill  Optional board values to pre-fill.
 */
function buildInputGrid(container, size, prefill = null) {
  container.innerHTML = "";
  container.dataset.size = size;
  container.style.gridTemplateColumns = `repeat(${size}, var(--cell-size, 44px))`;

  const [sr, sc] = SUBGRID[size] || [3,3];

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const input = document.createElement("input");
      input.type = "text";
      input.maxLength = size > 9 ? 2 : 1;
      input.className = "cell";
      input.setAttribute("aria-label", `Row ${r+1}, Column ${c+1}`);
      input.dataset.row = r;
      input.dataset.col = c;

      if (prefill && prefill[r][c] !== 0) {
        input.value = prefill[r][c];
      }

      // Subgrid border classes
      if ((c + 1) % sc === 0 && c < size - 1) input.classList.add("border-right");
      if ((r + 1) % sr === 0 && r < size - 1) input.classList.add("border-bottom");

      // Input validation & keyboard navigation
      input.addEventListener("input", onCellInput);
      input.addEventListener("keydown", onCellKeydown);

      container.appendChild(input);
    }
  }
}

/**
 * Render a read-only solution grid.
 * @param {HTMLElement} container
 * @param {number[][]} solution
 * @param {number[][]} original  Original board (to distinguish given vs solved).
 */
function buildSolutionGrid(container, solution, original) {
  const size = solution.length;
  container.innerHTML = "";
  container.dataset.size = size;
  container.style.gridTemplateColumns = `repeat(${size}, var(--cell-size, 44px))`;

  const [sr, sc] = SUBGRID[size] || [3,3];

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const div = document.createElement("div");
      div.className = "cell";
      div.textContent = solution[r][c] || "";

      const wasGiven = original[r][c] !== 0;
      div.classList.add(wasGiven ? "given" : "solved-val");

      // Stagger animation delay for solved cells
      if (!wasGiven) {
        div.style.animationDelay = `${(r * size + c) * 15}ms`;
      }

      if ((c + 1) % sc === 0 && c < size - 1) div.classList.add("border-right");
      if ((r + 1) % sr === 0 && r < size - 1) div.classList.add("border-bottom");

      container.appendChild(div);
    }
  }
}

// ── Cell input handlers ──────────────────────────────────────────────────────

function onCellInput(e) {
  const input = e.target;
  const size = currentSize;
  let raw = input.value.trim();

  // Strip non-digit characters
  if (size <= 9) {
    raw = raw.replace(/\D/g, "");
  } else {
    raw = raw.replace(/[^0-9A-Fa-f]/g, "").toUpperCase();
  }

  // Keep only first character
  if (raw.length > 1) raw = raw[raw.length - 1];

  input.value = raw;

  // Validate range
  const num = size <= 9 ? parseInt(raw, 10) : parseInt(raw, 16);
  if (raw === "" || raw === "0") {
    input.value = "";
    input.classList.remove("invalid");
  } else if (!isNaN(num) && num >= 1 && num <= size) {
    input.classList.remove("invalid");
  } else {
    input.classList.add("invalid");
  }

  // Auto-advance focus
  if (raw !== "" && !input.classList.contains("invalid")) {
    const cells = inputGrid.querySelectorAll("input.cell");
    const idx = Array.from(cells).indexOf(input);
    if (idx < cells.length - 1) cells[idx + 1].focus();
  }
}

function onCellKeydown(e) {
  const cells = Array.from(inputGrid.querySelectorAll("input.cell"));
  const idx   = cells.indexOf(e.target);
  const size  = currentSize;

  const move = {
    ArrowRight: 1, ArrowLeft: -1,
    ArrowDown: size, ArrowUp: -size,
  }[e.key];

  if (move !== undefined) {
    e.preventDefault();
    const target = cells[idx + move];
    if (target) target.focus();
  }

  if (e.key === "Backspace" && e.target.value === "") {
    const prev = cells[idx - 1];
    if (prev) { prev.focus(); prev.value = ""; }
  }
}

// ── Board read/write ─────────────────────────────────────────────────────────

/** Read the current input grid into a 2D array. */
function readBoard() {
  const size = currentSize;
  const board = Array.from({length: size}, () => Array(size).fill(0));
  inputGrid.querySelectorAll("input.cell").forEach(inp => {
    const r = parseInt(inp.dataset.row, 10);
    const c = parseInt(inp.dataset.col, 10);
    const val = inp.value.trim();
    if (val !== "") {
      board[r][c] = size <= 9 ? parseInt(val, 10) : parseInt(val, 16);
    }
  });
  return board;
}

// ── Result display ────────────────────────────────────────────────────────────

function showEmpty() {
  resultEmpty.classList.remove("hidden");
  resultContent.classList.add("hidden");
  resultError.classList.add("hidden");
}

function showError(msg) {
  resultEmpty.classList.add("hidden");
  resultContent.classList.add("hidden");
  resultError.classList.remove("hidden");
  errorMsg.textContent = msg;
}

function showResult(data, originalBoard) {
  resultEmpty.classList.add("hidden");
  resultError.classList.add("hidden");
  resultContent.classList.remove("hidden");

  // Difficulty badge
  difficultyBadge.textContent = data.difficulty || "—";
  difficultyBadge.className = "difficulty-badge " + (data.difficulty || "");

  // Meta stats
  metaSteps.textContent = `${data.total_steps} steps`;
  metaBt.textContent    = `${data.backtrack_count} backtracks`;

  // Solved grid
  buildSolutionGrid(solutionGrid, data.solution, originalBoard);

  // Steps
  renderSteps(data.steps || []);
}

function renderSteps(steps) {
  stepsList.innerHTML = "";
  stepsCount.textContent = steps.length;

  // Limit rendered steps for performance on large grids
  const MAX_RENDER = 500;
  const visible = steps.slice(0, MAX_RENDER);

  visible.forEach((step, i) => {
    const div = document.createElement("div");
    div.className = "step-item";

    const badge = document.createElement("span");
    badge.className = `step-badge ${step.action}`;
    badge.textContent = step.action === "place" ? "Place" : "Undo";

    const text = document.createElement("span");
    const r = step.row + 1, c = step.col + 1;
    text.textContent = step.action === "place"
      ? `[${r},${c}] ← ${step.value}`
      : `[${r},${c}] ✗ ${step.value}  (${step.backtracks_total} total)`;

    div.appendChild(badge);
    div.appendChild(text);
    stepsList.appendChild(div);
  });

  if (steps.length > MAX_RENDER) {
    const note = document.createElement("div");
    note.className = "step-item";
    note.style.color = "var(--ink-60)";
    note.textContent = `… and ${steps.length - MAX_RENDER} more steps not shown.`;
    stepsList.appendChild(note);
  }
}

// ── Loading state ─────────────────────────────────────────────────────────────

function setLoading(btn, state) {
  if (state) {
    btn.classList.add("loading");
    btn.disabled = true;
  } else {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
}

// ── API calls ─────────────────────────────────────────────────────────────────

async function solveManual() {
  const board = readBoard();

  // Quick client-side empty check
  const filled = board.flat().filter(v => v !== 0).length;
  if (filled === 0) {
    showError("Please enter at least one digit before solving.");
    return;
  }

  setLoading(btnSolveManual, true);

  try {
    const resp = await fetch(`${API_BASE}/solve/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ board }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      showError(data.detail || data.message || "An error occurred.");
      return;
    }

    showResult(data, board);
  } catch (err) {
    showError(
      "Could not reach the API server. Make sure the backend is running on " +
      API_BASE + "."
    );
  } finally {
    setLoading(btnSolveManual, false);
  }
}

async function solveImage() {
  if (!uploadedFile) return;

  const originalBoard = null; // We don't have the board before OCR
  setLoading(btnSolveImage, true);

  try {
    const formData = new FormData();
    formData.append("file", uploadedFile);

    const resp = await fetch(`${API_BASE}/solve/image`, {
      method: "POST",
      body: formData,
    });

    const data = await resp.json();

    if (!resp.ok) {
      showError(data.detail || data.message || "Image processing failed.");
      return;
    }

    // For image solves, mark all cells as solved (no original known)
    const fakeOriginal = Array.from({length: data.solution.length},
      () => Array(data.solution.length).fill(0));

    showResult(data, fakeOriginal);
  } catch (err) {
    showError(
      "Could not reach the API server. Make sure the backend is running on " +
      API_BASE + "."
    );
  } finally {
    setLoading(btnSolveImage, false);
  }
}

// ── Tab switching ─────────────────────────────────────────────────────────────

tabBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    tabBtns.forEach(b => { b.classList.remove("active"); b.setAttribute("aria-selected","false"); });
    tabContents.forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    btn.setAttribute("aria-selected","true");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    showEmpty();
  });
});

// ── Size pills ────────────────────────────────────────────────────────────────

pills.forEach(pill => {
  pill.addEventListener("click", () => {
    pills.forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    currentSize = parseInt(pill.dataset.size, 10);
    buildInputGrid(inputGrid, currentSize);
    showEmpty();
  });
});

// ── Clear / Example ───────────────────────────────────────────────────────────

btnClear.addEventListener("click", () => {
  buildInputGrid(inputGrid, currentSize);
  showEmpty();
});

btnExample.addEventListener("click", () => {
  buildInputGrid(inputGrid, currentSize, EXAMPLES[currentSize]);
  showEmpty();
});

// ── Solve buttons ─────────────────────────────────────────────────────────────

btnSolveManual.addEventListener("click", solveManual);
btnSolveImage.addEventListener("click", solveImage);

// ── File upload ───────────────────────────────────────────────────────────────

function handleFile(file) {
  if (!file) return;
  if (!["image/jpeg","image/jpg","image/png"].includes(file.type)) {
    showError("Please upload a JPEG or PNG image.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError("File exceeds 10 MB limit.");
    return;
  }
  uploadedFile = file;
  const url = URL.createObjectURL(file);
  imagePreview.src = url;
  imagePreviewWrap.classList.remove("hidden");
  dropZone.style.display = "none";
  btnSolveImage.disabled = false;
  showEmpty();
}

fileInput.addEventListener("change", e => handleFile(e.target.files[0]));

btnRemoveImage.addEventListener("click", () => {
  uploadedFile = null;
  imagePreview.src = "";
  imagePreviewWrap.classList.add("hidden");
  dropZone.style.display = "";
  btnSolveImage.disabled = true;
  fileInput.value = "";
  showEmpty();
});

// Drag and drop
dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  handleFile(e.dataTransfer.files[0]);
});

// ── Init ──────────────────────────────────────────────────────────────────────

buildInputGrid(inputGrid, currentSize);
