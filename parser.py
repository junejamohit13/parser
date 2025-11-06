/* Drag handle for Excel-like drag-to-fill */
.drag-handle {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 10px;
  height: 10px;
  background-color: #2563eb;
  border: 2px solid white;
  border-radius: 2px;
  cursor: crosshair;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 100;
  pointer-events: auto;
}

.group:hover .drag-handle {
  opacity: 1;
  pointer-events: auto;
}

.drag-handle:hover {
  background-color: #1d4ed8;
  transform: scale(1.3);
}

.drag-handle:active {
  cursor: crosshair;
}

/* Cell wrapper */
.cell-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

/* Prevent text selection while dragging */
.group {
  user-select: none;
}

.dragging {
  cursor: crosshair !important;
}

.dragging * {
  cursor: crosshair !important;
}
