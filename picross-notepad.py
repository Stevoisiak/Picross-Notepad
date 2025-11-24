
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

        self.grid_state = [[STATE_EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.rect_ids = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.mark_tags = [[f"mark_{r}_{c}" for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]

        self.drag_active = False
        self.drag_target_state = STATE_EMPTY
        self.drag_button = None

        self._build_ui()
        self._draw_grid()

    def _build_ui(self):
        root = ttk.Frame(self, padding=8)
        root.grid(sticky="nsew")

        # Top instructions / actions
        toolbar = ttk.Frame(root)
        toolbar.grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Button(toolbar, text="Reset Board", command=self.reset_board).grid(row=0, column=0, padx=(0,6))
        ttk.Button(toolbar, text="Clear Hints", command=self.clear_hints).grid(row=0, column=1, padx=(0,6))
        ttk.Label(toolbar, text="Controls: Left=Fill  •  Right=X  •  Middle=Maybe  •  Drag to paint").grid(row=0, column=2)

        # Main area with hints + grid
        area = ttk.Frame(root)
        area.grid(row=1, column=0)

        # Corner label (top-left)
        corner = tk.Label(area, text="Hints", bg=BG_HINT, width=6)
        corner.grid(row=0, column=0, sticky="nsew")

        # Column hints (top row: one Entry per column)
        self.col_hint_entries = []
        for c in range(GRID_SIZE):
            e = tk.Entry(area, width=6, justify="center", bg=BG_HINT, relief="solid", bd=1)
            e.insert(0, "")  # user types numbers like "3 2"
            e.grid(row=0, column=c+1, padx=(0,0), pady=(0,4))
            self.col_hint_entries.append(e)

        # Row hints (left column: one Entry per row)
        self.row_hint_entries = []
        for r in range(GRID_SIZE):
            e = tk.Entry(area, width=8, justify="right", bg=BG_HINT, relief="solid", bd=1)
            e.insert(0, "")
            e.grid(row=r+1, column=0, padx=(0,6), pady=(0,0))
            self.row_hint_entries.append(e)

        # Canvas for the main grid
        canvas_w = GRID_SIZE * CELL_SIZE
        canvas_h = GRID_SIZE * CELL_SIZE
        self.canvas = tk.Canvas(area, width=canvas_w, height=canvas_h, bg=BG_GRID, highlightthickness=0)
        self.canvas.grid(row=1, column=1, rowspan=GRID_SIZE, columnspan=GRID_SIZE)

        # Mouse bindings (primary, middle, secondary) + drag + release
        self.canvas.bind("<Button-1>", lambda e: self._on_press(e, STATE_FILLED, 1))
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Middle click (Button-2); add Shift-Left as a fallback for trackpads
        self.canvas.bind("<Button-2>", lambda e: self._on_press(e, STATE_MAYBE, 2))
        self.canvas.bind("<B2-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_release)
        self.canvas.bind("<Shift-Button-1>", lambda e: self._on_press(e, STATE_MAYBE, 2))
        self.canvas.bind("<Shift-B1-Motion>", self._on_drag)
        self.canvas.bind("<Shift-ButtonRelease-1>", self._on_release)

        # Right click (Button-3); add Control-Left as a fallback for macOS
        self.canvas.bind("<Button-3>", lambda e: self._on_press(e, STATE_X, 3))
        self.canvas.bind("<B3-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_release)
        self.canvas.bind("<Control-Button-1>", lambda e: self._on_press(e, STATE_X, 3))
        self.canvas.bind("<Control-B1-Motion>", self._on_drag)
        self.canvas.bind("<Control-ButtonRelease-1>", self._on_release)

    def _draw_grid(self):
        # Draw cell rectangles and gridlines
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

        # Thicker lines every 5th to visually break things up (optional)
        for i in range(GRID_SIZE + 1):
            w = 2 if i % 5 == 0 else 1
            # vertical
            self.canvas.create_line(i * CELL_SIZE, 0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, fill=LINE_COLOR, width=w)
            # horizontal
            self.canvas.create_line(0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, i * CELL_SIZE, fill=LINE_COLOR, width=w)

    def reset_board(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self._set_cell(r, c, STATE_EMPTY)

    def clear_hints(self):
        for e in self.row_hint_entries:
            e.delete(0, tk.END)
        for e in self.col_hint_entries:
            e.delete(0, tk.END)

    def _on_press(self, event, desired_state, button_id):
        cell = self._event_to_cell(event)
        if not cell:
            return
        r, c = cell
        current = self.grid_state[r][c]

        # Toggle behavior: if already that state, we erase on drag; else we paint that state
        if current == desired_state:
            self.drag_target_state = STATE_EMPTY
        else:
            self.drag_target_state = desired_state

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
        if self.grid_state[r][c] != self.drag_target_state:
            self._set_cell(r, c, self.drag_target_state)

    def _on_release(self, event):
        self.drag_active = False
        self.drag_button = None

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
            # Draw a small '?' or dot
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            self.canvas.create_text(cx, cy, text="?", fill=MAYBE_COLOR, font=("Segoe UI", 12, "bold"), tags=(tag,))

if __name__ == "__main__":
    PicrossApp().mainloop()
