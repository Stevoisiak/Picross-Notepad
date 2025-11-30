import tkinter as tk
from tkinter import ttk
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal

# --- Configuration ---

@dataclass
class GameConfig:
    CELL_SIZE: int = 28
    DIMENSIONS: int = 16
    BLOCK_INTERVAL: int = 4  # Thicker lines every N cells
    HINTS_PER_SIDE: int = 4
    
    # Colors
    COLOR_GRID_LINE: str = "#A9A9A9"
    COLOR_BG_HINT: str = "#F0F0F0"
    COLOR_BG_GRID: str = "#FFFFFF"
    COLOR_CELL_FILLED: str = "#111111"
    COLOR_CELL_X: str = "#D22222"
    COLOR_CELL_MAYBE: str = "#666666"
    
    # Fonts & Dimensions
    FONT_HINT: Tuple[str, int, str] = ("Calibri", 11, "bold")
    TOP_HINT_HEIGHT: int = 22 * HINTS_PER_SIDE
    LEFT_HINT_WIDTH: int = 22 * HINTS_PER_SIDE
    LINE_WIDTH_THIN: int = 1
    LINE_WIDTH_THICK: int = 2

CFG = GameConfig()

class CellState(IntEnum):
    EMPTY = 0
    FILLED = 1
    X = 2
    MAYBE = 3

# --- Custom Widgets ---

class PicrossGrid(tk.Canvas):
    """
    Handles the drawing of the main game grid and mouse interactions.
    """
    def __init__(self, master, **kwargs):
        width = CFG.DIMENSIONS * CFG.CELL_SIZE
        height = CFG.DIMENSIONS * CFG.CELL_SIZE
        super().__init__(master, width=width, height=height, 
                         bg=CFG.COLOR_BG_GRID, highlightthickness=0, **kwargs)
        
        # Internal State
        self.grid_state = [[CellState.EMPTY for _ in range(CFG.DIMENSIONS)] 
                           for _ in range(CFG.DIMENSIONS)]
        self.rect_ids = [[None for _ in range(CFG.DIMENSIONS)] 
                         for _ in range(CFG.DIMENSIONS)]
        self.mark_tags = [[f"mark_{r}_{c}" for c in range(CFG.DIMENSIONS)] 
                          for r in range(CFG.DIMENSIONS)]
        
        # Dragging State
        self._is_dragging = False
        self._drag_target_state = CellState.EMPTY
        self._drag_start_cell: Optional[Tuple[int, int]] = None
        self._drag_axis: Optional[Literal['row', 'col']] = None

        self._init_draw()
        self._bind_events()

    def _init_draw(self):
        """Draws the initial grid lines and empty cell rectangles."""
        # 1. Draw cell backgrounds
        for r in range(CFG.DIMENSIONS):
            for c in range(CFG.DIMENSIONS):
                x0, y0 = c * CFG.CELL_SIZE, r * CFG.CELL_SIZE
                x1, y1 = x0 + CFG.CELL_SIZE, y0 + CFG.CELL_SIZE
                rid = self.create_rectangle(x0, y0, x1, y1, fill=CFG.COLOR_BG_GRID, width=0)
                self.rect_ids[r][c] = rid

        # 2. Draw grid lines
        total_size = CFG.DIMENSIONS * CFG.CELL_SIZE
        for i in range(1, CFG.DIMENSIONS):
            width = CFG.LINE_WIDTH_THICK if i % CFG.BLOCK_INTERVAL == 0 else CFG.LINE_WIDTH_THIN
            pos = i * CFG.CELL_SIZE
            self.create_line(pos, 0, pos, total_size, fill=CFG.COLOR_GRID_LINE, width=width)
            self.create_line(0, pos, total_size, pos, fill=CFG.COLOR_GRID_LINE, width=width)

        # 3. Outer Border
        inset = CFG.LINE_WIDTH_THICK / 2
        self.create_rectangle(inset, inset, total_size - inset, total_size - inset, 
                              outline=CFG.COLOR_GRID_LINE, width=CFG.LINE_WIDTH_THICK)

    def _bind_events(self):
        # Left Click: Fill
        self.bind("<Button-1>", lambda e: self._on_press(e, CellState.FILLED))
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._end_drag)
        
        # Middle / Shift+Left: Maybe
        self.bind("<Button-2>", lambda e: self._on_press(e, CellState.MAYBE))
        self.bind("<B2-Motion>", self._on_drag)
        self.bind("<ButtonRelease-2>", self._end_drag)
        self.bind("<Shift-Button-1>", lambda e: self._on_press(e, CellState.MAYBE))
        self.bind("<Shift-B1-Motion>", self._on_drag)
        self.bind("<Shift-ButtonRelease-1>", self._end_drag)
        
        # Right / Ctrl+Left: X
        self.bind("<Button-3>", lambda e: self._on_press(e, CellState.X))
        self.bind("<B3-Motion>", self._on_drag)
        self.bind("<ButtonRelease-3>", self._end_drag)
        self.bind("<Control-Button-1>", lambda e: self._on_press(e, CellState.X))
        self.bind("<Control-B1-Motion>", self._on_drag)
        self.bind("<Control-ButtonRelease-1>", self._end_drag)

        # Mouse 5: Erase
        self.bind("<Button-5>", lambda e: self._on_press(e, CellState.EMPTY))
        self.bind("<B5-Motion>", self._on_drag)
        self.bind("<ButtonRelease-5>", self._end_drag)

    def reset_grid(self):
        for r in range(CFG.DIMENSIONS):
            for c in range(CFG.DIMENSIONS):
                self._update_cell(r, c, CellState.EMPTY)

    def _get_cell_coords(self, event) -> Optional[Tuple[int, int]]:
        c = event.x // CFG.CELL_SIZE
        r = event.y // CFG.CELL_SIZE
        if 0 <= r < CFG.DIMENSIONS and 0 <= c < CFG.DIMENSIONS:
            return int(r), int(c)
        return None

    def _update_cell(self, r, c, state):
        if self.grid_state[r][c] == state:
            return
            
        self.grid_state[r][c] = state
        rid = self.rect_ids[r][c]
        tag = self.mark_tags[r][c]
        
        # Cleanup old marks
        self.delete(tag)
        
        # Update Background
        fill = CFG.COLOR_CELL_FILLED if state == CellState.FILLED else CFG.COLOR_BG_GRID
        self.itemconfig(rid, fill=fill)

        # Draw Overlay (X or ?)
        x0, y0 = c * CFG.CELL_SIZE, r * CFG.CELL_SIZE
        x1, y1 = x0 + CFG.CELL_SIZE, y0 + CFG.CELL_SIZE
        
        if state == CellState.X:
            pad = 6
            self.create_line(x0+pad, y0+pad, x1-pad, y1-pad, fill=CFG.COLOR_CELL_X, width=2, tags=tag)
            self.create_line(x0+pad, y1-pad, x1-pad, y0+pad, fill=CFG.COLOR_CELL_X, width=2, tags=tag)
        elif state == CellState.MAYBE:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            self.create_text(cx, cy, text="?", fill=CFG.COLOR_CELL_MAYBE, 
                             font=("Segoe UI", 12, "bold"), tags=tag)

    def _on_press(self, event, desired_state):
        self.focus_set()
        cell = self._get_cell_coords(event)
        if not cell: return

        r, c = cell
        current_state = self.grid_state[r][c]
        
        # Toggle logic
        if current_state == desired_state:
            self._drag_target_state = CellState.EMPTY
        else:
            self._drag_target_state = desired_state

        self._is_dragging = True
        self._drag_start_cell = (r, c)
        self._drag_axis = None
        
        self._update_cell(r, c, self._drag_target_state)

    def _on_drag(self, event):
        if not self._is_dragging: return
        
        # Get mouse position clamped to grid
        c = max(0, min(CFG.DIMENSIONS - 1, event.x // CFG.CELL_SIZE))
        r = max(0, min(CFG.DIMENSIONS - 1, event.y // CFG.CELL_SIZE))
        
        start_r, start_c = self._drag_start_cell
        
        # Determine Lock Axis if not set
        if self._drag_axis is None:
            if r != start_r and c == start_c:
                self._drag_axis = 'col'
            elif c != start_c and r == start_r:
                self._drag_axis = 'row'
            elif r != start_r and c != start_c:
                # Diagonal move: pick dominant axis
                if abs(r - start_r) > abs(c - start_c):
                    self._drag_axis = 'col'
                else:
                    self._drag_axis = 'row'

        # Apply Lock
        target_r, target_c = r, c
        if self._drag_axis == 'row':
            target_r = start_r 
        elif self._drag_axis == 'col':
            target_c = start_c
            
        # Paint
        self._update_cell(target_r, target_c, self._drag_target_state)

    def _end_drag(self, event):
        self._is_dragging = False
        self._drag_start_cell = None
        self._drag_axis = None


# --- Main Application ---

class PicrossApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Picross {CFG.DIMENSIONS}×{CFG.DIMENSIONS}")
        self.resizable(False, False)
        
        self.row_hints: List[List[tk.Entry]] = []
        self.col_hints: List[List[tk.Entry]] = []
        
        self._build_layout()
        self._bind_navigation()

    def _build_layout(self):
        # Root container
        root = ttk.Frame(self, padding=8)
        root.grid(sticky="nsew")

        # 1. Toolbar
        toolbar = ttk.Frame(root)
        toolbar.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Button(toolbar, text="Reset Board", command=self.reset_board).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Clear Hints", command=self.clear_hints).pack(side="left", padx=2)
        ttk.Label(toolbar, text="  Left: Fill • Right: X • Mid: Maybe • Drag to paint").pack(side="left", padx=8)

        # 2. Game Area Container
        area = ttk.Frame(root)
        area.grid(row=1, column=0)

        # --- Top Hints (Column Hints) ---
        # The canvas draws the lines behind the hint boxes.
        # CRITICAL: columnspan=16 ensures the canvas stretches across all hint columns.
        grid_pixel_width = CFG.DIMENSIONS * CFG.CELL_SIZE
        
        self.col_sep_canvas = tk.Canvas(
            area, 
            width=grid_pixel_width, 
            height=CFG.TOP_HINT_HEIGHT, 
            bg=CFG.COLOR_BG_HINT, 
            highlightthickness=0
        )
        self.col_sep_canvas.grid(row=0, column=1, columnspan=CFG.DIMENSIONS, sticky="ew")
        
        self._draw_separators(self.col_sep_canvas, grid_pixel_width, CFG.TOP_HINT_HEIGHT, vertical=True)

        # Place the Entry widgets over the canvas
        for c in range(CFG.DIMENSIONS):
            # Frame for one column of hints
            frame = tk.Frame(area, bg=CFG.COLOR_BG_HINT)
            frame.grid(row=0, column=c+1, sticky="s", padx=0, pady=0)
            
            col_entries = []
            for i in range(CFG.HINTS_PER_SIDE):
                e = self._create_hint_entry(frame, width=3)
                e.pack(side="top", ipady=0)
                col_entries.append(e)
            self.col_hints.append(col_entries)

        # --- Left Hints (Row Hints) ---
        grid_pixel_height = CFG.DIMENSIONS * CFG.CELL_SIZE

        # CRITICAL: rowspan=16 ensures the canvas stretches down all hint rows.
        self.row_sep_canvas = tk.Canvas(
            area,
            width=CFG.LEFT_HINT_WIDTH,
            height=grid_pixel_height,
            bg=CFG.COLOR_BG_HINT,
            highlightthickness=0
        )
        self.row_sep_canvas.grid(row=1, column=0, rowspan=CFG.DIMENSIONS, sticky="ns")

        # Place the Entry widgets to the left
        for r in range(CFG.DIMENSIONS):
            # Frame for one row of hints
            frame = tk.Frame(area, bg=CFG.COLOR_BG_HINT)
            frame.grid(row=r+1, column=0, sticky="e", padx=0, pady=0)
            
            row_entries = []
            for i in range(CFG.HINTS_PER_SIDE):
                # Using minsize ensures alignment even if entry is empty/small
                frame.grid_columnconfigure(i, minsize=22) 
                e = self._create_hint_entry(frame, width=1)
                e.grid(row=0, column=i, sticky="ew")
                row_entries.append(e)
            self.row_hints.append(row_entries)
        
        # Draw left separators (needs idle update to get width if dynamic, but fixed width is safer here)
        self._draw_separators(self.row_sep_canvas, CFG.LEFT_HINT_WIDTH, grid_pixel_height, vertical=False)

        # --- Main Grid ---
        # CRITICAL: This must align with rows=1..16 and cols=1..16 of the hint frames.
        # We use rowspan and columnspan so it occupies the exact same grid cells as the hint frames adjacent to it.
        self.grid_canvas = PicrossGrid(area)
        self.grid_canvas.grid(row=1, column=1, rowspan=CFG.DIMENSIONS, columnspan=CFG.DIMENSIONS)

    def _create_hint_entry(self, parent, width):
        return tk.Entry(parent, width=width, justify="center", 
                        bg=CFG.COLOR_BG_HINT, relief="flat", bd=0,
                        font=CFG.FONT_HINT)

    def _draw_separators(self, canvas, width, height, vertical=True):
        canvas.delete("all")
        inset = CFG.LINE_WIDTH_THICK / 2
        
        # Outer Borders
        if vertical:
            canvas.create_line(inset, 0, inset, height, fill=CFG.COLOR_GRID_LINE, width=CFG.LINE_WIDTH_THICK)
            canvas.create_line(width-inset, 0, width-inset, height, fill=CFG.COLOR_GRID_LINE, width=CFG.LINE_WIDTH_THICK)
        else:
            canvas.create_line(0, inset, width, inset, fill=CFG.COLOR_GRID_LINE, width=CFG.LINE_WIDTH_THICK)
            canvas.create_line(0, height-inset, width, height-inset, fill=CFG.COLOR_GRID_LINE, width=CFG.LINE_WIDTH_THICK)

        # Internal Lines
        step = CFG.CELL_SIZE
        for i in range(1, CFG.DIMENSIONS):
            line_w = CFG.LINE_WIDTH_THICK if i % CFG.BLOCK_INTERVAL == 0 else CFG.LINE_WIDTH_THIN
            pos = i * step
            
            if vertical:
                canvas.create_line(pos, 0, pos, height, fill=CFG.COLOR_GRID_LINE, width=line_w)
            else:
                canvas.create_line(0, pos, width, pos, fill=CFG.COLOR_GRID_LINE, width=line_w)

    def _bind_navigation(self):
        """Binds arrow keys to navigate the hint grids."""
        def move_focus(entry_list, r, c, dr, dc):
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(entry_list) and 0 <= nc < len(entry_list[0]):
                target = entry_list[nr][nc]
                target.focus_set()
                target.icursor(tk.END)
                target.selection_range(0, tk.END)
                return "break"

        # Row Hints (Left)
        for r in range(CFG.DIMENSIONS):
            for i in range(CFG.HINTS_PER_SIDE):
                e = self.row_hints[r][i]
                e.bind("<Up>",    lambda _, r=r, i=i: move_focus(self.row_hints, r, i, -1, 0))
                e.bind("<Down>",  lambda _, r=r, i=i: move_focus(self.row_hints, r, i, 1, 0))
                e.bind("<Left>",  lambda _, r=r, i=i: move_focus(self.row_hints, r, i, 0, -1))
                e.bind("<Right>", lambda _, r=r, i=i: move_focus(self.row_hints, r, i, 0, 1))

        # Col Hints (Top)
        for c in range(CFG.DIMENSIONS):
            for i in range(CFG.HINTS_PER_SIDE):
                e = self.col_hints[c][i]
                e.bind("<Up>",    lambda _, c=c, i=i: move_focus(self.col_hints, c, i, 0, -1))
                e.bind("<Down>",  lambda _, c=c, i=i: move_focus(self.col_hints, c, i, 0, 1))
                e.bind("<Left>",  lambda _, c=c, i=i: move_focus(self.col_hints, c, i, -1, 0))
                e.bind("<Right>", lambda _, c=c, i=i: move_focus(self.col_hints, c, i, 1, 0))

    def reset_board(self):
        self.grid_canvas.reset_grid()

    def clear_hints(self):
        for row in self.row_hints:
            for e in row: e.delete(0, tk.END)
        for col in self.col_hints:
            for e in col: e.delete(0, tk.END)

if __name__ == "__main__":
    PicrossApp().mainloop()