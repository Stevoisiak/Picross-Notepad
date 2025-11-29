from enum import IntEnum

# picross.py
import tkinter as tk
from tkinter import ttk

CELL_SIZE = 28
GRID_DIMENSIONS = 16
GRID_LINE_COLOR = "#A9A9A9"
HINT_BG_COLOR = "#F0F0F0"
GRID_BG_COLOR = "#FFFFFF"
CELL_FILLED_COLOR = "#111111"
CELL_X_COLOR = "#D22"
CELL_MAYBE_COLOR = "#666"
BLOCK_INTERVAL = 4  # thicker grid lines every BLOCK_SIZE cells
LINE_THIN = 1
LINE_THICK = 2
HINT_FONT = ("Segoe UI", 10, "bold")
HINTS_PER_SIDE = 4
TOP_HINT_ENTRY_HEIGHT = 22
LEFT_HINT_ENTRY_WIDTH = 28  # FIXME: When this is too thin, line doesn't reach main grid

class CellState(IntEnum):
    EMPTY = 0
    FILLED = 1
    X = 2
    MAYBE = 3

class PicrossApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Picross 16×16")
        self.resizable(False, False)

        # Grid state and drawing helpers
        self.grid_state = [[CellState.EMPTY for _ in range(GRID_DIMENSIONS)] for _ in range(GRID_DIMENSIONS)]
        self.rect_ids = [[None for _ in range(GRID_DIMENSIONS)] for _ in range(GRID_DIMENSIONS)]
        self.mark_tags = [[f"mark_{row}_{col}" for col in range(GRID_DIMENSIONS)] for row in range(GRID_DIMENSIONS)]
        self._reset_drag()

        # Hint entries (4 per row, 4 per column)
        self.row_hint_entries = None  # list[list[Entry]] length GRID_SIZE, each with 4 entries
        self.col_hint_entries = None  # list[list[Entry]] length GRID_SIZE, each with 4 entries

        self._build_ui()
        self._draw_grid()

    def _build_ui(self):
        root = ttk.Frame(self, padding=8)
        root.grid(sticky="nsew")

        # Toolbar
        toolbar = ttk.Frame(root)
        toolbar.grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Button(toolbar, text="Reset Board", command=self.reset_board).grid(row=0, column=0, padx=(0,3))
        ttk.Button(toolbar, text="Clear Hints", command=self.clear_hints).grid(row=0, column=1, padx=(0,3))
        ttk.Label(toolbar, text="Controls: Left=Fill • Right=X • Middle=Maybe • Drag to paint").grid(row=0, column=2)

        # Main area with hints + grid
        area = ttk.Frame(root)
        area.grid(row=1, column=0)

        # === Column separators canvas (TOP) ===
        top_canvas_height = HINTS_PER_SIDE * TOP_HINT_ENTRY_HEIGHT
        self.col_sep_canvas = tk.Canvas(
            area,
            width=GRID_DIMENSIONS * CELL_SIZE,
            height=top_canvas_height,
            bg=HINT_BG_COLOR,
            highlightthickness=0,
        )
        self.col_sep_canvas.grid(row=0, column=1, columnspan=GRID_DIMENSIONS, sticky="ew")

        # === Column hints: 4 stacked per column ===
        self.col_hint_entries = [[] for _ in range(GRID_DIMENSIONS)]
        for col in range(GRID_DIMENSIONS):
            col_frame = tk.Frame(area, bg=HINT_BG_COLOR)
            col_frame.grid(row=0, column=col+1, padx=(0,0), pady=(0,0))
            for i in range(HINTS_PER_SIDE):
                e = tk.Entry(col_frame, width=3, justify="center", bg=HINT_BG_COLOR, relief="flat", bd=0, font=HINT_FONT)
                e.grid(row=i, column=0, pady=0, ipady=0)
                self.col_hint_entries[col].append(e)

        # Draw vertical separators between columns on the top canvas
        self._draw_top_hint_separators(top_canvas_height)

        # === Row separators canvas (LEFT) ===
        left_canvas_width = HINTS_PER_SIDE * LEFT_HINT_ENTRY_WIDTH  # width to accommodate 4 entries
        self.row_sep_canvas = tk.Canvas(
            area,
            width=left_canvas_width,
            height=GRID_DIMENSIONS * CELL_SIZE,
            bg=HINT_BG_COLOR,
            highlightthickness=0,
        )
        self.row_sep_canvas.grid(row=1, column=0, rowspan=GRID_DIMENSIONS, sticky="ns")

        # === Row hints: 4 horizontally per row ===
        self.row_hint_entries = [[] for _ in range(GRID_DIMENSIONS)]
        for row in range(GRID_DIMENSIONS):
            row_frame = tk.Frame(area, bg=HINT_BG_COLOR)
            row_frame.grid(row=row+1, column=0, padx=(0,0), pady=(0,0), sticky="w")
            for i in range(HINTS_PER_SIDE):
                e = tk.Entry(row_frame, width=3, justify="center", bg=HINT_BG_COLOR, relief="flat", bd=0, font=HINT_FONT)
                e.grid(row=0, column=i, padx=(4 if i > 0 else 0,0), ipady=2)
                self.row_hint_entries[row].append(e)

        # Draw horizontal separators between rows on the left canvas
        self._draw_left_hint_separators(left_canvas_width)

        # Canvas for the main grid
        grid_canvas_width = GRID_DIMENSIONS * CELL_SIZE
        grid_canvas_height = GRID_DIMENSIONS * CELL_SIZE
        self.grid_canvas = tk.Canvas(area, width=grid_canvas_width, height=grid_canvas_height, bg=GRID_BG_COLOR, highlightthickness=0)
        self.grid_canvas.grid(row=1, column=1, rowspan=GRID_DIMENSIONS, columnspan=GRID_DIMENSIONS)

        # Bind mouse input for grid cells
        self.grid_canvas.bind("<Button-1>", lambda e: self._on_press(e, CellState.FILLED))
        self.grid_canvas.bind("<B1-Motion>", self._on_drag)
        self.grid_canvas.bind("<ButtonRelease-1>", self._reset_drag)
        # Middle click (Button-2); Shift-Left fallback
        self.grid_canvas.bind("<Button-2>", lambda e: self._on_press(e, CellState.MAYBE))
        self.grid_canvas.bind("<B2-Motion>", self._on_drag)
        self.grid_canvas.bind("<ButtonRelease-2>", self._reset_drag)
        self.grid_canvas.bind("<Shift-Button-1>", lambda e: self._on_press(e, CellState.MAYBE))
        self.grid_canvas.bind("<Shift-B1-Motion>", self._on_drag)
        self.grid_canvas.bind("<Shift-ButtonRelease-1>", self._reset_drag)
        # Right click (Button-3); Ctrl-Left fallback (macOS)
        self.grid_canvas.bind("<Button-3>", lambda e: self._on_press(e, CellState.X))
        self.grid_canvas.bind("<B3-Motion>", self._on_drag)
        self.grid_canvas.bind("<ButtonRelease-3>", self._reset_drag)
        self.grid_canvas.bind("<Control-Button-1>", lambda e: self._on_press(e, CellState.X))
        self.grid_canvas.bind("<Control-B1-Motion>", self._on_drag)
        self.grid_canvas.bind("<Control-ButtonRelease-1>", self._reset_drag)
        # Mouse5 = clear
        self.grid_canvas.bind("<Button-5>", lambda e: self._on_press(e, CellState.EMPTY))
        self.grid_canvas.bind("<B5-Motion>", self._on_drag)
        self.grid_canvas.bind("<ButtonRelease-5>", self._reset_drag)


        # Bind arrow key navigation for hint boxes
        self._bind_hint_navigation()

    def _draw_top_hint_separators(self, height: int) -> None:
        """Draw vertical lines between columns in the top hints area, including outer borders with proper stroke insets."""
        self.col_sep_canvas.delete("sep")

        # Outer borders (use half-width inset to avoid clipping)
        inset = LINE_THICK / 2
        total_width = GRID_DIMENSIONS * CELL_SIZE

        # Left border
        self.col_sep_canvas.create_line(
            inset, 0, inset, height,
            fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
        )
        # Right border
        self.col_sep_canvas.create_line(
            total_width - inset, 0, total_width - inset, height,
            fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
        )

        # Thin separators between columns
        for i in range(1, GRID_DIMENSIONS):
            x_pos = i * CELL_SIZE
            self.col_sep_canvas.create_line(
                x_pos, 0, x_pos, height,
                fill=GRID_LINE_COLOR, width=LINE_THIN, tags=("sep",)
            )

        # Thicker delimiters every 4th column to match grid blocks
        for i in range(BLOCK_INTERVAL, GRID_DIMENSIONS, BLOCK_INTERVAL):
            x_pos = i * CELL_SIZE
            self.col_sep_canvas.create_line(
                x_pos, 0, x_pos, height,
                fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
            )


    def _draw_left_hint_separators(self, width: int) -> None:
        """Draw horizontal lines between rows in the left hints area, including outer borders with proper stroke insets."""
        self.row_sep_canvas.delete("sep")

        # Outer borders (use half-width inset to avoid clipping)
        inset = LINE_THICK / 2
        total_height = GRID_DIMENSIONS * CELL_SIZE

        # Top border
        self.row_sep_canvas.create_line(
            0, inset, width, inset,
            fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
        )
        # Bottom border
        self.row_sep_canvas.create_line(
            0, total_height - inset, width, total_height - inset,
            fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
        )

        # Thin separators between rows
        for i in range(1, GRID_DIMENSIONS):
            y_pos = i * CELL_SIZE
            self.row_sep_canvas.create_line(
                0, y_pos, width, y_pos,
                fill=GRID_LINE_COLOR, width=LINE_THIN, tags=("sep",)
            )

        # Thicker delimiters every 4th row to match grid blocks
        for i in range(BLOCK_INTERVAL, GRID_DIMENSIONS, BLOCK_INTERVAL):
            y_pos = i * CELL_SIZE
            self.row_sep_canvas.create_line(
                0, y_pos, width, y_pos,
                fill=GRID_LINE_COLOR, width=LINE_THICK, tags=("sep",)
            )

    def _draw_grid(self):
        # Draw cell rectangles: fills only; no outlines (prevents doubled internal borders)
        for row in range(GRID_DIMENSIONS):
            for col in range(GRID_DIMENSIONS):
                x0 = col * CELL_SIZE
                y0 = row * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                rid = self.grid_canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=GRID_BG_COLOR, outline="", width=0,
                    tags=(f"cell_{row}_{col}",)
                )
                self.rect_ids[row][col] = rid

        # Draw internal vertical/horizontal separators (skip outer edges here)
        for i in range(1, GRID_DIMENSIONS):
            # Choose width (thick every BLOCK_INTERVAL)
            line_width = LINE_THICK if i % BLOCK_INTERVAL == 0 else LINE_THIN
            x_pos = i * CELL_SIZE
            y_pos = i * CELL_SIZE

            # vertical internal line
            self.grid_canvas.create_line(
                x_pos, 0, x_pos, GRID_DIMENSIONS * CELL_SIZE,
                fill=GRID_LINE_COLOR, width=line_width
            )
            # horizontal internal line
            self.grid_canvas.create_line(
                0, y_pos, GRID_DIMENSIONS * CELL_SIZE, y_pos,
                fill=GRID_LINE_COLOR, width=line_width
            )

        # Draw outer border as a single rectangle inset so full stroke is visible
        inset = LINE_THICK / 2
        total_width = GRID_DIMENSIONS * CELL_SIZE
        total_height = GRID_DIMENSIONS * CELL_SIZE

        self.grid_canvas.create_rectangle(
            inset, inset, total_width - inset, total_height - inset,
            outline=GRID_LINE_COLOR, width=LINE_THICK
        )

    def reset_board(self):
        for row in range(GRID_DIMENSIONS):
            for col in range(GRID_DIMENSIONS):
                self._set_cell(row, col, CellState.EMPTY)

    def clear_hints(self):
        for row in range(GRID_DIMENSIONS):
            for i in range(HINTS_PER_SIDE):
                self.row_hint_entries[row][i].delete(0, tk.END)
        for col in range(GRID_DIMENSIONS):
            for i in range(HINTS_PER_SIDE):
                self.col_hint_entries[col][i].delete(0, tk.END)

    # === Arrow key navigation across hint boxes ===
    def _bind_hint_navigation(self):
        # Row hints: left/right within the row; up/down to same index in prev/next row
        for row in range(GRID_DIMENSIONS):
            for i in range(HINTS_PER_SIDE):
                e = self.row_hint_entries[row][i]
                e.bind("<Up>", lambda ev, row=row, i=i: self._row_hint_move(row, i, "up"))
                e.bind("<Down>", lambda ev, row=row, i=i: self._row_hint_move(row, i, "down"))
                e.bind("<Left>", lambda ev, row=row, i=i: self._row_hint_move(row, i, "left"))
                e.bind("<Right>", lambda ev, row=row, i=i: self._row_hint_move(row, i, "right"))

        # Column hints: up/down within the column; left/right to same index in prev/next column
        for col in range(GRID_DIMENSIONS):
            for i in range(HINTS_PER_SIDE):
                e = self.col_hint_entries[col][i]
                e.bind("<Up>", lambda ev, col=col, i=i: self._col_hint_move(col, i, "up"))
                e.bind("<Down>", lambda ev, col=col, i=i: self._col_hint_move(col, i, "down"))
                e.bind("<Left>", lambda ev, col=col, i=i: self._col_hint_move(col, i, "left"))
                e.bind("<Right>", lambda ev, col=col, i=i: self._col_hint_move(col, i, "right"))

    def _row_hint_move(self, row, i, direction):
        target = None
        if direction == "up":
            if row > 0:
                target = self.row_hint_entries[row-1][i]
        elif direction == "down":
            if row < GRID_DIMENSIONS - 1:
                target = self.row_hint_entries[row+1][i]
        elif direction == "left":
            if i > 0:
                target = self.row_hint_entries[row][i-1]
        elif direction == "right":
            if i < HINTS_PER_SIDE - 1:
                target = self.row_hint_entries[row][i+1]

        if target is not None:
            self._focus_entry(target)
            return "break"  # prevent default caret movement
        # else: let default behavior (caret motion) occur

    def _col_hint_move(self, col, i, direction):
        target = None
        if direction == "up":
            if i > 0:
                target = self.col_hint_entries[col][i-1]
        elif direction == "down":
            if i < HINTS_PER_SIDE - 1:
                target = self.col_hint_entries[col][i+1]
        elif direction == "left":
            if col > 0:
                target = self.col_hint_entries[col-1][i]
        elif direction == "right":
            if col < GRID_DIMENSIONS - 1:
                target = self.col_hint_entries[col+1][i]

        if target is not None:
            self._focus_entry(target)
            return "break"
        # else: let default behavior occur

    def _focus_entry(self, entry):
        entry.focus_set()
        # Select the whole content for fast editing (optional)
        try:
            entry.selection_range(0, tk.END)
        except tk.TclError:
            pass
        # Put caret at end (in case selection isn't desired)
        try:
            entry.icursor(tk.END)
        except tk.TclError:
            pass

    def _event_to_locked_cell(self, event):
        base = self._event_to_cell(event)
        if not base:
            return None
        row, col = base

        # If lock_axis is active, override row or column based on axis
        if self.dragging_lock_axis:
            axis, idx = self.dragging_lock_axis
            if axis == 'row':
                # Force row to locked row, compute column from mouse x
                row = idx
                col = event.x // CELL_SIZE
            elif axis == 'col':
                # Force column to locked column, compute row from mouse y
                col = idx
                row = event.y // CELL_SIZE
        # Validate bounds
        if row < 0 or row >= GRID_DIMENSIONS or col < 0 or col >= GRID_DIMENSIONS:
            return None
        return int(row), int(col)

    def _update_drag_axis_lock(self, cell):
        if not self.dragging_path_cells or self.dragging_path_cells[-1] != cell:
            self.dragging_path_cells.append(cell)
        if len(self.dragging_path_cells) == 2 and self.dragging_lock_axis is None:
            r1, c1 = self.dragging_path_cells[0]
            r2, c2 = self.dragging_path_cells[1]
            if r1 == r2:
                self.dragging_lock_axis = ('row', r1)
            elif c1 == c2:
                self.dragging_lock_axis = ('col', c1)

    def _compute_drag_target(self, row, col, desired_state):
        current = self.grid_state[row][col]
        if desired_state == CellState.EMPTY:
            return CellState.EMPTY
        return CellState.EMPTY if current == desired_state else desired_state

    def _apply_cell_state(self, event, target_state):
        cell = self._event_to_locked_cell(event)
        if not cell:
            return
        row, col = cell
        # Enforce lock if set
        if self.dragging_lock_axis:
            axis, idx = self.dragging_lock_axis
            if (axis == 'row' and row != idx) or (axis == 'col' and col != idx):
                return
        if self.grid_state[row][col] != target_state:
            self._set_cell(row, col, target_state)


    # === Grid interaction ===
    def _on_press(self, event, desired_state):
        cell = self._event_to_locked_cell(event)
        if not cell:
            return
        row, col = cell
        self.dragging_target_state = self._compute_drag_target(row, col, desired_state)
        self.dragging_path_cells = []
        self.dragging_lock_axis = None
        self.user_is_dragging = True
        self._update_drag_axis_lock((row, col))
        self._apply_cell_state(event, self.dragging_target_state)

    def _on_drag(self, event):
        if not self.user_is_dragging:
            return
        cell = self._event_to_locked_cell(event)
        if not cell:
            return
        self._update_drag_axis_lock(cell)
        self._apply_cell_state(event, self.dragging_target_state)

    def _reset_drag(self, event=None):
        self.user_is_dragging = False
        self.dragging_lock_axis = None  # ('row', index) or ('col', index)
        self.dragging_path_cells = []  # track cells filled during drag
        self.dragging_target_state = CellState.EMPTY

    def _event_to_cell(self, event):
        x, y = event.x, event.y
        if x < 0 or y < 0:
            return None
        col = x // CELL_SIZE
        row = y // CELL_SIZE
        if 0 <= row < GRID_DIMENSIONS and 0 <= col < GRID_DIMENSIONS:
            return int(row), int(col)
        return None

    def _set_cell(self, row, col, state):
        self.grid_state[row][col] = state
        rect_id = self.rect_ids[row][col]
        tag = self.mark_tags[row][col]

        # Clear any mark overlays for this cell
        self.grid_canvas.delete(tag)

        # Base background
        if state == CellState.FILLED:
            self.grid_canvas.itemconfig(rect_id, fill=CELL_FILLED_COLOR)
        else:
            self.grid_canvas.itemconfig(rect_id, fill=GRID_BG_COLOR)

        # Overlay marks for X and Maybe
        x0 = col * CELL_SIZE
        y0 = row * CELL_SIZE
        x1 = x0 + CELL_SIZE
        y1 = y0 + CELL_SIZE
        pad = 6

        if state == CellState.X:
            # Draw an 'X'
            self.grid_canvas.create_line(x0+pad, y0+pad, x1-pad, y1-pad, fill=CELL_X_COLOR, width=2, tags=(tag,))
            self.grid_canvas.create_line(x0+pad, y1-pad, x1-pad, y0+pad, fill=CELL_X_COLOR, width=2, tags=(tag,))
        elif state == CellState.MAYBE:
            # Draw a '?' marker
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.grid_canvas.create_text(cx, cy, text="?", fill=CELL_MAYBE_COLOR, font=("Segoe UI", 12, "bold"), tags=(tag,))

if __name__ == "__main__":
    PicrossApp().mainloop()
