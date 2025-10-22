"""Interactive Processing shape exporter.

This script provides a Tkinter GUI that lets users draw Processing 2D
primitives (line, rect, ellipse, triangle, arc) and custom polygon
shapes, and exports the equivalent Processing code for recreating the
drawing.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Tuple

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600


def _normalize_box(p1: Tuple[int, int], p2: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Return the top-left and bottom-right corners of a box defined by p1/p2."""

    x1, y1 = p1
    x2, y2 = p2
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return [(left, top), (right, bottom)]


def _box_center(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[float, float]:
    """Return the center point for the bounding box defined by two corners."""

    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def _arc_geometry(
    box_p1: Tuple[int, int],
    box_p2: Tuple[int, int],
    start_point: Tuple[int, int],
    end_point: Tuple[int, int],
) -> Tuple[float, float, float, float, Tuple[float, float]]:
    """Return arc geometry for canvas previews and Processing export.

    Returns a tuple of (start_rad, stop_rad, start_deg, extent_deg, center).
    """

    center = _box_center(box_p1, box_p2)
    cx, cy = center
    start_rad = math.atan2(start_point[1] - cy, start_point[0] - cx)
    end_rad = math.atan2(end_point[1] - cy, end_point[0] - cx)
    start_rad = (start_rad + math.tau) % math.tau
    end_rad = (end_rad + math.tau) % math.tau
    raw_extent = (end_rad - start_rad) % math.tau
    if math.isclose(raw_extent, 0.0) and (start_point != end_point):
        raw_extent = math.tau
    extent_deg = math.degrees(raw_extent)
    start_deg = math.degrees(start_rad)
    stop_rad = start_rad + raw_extent
    return start_rad, stop_rad, start_deg, extent_deg, center


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
            center_x, center_y = _box_center((x1, y1), (x2, y2))
            return (
                "  ellipse({0}, {1}, {2}, {3});".format(
                    int(round(center_x)),
                    int(round(center_y)),
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
        if self.shape_type == "Arc":
            box_p1, box_p2, start_point, end_point = self.points
            width = box_p2[0] - box_p1[0]
            height = box_p2[1] - box_p1[1]
            start_rad, stop_rad, _, _, center = _arc_geometry(
                box_p1, box_p2, start_point, end_point
            )
            cx, cy = center
            return (
                "  arc({0}, {1}, {2}, {3}, {4:.3f}, {5:.3f});".format(
                    int(round(cx)),
                    int(round(cy)),
                    int(round(width)),
                    int(round(height)),
                    start_rad,
                    stop_rad,
                )
            )
        if self.shape_type == "Custom Shape":
            vertices = [
                "    vertex({0}, {1});".format(
                    int(round(point[0])), int(round(point[1]))
                )
                for point in self.points
            ]
            return "\n".join([
                "  beginShape();",
                *vertices,
                "  endShape(CLOSE);",
            ])
        raise ValueError(f"Unsupported shape type: {self.shape_type}")


class ProcessingExporterApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Processing Shape Exporter")

        self.shapes: List[Shape] = []
        self.pending_points: List[Tuple[int, int]] = []
        self.current_preview_ids: List[int] = []

        self._build_ui()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self)
        controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Label(controls, text="Shape:").pack(side=tk.LEFT)
        self.shape_var = tk.StringVar(value="Line")
        self.shape_var.trace_add("write", self.on_shape_change)
        shape_menu = ttk.OptionMenu(
            controls,
            self.shape_var,
            self.shape_var.get(),
            "Line",
            "Rectangle",
            "Ellipse",
            "Triangle",
            "Arc",
            "Custom Shape",
        )
        shape_menu.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="Undo", command=self.undo_last).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Export", command=self.export_shapes).pack(side=tk.LEFT, padx=5)
        self.finish_button = ttk.Button(
            controls,
            text="Finish Shape",
            command=self.finish_custom_shape,
            state=tk.DISABLED,
        )
        self.finish_button.pack(side=tk.LEFT, padx=5)

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
        if shape == "Custom Shape":
            return None
        return {"Line": 2, "Rectangle": 2, "Ellipse": 2, "Triangle": 3, "Arc": 4}[shape]

    def on_canvas_click(self, event: tk.Event) -> None:
        shape = self.shape_var.get()
        self.pending_points.append((event.x, event.y))
        needed = self.required_points()

        if shape == "Custom Shape":
            if len(self.pending_points) >= 2:
                self.draw_preview(*self.pending_points)
            self.update_finish_button()
            return

        if needed is not None and len(self.pending_points) == needed:
            self.add_shape()
            self.pending_points.clear()
            self.clear_preview()
            self.update_finish_button()
        else:
            self.draw_preview(*self.pending_points)

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
        elif shape == "Arc":
            preview_points = self.pending_points + [(event.x, event.y)]
            self.draw_preview(*preview_points)
        elif shape == "Custom Shape":
            preview_points = self.pending_points + [(event.x, event.y)]
            self.draw_preview(*preview_points)

    def add_shape(
        self,
        shape_type: Optional[str] = None,
        points: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        shape_type = shape_type or self.shape_var.get()
        source_points = points if points is not None else self.pending_points
        points_copy = list(source_points)
        if shape_type in {"Rectangle", "Ellipse"}:
            points_copy = _normalize_box(points_copy[0], points_copy[1])
        elif shape_type == "Arc":
            box_p1, box_p2 = _normalize_box(points_copy[0], points_copy[1])
            points_copy = [box_p1, box_p2, points_copy[2], points_copy[3]]
        shape = Shape(shape_type, points_copy)
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
        elif shape.shape_type == "Arc":
            box_p1, box_p2, start_point, end_point = shape.points
            start_rad, _, _, extent_deg, _ = _arc_geometry(
                box_p1, box_p2, start_point, end_point
            )
            tk_start = (-math.degrees(start_rad)) % 360
            tk_extent = -extent_deg
            self.canvas.create_arc(
                box_p1[0],
                box_p1[1],
                box_p2[0],
                box_p2[1],
                start=tk_start,
                extent=tk_extent,
                style=tk.ARC,
                outline="black",
            )
        elif shape.shape_type == "Custom Shape":
            coords = [coord for point in shape.points for coord in point]
            self.canvas.create_polygon(*coords, outline="black", fill="")

    def draw_preview(self, *points: Tuple[int, int]) -> None:
        self.clear_preview()
        shape = self.shape_var.get()
        preview_items: List[int] = []
        if shape == "Line" and len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            preview_items.append(
                self.canvas.create_line(x1, y1, x2, y2, dash=(3, 3))
            )
        elif shape == "Rectangle" and len(points) == 2:
            p1, p2 = _normalize_box(points[0], points[1])
            preview_items.append(
                self.canvas.create_rectangle(p1[0], p1[1], p2[0], p2[1], dash=(3, 3))
            )
        elif shape == "Ellipse" and len(points) == 2:
            p1, p2 = _normalize_box(points[0], points[1])
            preview_items.append(
                self.canvas.create_oval(p1[0], p1[1], p2[0], p2[1], dash=(3, 3))
            )
        elif shape == "Triangle" and len(points) == 3:
            coords = [coord for point in points for coord in point]
            preview_items.append(
                self.canvas.create_polygon(
                    *coords, dash=(3, 3), outline="black", fill=""
                )
            )
        elif shape == "Arc" and len(points) >= 2:
            box_p1, box_p2 = _normalize_box(points[0], points[1])
            preview_items.append(
                self.canvas.create_oval(
                    box_p1[0], box_p1[1], box_p2[0], box_p2[1], dash=(3, 3)
                )
            )
            center = _box_center(box_p1, box_p2)
            cx, cy = center
            if len(points) >= 3:
                start_point = points[2]
                preview_items.append(
                    self.canvas.create_line(
                        cx, cy, start_point[0], start_point[1], dash=(3, 3)
                    )
                )
            if len(points) == 4:
                start_rad, _, _, extent_deg, _ = _arc_geometry(
                    box_p1, box_p2, points[2], points[3]
                )
                tk_start = (-math.degrees(start_rad)) % 360
                tk_extent = -extent_deg
                preview_items.append(
                    self.canvas.create_arc(
                        box_p1[0],
                        box_p1[1],
                        box_p2[0],
                        box_p2[1],
                        start=tk_start,
                        extent=tk_extent,
                        style=tk.ARC,
                        dash=(3, 3),
                    )
                )
                end_point = points[3]
                preview_items.append(
                    self.canvas.create_line(
                        cx, cy, end_point[0], end_point[1], dash=(3, 3)
                    )
                )
        elif shape == "Custom Shape" and len(points) >= 2:
            coords = [coord for point in points for coord in point]
            preview_items.append(
                self.canvas.create_line(*coords, dash=(3, 3))
            )
        self.current_preview_ids = preview_items

    def clear_preview(self) -> None:
        for item_id in self.current_preview_ids:
            self.canvas.delete(item_id)
        self.current_preview_ids = []

    def undo_last(self) -> None:
        if not self.shapes:
            messagebox.showinfo("Undo", "No shapes to remove.")
            return
        self.shapes.pop()
        self.redraw_canvas()
        self.update_finish_button()

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

    def finish_custom_shape(self) -> None:
        if self.shape_var.get() != "Custom Shape":
            return
        if len(self.pending_points) < 3:
            messagebox.showinfo("Custom Shape", "Add at least three points before finishing.")
            return
        points = list(self.pending_points)
        self.add_shape("Custom Shape", points)
        self.pending_points.clear()
        self.clear_preview()
        self.update_finish_button()

    def update_finish_button(self) -> None:
        if self.shape_var.get() == "Custom Shape" and len(self.pending_points) >= 3:
            self.finish_button.state(["!disabled"])
        else:
            self.finish_button.state(["disabled"])

    def on_shape_change(self, *_: object) -> None:
        self.pending_points.clear()
        self.clear_preview()
        self.update_finish_button()


def main() -> None:
    app = ProcessingExporterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
