
# picross.py
import tkinter as tk
from tkinter import ttk

CELL_SIZE = 28
GRID_SIZE = 16
LINE_COLOR = "#A9A9A9"
BG_HINT = "#F0F0F0"
BG_GRID = "#FFFFFF"
FILLED_COLOR = "#111111"
X_COLOR = "#D22"
MAYBE_COLOR = "#666"

STATE_EMPTY = 0
STATE_FILLED = 1
STATE_X = 2
STATE_MAYBE = 3

class PicrossApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Picross 16×16")
        self.resizable(False, False)

        # Grid state and drawing helpers
        self.grid_state = [[STATE_EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.rect_ids = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.mark_tags = [[f"mark_{r}_{c}" for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]

        # Drag painting
        self.drag_active = False
        self.lock_axis = None
        self.drag_cells = []
        self.drag_target_state = STATE_EMPTY
        self.drag_button = None
        self.lock_axis = None  # ('row', index) or ('col', index)
        self.drag_cells = []  # track cells filled during drag

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

        # === Column hints: 4 stacked per column ===
        self.col_hint_entries = [[] for _ in range(GRID_SIZE)]
        for c in range(GRID_SIZE):
            col_frame = tk.Frame(area, bg=BG_HINT)
            col_frame.grid(row=0, column=c+1, padx=(0,0), pady=(0,2))
            for i in range(4):
                e = tk.Entry(col_frame, width=3, justify="center", bg=BG_HINT, relief="solid", bd=1, font=("Segoe UI", 10, "bold"))
                e.grid(row=i, column=0, pady=0)
                self.col_hint_entries[c].append(e)

        # === Row hints: 4 horizontally per row ===
        self.row_hint_entries = [[] for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            row_frame = tk.Frame(area, bg=BG_HINT)
            row_frame.grid(row=r+1, column=0, padx=(0,2), pady=(0,0))
            for i in range(4):
                e = tk.Entry(row_frame, width=3, justify="center", bg=BG_HINT, relief="solid", bd=1, font=("Segoe UI", 10, "bold"))
                e.grid(row=0, column=i, padx=0)
                self.row_hint_entries[r].append(e)

        # Canvas for the main grid
        canvas_w = GRID_SIZE * CELL_SIZE
        canvas_h = GRID_SIZE * CELL_SIZE
        self.canvas = tk.Canvas(area, width=canvas_w, height=canvas_h, bg=BG_GRID, highlightthickness=0)
        self.canvas.grid(row=1, column=1, rowspan=GRID_SIZE, columnspan=GRID_SIZE)

        # Bind mouse input for grid cells
        self.canvas.bind("<Button-1>", lambda e: self._on_press(e, STATE_FILLED, 1))
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        # Middle click (Button-2); Shift-Left fallback
        self.canvas.bind("<Button-2>", lambda e: self._on_press(e, STATE_MAYBE, 2))
        self.canvas.bind("<B2-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_release)
        self.canvas.bind("<Shift-Button-1>", lambda e: self._on_press(e, STATE_MAYBE, 2))
        self.canvas.bind("<Shift-B1-Motion>", self._on_drag)
        self.canvas.bind("<Shift-ButtonRelease-1>", self._on_release)
        # Right click (Button-3); Ctrl-Left fallback (macOS)
        self.canvas.bind("<Button-3>", lambda e: self._on_press(e, STATE_X, 3))
        self.canvas.bind("<B3-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_release)
        self.canvas.bind("<Control-Button-1>", lambda e: self._on_press(e, STATE_X, 3))
        self.canvas.bind("<Control-B1-Motion>", self._on_drag)
        self.canvas.bind("<Control-ButtonRelease-1>", self._on_release)
        # Mouse5 = clear
        self.canvas.bind("<Button-5>", lambda e: self._on_press(e, STATE_EMPTY, 8))
        self.canvas.bind("<B5-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-5>", self._on_release)


        # Bind arrow key navigation for hint boxes
        self._bind_hint_navigation()

    def _draw_grid(self):
        # Draw cell rectangles
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                rid = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=BG_GRID, outline=LINE_COLOR, width=1, tags=(f"cell_{r}_{c}",)
                )
                self.rect_ids[r][c] = rid

        # Thicker delimiter lines every 4th (optional)
        for i in range(GRID_SIZE + 1):
            w = 2 if i % 4 == 0 else 1
            # vertical
            self.canvas.create_line(i * CELL_SIZE, 0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, fill=LINE_COLOR, width=w)
            # horizontal
            self.canvas.create_line(0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, i * CELL_SIZE, fill=LINE_COLOR, width=w)

    def reset_board(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self._set_cell(r, c, STATE_EMPTY)

    def clear_hints(self):
        for r in range(GRID_SIZE):
            for i in range(4):
                self.row_hint_entries[r][i].delete(0, tk.END)
        for c in range(GRID_SIZE):
            for i in range(4):
                self.col_hint_entries[c][i].delete(0, tk.END)

    # === Arrow key navigation across hint boxes ===
    def _bind_hint_navigation(self):
        # Row hints: left/right within the row; up/down to same index in prev/next row
        for r in range(GRID_SIZE):
            for i in range(4):
                e = self.row_hint_entries[r][i]
                e.bind("<Left>", lambda ev, r=r, i=i: self._row_hint_move(r, i, "left"))
                e.bind("<Right>", lambda ev, r=r, i=i: self._row_hint_move(r, i, "right"))
                e.bind("<Up>", lambda ev, r=r, i=i: self._row_hint_move(r, i, "up"))
                e.bind("<Down>", lambda ev, r=r, i=i: self._row_hint_move(r, i, "down"))

        # Column hints: up/down within the column; left/right to same index in prev/next column
        for c in range(GRID_SIZE):
            for i in range(4):
                e = self.col_hint_entries[c][i]
                e.bind("<Up>", lambda ev, c=c, i=i: self._col_hint_move(c, i, "up"))
                e.bind("<Down>", lambda ev, c=c, i=i: self._col_hint_move(c, i, "down"))
                e.bind("<Left>", lambda ev, c=c, i=i: self._col_hint_move(c, i, "left"))
                e.bind("<Right>", lambda ev, c=c, i=i: self._col_hint_move(c, i, "right"))

    def _row_hint_move(self, r, i, direction):
        target = None
        if direction == "left":
            if i > 0:
                target = self.row_hint_entries[r][i-1]
        elif direction == "right":
            if i < 3:
                target = self.row_hint_entries[r][i+1]
        elif direction == "up":
            if r > 0:
                target = self.row_hint_entries[r-1][i]
        elif direction == "down":
            if r < GRID_SIZE - 1:
                target = self.row_hint_entries[r+1][i]

        if target is not None:
            self._focus_entry(target)
            return "break"  # prevent default caret movement
        # else: let default behavior (caret motion) occur

    def _col_hint_move(self, c, i, direction):
        target = None
        if direction == "up":
            if i > 0:
                target = self.col_hint_entries[c][i-1]
        elif direction == "down":
            if i < 3:
                target = self.col_hint_entries[c][i+1]
        elif direction == "left":
            if c > 0:
                target = self.col_hint_entries[c-1][i]
        elif direction == "right":
            if c < GRID_SIZE - 1:
                target = self.col_hint_entries[c+1][i]

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

    # === Grid interaction ===
    def _on_press(self, event, desired_state, button_id):
        cell = self._event_to_cell(event)
        if not cell:
            return
        r, c = cell

        # If lock_axis is active, override row or column based on axis
        if self.lock_axis:
            axis, idx = self.lock_axis
            if axis == 'row':
                # Force row to locked row, compute column from mouse x
                r = idx
                c = event.x // CELL_SIZE
            elif axis == 'col':
                # Force column to locked column, compute row from mouse y
                c = idx
                r = event.y // CELL_SIZE
            # Validate bounds
            if r < 0 or r >= GRID_SIZE or c < 0 or c >= GRID_SIZE:
                return


        # Track cells and determine lock axis
        if cell not in self.drag_cells:
            self.drag_cells.append(cell)
            if len(self.drag_cells) == 2 and self.lock_axis is None:
                r1, c1 = self.drag_cells[0]
                r2, c2 = self.drag_cells[1]
                if r1 == r2:
                    self.lock_axis = ('row', r1)
                elif c1 == c2:
                    self.lock_axis = ('col', c1)

        # Enforce lock if set
        if self.lock_axis:
            axis, idx = self.lock_axis
            if axis == 'row' and r != idx:
                return
            if axis == 'col' and c != idx:
                return

        current = self.grid_state[r][c]

        # If we're clearing, never toggle — always clear
        if desired_state == STATE_EMPTY:
            self.drag_target_state = STATE_EMPTY
        else:
            # Toggle: clicking same state sets to empty; else set to desired state
            if current == desired_state:
                self.drag_target_state = STATE_EMPTY
            else:
                self.drag_target_state = desired_state

        self.drag_cells = []
        self.lock_axis = None
        self.drag_active = True
        self.drag_button = button_id
        self._set_cell(r, c, self.drag_target_state)

    def _on_drag(self, event):
        if not self.drag_active:
            return
        cell = self._event_to_cell(event)
        if not cell:
            return
        r, c = cell

        # If lock_axis is active, override row or column based on axis
        if self.lock_axis:
            axis, idx = self.lock_axis
            if axis == 'row':
                # Force row to locked row, compute column from mouse x
                r = idx
                c = event.x // CELL_SIZE
            elif axis == 'col':
                # Force column to locked column, compute row from mouse y
                c = idx
                r = event.y // CELL_SIZE
            # Validate bounds
            if r < 0 or r >= GRID_SIZE or c < 0 or c >= GRID_SIZE:
                return


        # Track cells and determine lock axis
        if cell not in self.drag_cells:
            self.drag_cells.append(cell)
            if len(self.drag_cells) == 2 and self.lock_axis is None:
                r1, c1 = self.drag_cells[0]
                r2, c2 = self.drag_cells[1]
                if r1 == r2:
                    self.lock_axis = ('row', r1)
                elif c1 == c2:
                    self.lock_axis = ('col', c1)

        # Enforce lock if set
        if self.lock_axis:
            axis, idx = self.lock_axis
            if axis == 'row' and r != idx:
                return
            if axis == 'col' and c != idx:
                return

        if self.grid_state[r][c] != self.drag_target_state:
            self._set_cell(r, c, self.drag_target_state)

    def _on_release(self, event):
        self.drag_active = False
        self.lock_axis = None
        self.drag_cells = []
        self.drag_button = None
        self.lock_axis = None  # ('row', index) or ('col', index)
        self.drag_cells = []  # track cells filled during drag

    def _event_to_cell(self, event):
        x, y = event.x, event.y
        if x < 0 or y < 0:
            return None
        c = x // CELL_SIZE
        r = y // CELL_SIZE
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            return int(r), int(c)
        return None

    def _set_cell(self, r, c, state):
        self.grid_state[r][c] = state
        rect_id = self.rect_ids[r][c]
        tag = self.mark_tags[r][c]

        # Clear any mark overlays for this cell
        self.canvas.delete(tag)

        # Base background
        if state == STATE_FILLED:
            self.canvas.itemconfig(rect_id, fill=FILLED_COLOR)
        else:
            self.canvas.itemconfig(rect_id, fill=BG_GRID)

        # Overlay marks for X and Maybe
        x0 = c * CELL_SIZE
        y0 = r * CELL_SIZE
        x1 = x0 + CELL_SIZE
        y1 = y0 + CELL_SIZE
        pad = 6

        if state == STATE_X:
            # Draw an 'X'
            self.canvas.create_line(x0+pad, y0+pad, x1-pad, y1-pad, fill=X_COLOR, width=2, tags=(tag,))
            self.canvas.create_line(x0+pad, y1-pad, x1-pad, y0+pad, fill=X_COLOR, width=2, tags=(tag,))
        elif state == STATE_MAYBE:
            # Draw a '?' marker
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.canvas.create_text(cx, cy, text="?", fill=MAYBE_COLOR, font=("Segoe UI", 12, "bold"), tags=(tag,))

if __name__ == "__main__":
    PicrossApp().mainloop()
