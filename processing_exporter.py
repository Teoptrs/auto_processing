"""Interactive Processing shape exporter.

This script provides a Tkinter GUI that lets users draw basic Processing
2D primitives (line, rect, ellipse, triangle) and exports the equivalent
Processing code for recreating the drawing.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600


class Shape:
    """Represents a drawn shape."""

    def __init__(self, shape_type: str, points: List[Tuple[float, float]]):
        self.shape_type = shape_type
        self.points = points

    def to_processing(self) -> str:
        """Return Processing code for this shape."""
        if self.shape_type == "Line":
            (x1, y1), (x2, y2) = self.points
            return f"  line({int(round(x1))}, {int(round(y1))}, {int(round(x2))}, {int(round(y2))});"
        if self.shape_type == "Rectangle":
            (x1, y1), (x2, y2) = self.points
            width = x2 - x1
            height = y2 - y1
            return (
                "  rect({0}, {1}, {2}, {3});".format(
                    int(round(x1)),
                    int(round(y1)),
                    int(round(width)),
                    int(round(height)),
                )
            )
        if self.shape_type == "Ellipse":
            (x1, y1), (x2, y2) = self.points
            width = x2 - x1
            height = y2 - y1
            return (
                "  ellipse({0}, {1}, {2}, {3});".format(
                    int(round(x1)),
                    int(round(y1)),
                    int(round(width)),
                    int(round(height)),
                )
            )
        if self.shape_type == "Triangle":
            return "  triangle({0}, {1}, {2}, {3}, {4}, {5});".format(
                int(round(self.points[0][0])),
                int(round(self.points[0][1])),
                int(round(self.points[1][0])),
                int(round(self.points[1][1])),
                int(round(self.points[2][0])),
                int(round(self.points[2][1])),
            )
        raise ValueError(f"Unsupported shape type: {self.shape_type}")


class ProcessingExporterApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Processing Shape Exporter")

        self.shapes: List[Shape] = []
        self.pending_points: List[Tuple[int, int]] = []
        self.current_preview = None

        self._build_ui()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self)
        controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(controls, text="Shape:").pack(side=tk.LEFT)
        self.shape_var = tk.StringVar(value="Line")
        shape_menu = ttk.OptionMenu(
            controls,
            self.shape_var,
            self.shape_var.get(),
            "Line",
            "Rectangle",
            "Ellipse",
            "Triangle",
        )
        shape_menu.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Undo", command=self.undo_last).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Export", command=self.export_shapes).pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

        self.output_text = tk.Text(self, height=10, width=80)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.output_text.insert(tk.END, "Processing code will appear here after exporting.\n")
        self.output_text.configure(state=tk.DISABLED)

    def required_points(self) -> int:
        shape = self.shape_var.get()
        return {"Line": 2, "Rectangle": 2, "Ellipse": 2, "Triangle": 3}[shape]

    def on_canvas_click(self, event: tk.Event) -> None:
        self.pending_points.append((event.x, event.y))
        needed = self.required_points()
        if len(self.pending_points) == needed:
            self.add_shape()
            self.pending_points.clear()
            self.clear_preview()

    def on_canvas_motion(self, event: tk.Event) -> None:
        if not self.pending_points:
            return
        shape = self.shape_var.get()
        if shape in {"Line", "Rectangle", "Ellipse"} and len(self.pending_points) == 1:
            self.draw_preview(self.pending_points[0], (event.x, event.y))
        elif shape == "Triangle" and len(self.pending_points) == 2:
            self.draw_preview(
                self.pending_points[0],
                self.pending_points[1],
                (event.x, event.y),
            )

    def add_shape(self) -> None:
        shape_type = self.shape_var.get()
        points = list(self.pending_points)
        if shape_type in {"Rectangle", "Ellipse"}:
            points = self._normalize_box(points[0], points[1])
        shape = Shape(shape_type, points)
        self.shapes.append(shape)
        self.draw_shape(shape)

    def draw_shape(self, shape: Shape) -> None:
        if shape.shape_type == "Line":
            (x1, y1), (x2, y2) = shape.points
            self.canvas.create_line(x1, y1, x2, y2, fill="black")
        elif shape.shape_type == "Rectangle":
            (x1, y1), (x2, y2) = shape.points
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="black")
        elif shape.shape_type == "Ellipse":
            (x1, y1), (x2, y2) = shape.points
            self.canvas.create_oval(x1, y1, x2, y2, outline="black")
        elif shape.shape_type == "Triangle":
            coords = [coord for point in shape.points for coord in point]
            self.canvas.create_polygon(*coords, outline="black", fill="")

    def draw_preview(self, *points: Tuple[int, int]) -> None:
        self.clear_preview()
        shape = self.shape_var.get()
        if shape == "Line" and len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            self.current_preview = self.canvas.create_line(x1, y1, x2, y2, dash=(3, 3))
        elif shape == "Rectangle" and len(points) == 2:
            p1, p2 = self._normalize_box(points[0], points[1])
            self.current_preview = self.canvas.create_rectangle(
                p1[0], p1[1], p2[0], p2[1], dash=(3, 3)
            )
        elif shape == "Ellipse" and len(points) == 2:
            p1, p2 = self._normalize_box(points[0], points[1])
            self.current_preview = self.canvas.create_oval(
                p1[0], p1[1], p2[0], p2[1], dash=(3, 3)
            )
        elif shape == "Triangle" and len(points) == 3:
            coords = [coord for point in points for coord in point]
            self.current_preview = self.canvas.create_polygon(*coords, dash=(3, 3), outline="black", fill="")

    def clear_preview(self) -> None:
        if self.current_preview is not None:
            self.canvas.delete(self.current_preview)
            self.current_preview = None

    def undo_last(self) -> None:
        if not self.shapes:
            messagebox.showinfo("Undo", "No shapes to remove.")
            return
        self.shapes.pop()
        self.redraw_canvas()

    def redraw_canvas(self) -> None:
        self.canvas.delete("all")
        for shape in self.shapes:
            self.draw_shape(shape)

    def export_shapes(self) -> None:
        if not self.shapes:
            messagebox.showinfo("Export", "Draw some shapes before exporting.")
            return

        lines = [
            "void setup() {",
            f"  size({CANVAS_WIDTH}, {CANVAS_HEIGHT});",
            "  stroke(0);",
            "  noFill();",
            "}",
            "",
            "void draw() {",
            "  background(255);",
        ]
        lines.extend(shape.to_processing() for shape in self.shapes)
        lines.append("}")

        code = "\n".join(lines)
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, code)
        self.output_text.configure(state=tk.DISABLED)

        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("Export", "Processing code copied to clipboard.")

    @staticmethod
    def _normalize_box(p1: Tuple[int, int], p2: Tuple[int, int]) -> List[Tuple[int, int]]:
        x1, y1 = p1
        x2, y2 = p2
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        return [(left, top), (right, bottom)]


def main() -> None:
    app = ProcessingExporterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
