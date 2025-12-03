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
    FONT_HINT: Tuple[str, int, str] = ("Calibri", 15, "bold")
    TOP_HINT_HEIGHT: int = 22
    LEFT_HINT_WIDTH: int = 20

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
        self.mark_tags = [[f"mark_{row}_{col}" for col in range(CFG.DIMENSIONS)] 
                          for row in range(CFG.DIMENSIONS)]
        
        # Dragging State
        self._is_dragging = False
        self._drag_target_state = CellState.EMPTY
        self._drag_start_cell: Optional[Tuple[int, int]] = None
        self._drag_axis: Optional[Literal['row', 'col']] = None

        self._init_draw()
        self._bind_events()

    def _init_draw(self):
        """Draws the initial grid lines and empty cell rectangles."""
        # 1. Cell backgrounds
        for row in range(CFG.DIMENSIONS):
            for col in range(CFG.DIMENSIONS):
                x0, y0 = col * CFG.CELL_SIZE, row * CFG.CELL_SIZE
                x1, y1 = x0 + CFG.CELL_SIZE, y0 + CFG.CELL_SIZE
                rid = self.create_rectangle(x0, y0, x1, y1, fill=CFG.COLOR_BG_GRID, width=0)
                self.rect_ids[row][col] = rid

        # 2. Grid lines
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
        for row in range(CFG.DIMENSIONS):
            for col in range(CFG.DIMENSIONS):
                self._update_cell(row, col, CellState.EMPTY)

    def _get_cell_coords(self, event) -> Optional[Tuple[int, int]]:
        col = event.x // CFG.CELL_SIZE
        row = event.y // CFG.CELL_SIZE
        if 0 <= row < CFG.DIMENSIONS and 0 <= col < CFG.DIMENSIONS:
            return int(row), int(col)
        return None

    def _update_cell(self, row, col, state):
        if self.grid_state[row][col] == state:
            return
            
        self.grid_state[row][col] = state
        rid = self.rect_ids[row][col]
        tag = self.mark_tags[row][col]
        
        # Cleanup old marks
        self.delete(tag)
        
        # Update Background
        fill = CFG.COLOR_CELL_FILLED if state == CellState.FILLED else CFG.COLOR_BG_GRID
        self.itemconfig(rid, fill=fill)

        # Draw Overlay (X or ?)
        x0, y0 = col * CFG.CELL_SIZE, row * CFG.CELL_SIZE
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
        cell = self._get_cell_coords(event)
        if not cell: return

        row, col = cell
        current_state = self.grid_state[row][col]
        
        # Toggle logic
        if current_state == desired_state:
            self._drag_target_state = CellState.EMPTY
        else:
            self._drag_target_state = desired_state

        self._is_dragging = True
        self._drag_start_cell = (row, col)
        self._drag_axis = None
        
        self._update_cell(row, col, self._drag_target_state)

    def _on_drag(self, event):
        if not self._is_dragging: return
        
        # Get mouse position clamped to grid
        col = max(0, min(CFG.DIMENSIONS - 1, event.x // CFG.CELL_SIZE))
        row = max(0, min(CFG.DIMENSIONS - 1, event.y // CFG.CELL_SIZE))
        
        start_row, start_col = self._drag_start_cell
        
        # Determine Lock Axis if not set
        if self._drag_axis is None:
            if row != start_row and col == start_col:
                self._drag_axis = 'col'
            elif col != start_col and row == start_row:
                self._drag_axis = 'row'
            elif row != start_row and col != start_col:
                # Diagonal move: pick dominant axis
                if abs(row - start_row) > abs(col - start_col):
                    self._drag_axis = 'col'
                else:
                    self._drag_axis = 'row'

        # Apply Lock
        target_row, target_col = row, col
        if self._drag_axis == 'row':
            target_row = start_row 
        elif self._drag_axis == 'col':
            target_col = start_col
            
        # Paint
        self._update_cell(target_row, target_col, self._drag_target_state)

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
        self._bind_focus_clear()

    
    def validate_and_color(self, P, widget_id):
        # Only allow single character
        if len(P) > 1:
            return False

        # Update color based on hint number
        colors = {
            "1": "#AC0005",  # Red
            "2": "#B15008",  # Orange
            "3": "#D6AB2D",  # Yellow
            "4": "#5ABB00",  # Green
            "5": "#13338E",  # Blue
            "6": "#4E1391",  # Purple
            "7": "#7FAEE8",  # White
            "8": "black",  # Black
        }
        widget = self.nametowidget(widget_id)
        widget.config(fg=colors.get(P, "black"))
        return True


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
        top_w = CFG.DIMENSIONS * CFG.CELL_SIZE
        top_h = CFG.HINTS_PER_SIDE * CFG.TOP_HINT_HEIGHT
        
        self.col_sep_canvas = tk.Canvas(
            area, 
            width=top_w, 
            height=top_h, 
            bg=CFG.COLOR_BG_HINT, 
            highlightthickness=0
        )
        self.col_sep_canvas.grid(row=0, column=1, sticky="nsew")
        
        self._draw_separators(self.col_sep_canvas, top_w, top_h, vertical=True)
        self.col_sep_canvas.bind("<Configure>", 
            lambda e: self._draw_separators(self.col_sep_canvas, e.width, e.height, vertical=True))

        # Place the Entry widgets over the canvas
        vcmd = self.register(self.validate_and_color)
        for col in range(CFG.DIMENSIONS):
            # Frame for one column of hints
            col_entries = []
            for i in range(CFG.HINTS_PER_SIDE):
                x = col * CFG.CELL_SIZE + CFG.CELL_SIZE / 2
                y = i * CFG.TOP_HINT_HEIGHT + CFG.TOP_HINT_HEIGHT / 2
                e = tk.Entry(self.col_sep_canvas, justify="center", 
                             bg=CFG.COLOR_BG_HINT, relief="flat", bd=0,
                             font=CFG.FONT_HINT)
                e.config(validate="key", validatecommand=(vcmd, "%P", str(e)))
                self.col_sep_canvas.create_window(x, y, 
                                                  width=CFG.CELL_SIZE - 4, 
                                                  height=CFG.TOP_HINT_HEIGHT - 4, 
                                                  window=e)
                col_entries.append(e)
            self.col_hints.append(col_entries)

        # --- Left Hints (Row Hints) ---
        left_w = CFG.HINTS_PER_SIDE * CFG.LEFT_HINT_WIDTH
        left_h = CFG.DIMENSIONS * CFG.CELL_SIZE
        
        self.row_sep_canvas = tk.Canvas(
            area,
            width=left_w,
            height=left_h, 
            bg=CFG.COLOR_BG_HINT,
            highlightthickness=0
        )
        self.row_sep_canvas.grid(row=1, column=0, sticky="nsew")
        
        self._draw_separators(self.row_sep_canvas, left_w, left_h, vertical=False)
        self.row_sep_canvas.bind("<Configure>", 
            lambda e: self._draw_separators(self.row_sep_canvas, e.width, e.height, vertical=False))

        for row in range(CFG.DIMENSIONS):
            row_entries = []
            for i in range(CFG.HINTS_PER_SIDE):
                x = i * CFG.LEFT_HINT_WIDTH + CFG.LEFT_HINT_WIDTH / 2
                y = row * CFG.CELL_SIZE + CFG.CELL_SIZE / 2
                
                e = tk.Entry(self.row_sep_canvas, justify="center", 
                             bg=CFG.COLOR_BG_HINT, relief="flat", bd=0,
                             font=CFG.FONT_HINT)
                e.config(validate="key", validatecommand=(vcmd, "%P", str(e)))
                self.row_sep_canvas.create_window(x, y, 
                                                  width=CFG.LEFT_HINT_WIDTH - 4, 
                                                  height=CFG.CELL_SIZE - 4, 
                                                  window=e)
                row_entries.append(e)
            self.row_hints.append(row_entries)
        
        # --- Main Grid ---
        self.grid_canvas = PicrossGrid(area)
        self.grid_canvas.grid(row=1, column=1)

    def _draw_separators(self, canvas, width, height, vertical=True):
        """
        Draws separation lines on the canvas.
        vertical=True (Top Hints): Draws ONLY vertical lines (separating columns).
        vertical=False (Left Hints): Draws ONLY horizontal lines (separating rows).
        """
        canvas.delete("lines")
        step = CFG.CELL_SIZE
        tags = ("lines",)

        # Loop 0 to DIMENSIONS (inclusive) to draw start edge, internal lines, and end edge.
        for i in range(0, CFG.DIMENSIONS + 1):
            # Thick lines every BLOCK_INTERVAL, and at edges (0, 16)
            line_w = CFG.LINE_WIDTH_THICK if i % CFG.BLOCK_INTERVAL == 0 else CFG.LINE_WIDTH_THIN
            pos = i * step

            # Offset edges to prevent clipping
            # If line is at 0, shift right by half width.
            # If line is at max width, shift left by half width.
            if i == 0:
                pos += line_w / 2
            elif i == CFG.DIMENSIONS:
                pos -= line_w / 2
            
            if vertical:
                # Top Hints: Vertical lines only
                # pos is x-coordinate. Draw from y=0 to y=height.
                canvas.create_line(pos, 0, pos, height, fill=CFG.COLOR_GRID_LINE, width=line_w, tags=tags)
            else:
                # Left Hints: Horizontal lines only
                # pos is y-coordinate. Draw from x=0 to x=width.
                canvas.create_line(0, pos, width, pos, fill=CFG.COLOR_GRID_LINE, width=line_w, tags=tags)

    def _bind_navigation(self):
        """Binds arrow keys to navigate the hint grids."""
        def move_focus(entry_list, row, col, dr, dc):
            nr, nc = row + dr, col + dc
            if 0 <= nr < len(entry_list) and 0 <= nc < len(entry_list[0]):
                target = entry_list[nr][nc]
                target.focus_set()
                target.icursor(tk.END)
                target.selection_range(0, tk.END)
                return "break"

        # Row Hints (Left)
        for row in range(CFG.DIMENSIONS):
            for i in range(CFG.HINTS_PER_SIDE):
                e = self.row_hints[row][i]
                e.bind("<Up>",    lambda _, row=row, i=i: move_focus(self.row_hints, row, i, -1, 0))
                e.bind("<Down>",  lambda _, row=row, i=i: move_focus(self.row_hints, row, i, 1, 0))
                e.bind("<Left>",  lambda _, row=row, i=i: move_focus(self.row_hints, row, i, 0, -1))
                e.bind("<Right>", lambda _, row=row, i=i: move_focus(self.row_hints, row, i, 0, 1))

        # Col Hints (Top)
        for col in range(CFG.DIMENSIONS):
            for i in range(CFG.HINTS_PER_SIDE):
                e = self.col_hints[col][i]
                e.bind("<Up>",    lambda _, col=col, i=i: move_focus(self.col_hints, col, i, 0, -1))
                e.bind("<Down>",  lambda _, col=col, i=i: move_focus(self.col_hints, col, i, 0, 1))
                e.bind("<Left>",  lambda _, col=col, i=i: move_focus(self.col_hints, col, i, -1, 0))
                e.bind("<Right>", lambda _, col=col, i=i: move_focus(self.col_hints, col, i, 1, 0))

    def _bind_focus_clear(self):
        # Clicking anywhere on the grid or root clears hint focus
        self.bind_all("<Button-1>", self._clear_hint_focus, add="+")
        
    def _clear_hint_focus(self, event):
        widget = event.widget
        # If clicked widget is NOT an Entry, remove focus from hint entries
        if not isinstance(widget, tk.Entry):
            self.grid_canvas.focus_set()

    def reset_board(self):
        self.grid_canvas.reset_grid()

    def clear_hints(self):
        for row in self.row_hints:
            for e in row: e.delete(0, tk.END)
        for col in self.col_hints:
            for e in col: e.delete(0, tk.END)

if __name__ == "__main__":
    PicrossApp().mainloop()