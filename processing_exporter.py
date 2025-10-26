"""Interactive Processing shape exporter.

This script provides a Tkinter GUI that lets users draw Processing 2D
primitives (line, rect, ellipse, triangle, arc) and custom polygon
shapes, and exports the equivalent Processing code for recreating the
drawing.
"""

import math
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional, Sequence, Tuple

DEFAULT_CANVAS_WIDTH = 800
DEFAULT_CANVAS_HEIGHT = 600


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

    def __init__(
        self,
        shape_type: str,
        points: List[Tuple[float, float]],
        commands: Optional[List[Tuple[str, Sequence[Tuple[float, float]]]]] = None,
    ) -> None:
        self.shape_type = shape_type
        self.points = points
        self.commands = commands

    def to_processing(
        self, coord_formatter: Optional[Callable[[float, str], str]] = None
    ) -> str:
        """Return Processing code for this shape."""
        if coord_formatter is None:
            coord_formatter = lambda value, axis: str(int(round(value)))
        if self.shape_type == "Line":
            (x1, y1), (x2, y2) = self.points
            return (
                f"  line({coord_formatter(x1, 'x')}, {coord_formatter(y1, 'y')}, "
                f"{coord_formatter(x2, 'x')}, {coord_formatter(y2, 'y')});"
            )
        if self.shape_type == "Rectangle":
            (x1, y1), (x2, y2) = self.points
            width = x2 - x1
            height = y2 - y1
            return (
                "  rect({0}, {1}, {2}, {3});".format(
                    coord_formatter(x1, "x"),
                    coord_formatter(y1, "y"),
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
                    coord_formatter(center_x, "x"),
                    coord_formatter(center_y, "y"),
                    int(round(width)),
                    int(round(height)),
                )
            )
        if self.shape_type == "Triangle":
            coords: List[str] = []
            for x, y in self.points:
                coords.append(coord_formatter(x, "x"))
                coords.append(coord_formatter(y, "y"))
            return f"  triangle({', '.join(coords)});"
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
                    coord_formatter(cx, "x"),
                    coord_formatter(cy, "y"),
                    int(round(width)),
                    int(round(height)),
                    start_rad,
                    stop_rad,
                )
            )
        if self.shape_type == "Custom Shape":
            if self.commands:
                lines = ["  beginShape();"]
                for command, command_points in self.commands:
                    if command == "vertex":
                        (x, y) = command_points[0]
                        lines.append(
                            "    vertex({0}, {1});".format(
                                coord_formatter(x, "x"),
                                coord_formatter(y, "y"),
                            )
                        )
                    elif command == "quadraticVertex":
                        control, end_point = command_points
                        lines.append(
                            "    quadraticVertex({0}, {1}, {2}, {3});".format(
                                coord_formatter(control[0], "x"),
                                coord_formatter(control[1], "y"),
                                coord_formatter(end_point[0], "x"),
                                coord_formatter(end_point[1], "y"),
                            )
                        )
                    elif command == "bezierVertex":
                        control1, control2, end_point = command_points
                        lines.append(
                            "    bezierVertex({0}, {1}, {2}, {3}, {4}, {5});".format(
                                coord_formatter(control1[0], "x"),
                                coord_formatter(control1[1], "y"),
                                coord_formatter(control2[0], "x"),
                                coord_formatter(control2[1], "y"),
                                coord_formatter(end_point[0], "x"),
                                coord_formatter(end_point[1], "y"),
                            )
                        )
                    else:
                        raise ValueError(f"Unsupported custom command: {command}")
                lines.append("  endShape(CLOSE);")
                return "\n".join(lines)
            vertices = [
                "    vertex({0}, {1});".format(
                    coord_formatter(point[0], "x"),
                    coord_formatter(point[1], "y"),
                )
                for point in self.points
            ]
            return "\n".join(
                [
                    "  beginShape();",
                    *vertices,
                    "  endShape(CLOSE);",
                ]
            )
        raise ValueError(f"Unsupported shape type: {self.shape_type}")


def _sample_custom_shape(
    commands: List[Tuple[str, Sequence[Tuple[float, float]]]],
    *,
    steps_per_curve: int = 20,
    closed: bool = False,
) -> List[Tuple[float, float]]:
    """Return an approximated polyline for custom shape commands."""

    if not commands:
        return []

    first_command, *remaining = commands
    if first_command[0] != "vertex":
        raise ValueError("Custom shapes must start with a vertex command")

    points: List[Tuple[float, float]] = [first_command[1][0]]
    current_point = first_command[1][0]

    for command, command_points in remaining:
        if command == "vertex":
            end_point = command_points[0]
            points.append(end_point)
            current_point = end_point
        elif command == "quadraticVertex":
            control, end_point = command_points
            for i in range(1, steps_per_curve + 1):
                t = i / steps_per_curve
                one_minus_t = 1 - t
                x = (
                    one_minus_t * one_minus_t * current_point[0]
                    + 2 * one_minus_t * t * control[0]
                    + t * t * end_point[0]
                )
                y = (
                    one_minus_t * one_minus_t * current_point[1]
                    + 2 * one_minus_t * t * control[1]
                    + t * t * end_point[1]
                )
                points.append((x, y))
            current_point = end_point
        elif command == "bezierVertex":
            control1, control2, end_point = command_points
            for i in range(1, steps_per_curve + 1):
                t = i / steps_per_curve
                one_minus_t = 1 - t
                x = (
                    one_minus_t**3 * current_point[0]
                    + 3 * one_minus_t * one_minus_t * t * control1[0]
                    + 3 * one_minus_t * t * t * control2[0]
                    + t**3 * end_point[0]
                )
                y = (
                    one_minus_t**3 * current_point[1]
                    + 3 * one_minus_t * one_minus_t * t * control1[1]
                    + 3 * one_minus_t * t * t * control2[1]
                    + t**3 * end_point[1]
                )
                points.append((x, y))
            current_point = end_point
        else:
            raise ValueError(f"Unsupported custom command: {command}")

    if closed and points and points[-1] != points[0]:
        points.append(points[0])
    return points


class ProcessingExporterApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Processing Shape Exporter")

        self.shapes: List[Shape] = []
        self.pending_points: List[Tuple[int, int]] = []
        self.current_preview_ids: List[int] = []
        self.grid_item_ids: List[int] = []
        self.shape_items: List[List[int]] = []

        self.canvas_width = DEFAULT_CANVAS_WIDTH
        self.canvas_height = DEFAULT_CANVAS_HEIGHT
        self.canvas_width_var = tk.StringVar(value=str(DEFAULT_CANVAS_WIDTH))
        self.canvas_height_var = tk.StringVar(value=str(DEFAULT_CANVAS_HEIGHT))

        self.custom_shape_commands_pending: List[
            Tuple[str, List[Tuple[int, int]]]
        ] = []
        self.custom_segment_buffer: List[Tuple[int, int]] = []

        self.relative_mode_var = tk.BooleanVar(value=False)
        self.relative_x_var = tk.StringVar(value="shapex")
        self.relative_y_var = tk.StringVar(value="shapey")
        self.grid_enabled_var = tk.BooleanVar(value=False)
        self.grid_size_var = tk.IntVar(value=40)
        self.export_method_var = tk.BooleanVar(value=False)
        self.method_name_var = tk.StringVar(value="drawShapes")

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
            "Eraser",
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

        self.custom_controls_frame = ttk.Frame(self)
        ttk.Label(self.custom_controls_frame, text="Segment type:").pack(side=tk.LEFT)
        self.custom_segment_type_var = tk.StringVar(value="Vertex")
        self.custom_segment_menu = ttk.OptionMenu(
            self.custom_controls_frame,
            self.custom_segment_type_var,
            "Vertex",
            "Vertex",
            "Quadratic Curve",
            "Bezier Curve",
        )
        self.custom_segment_menu.pack(side=tk.LEFT, padx=5)
        self.custom_segment_type_var.trace_add("write", self.on_custom_segment_change)
        self.custom_controls_visible = False

        size_frame = ttk.Frame(self)
        size_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(size_frame, text="Canvas size:").pack(side=tk.LEFT)
        self.canvas_width_entry = ttk.Entry(
            size_frame, textvariable=self.canvas_width_var, width=6
        )
        self.canvas_width_entry.pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(size_frame, text="×").pack(side=tk.LEFT)
        self.canvas_height_entry = ttk.Entry(
            size_frame, textvariable=self.canvas_height_var, width=6
        )
        self.canvas_height_entry.pack(side=tk.LEFT, padx=(2, 5))
        ttk.Button(size_frame, text="Apply", command=self.apply_canvas_size).pack(
            side=tk.LEFT
        )

        export_frame = ttk.Frame(self)
        export_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))
        self.method_toggle = ttk.Checkbutton(
            export_frame,
            text="Export as method",
            variable=self.export_method_var,
            command=self.update_method_entry,
        )
        self.method_toggle.pack(side=tk.LEFT, padx=5)
        ttk.Label(export_frame, text="Method name:").pack(side=tk.LEFT)
        self.method_name_entry = ttk.Entry(
            export_frame, textvariable=self.method_name_var, width=15
        )
        self.method_name_entry.pack(side=tk.LEFT, padx=(2, 5))

        relative_frame = ttk.Frame(self)
        relative_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))
        self.relative_toggle = ttk.Checkbutton(
            relative_frame,
            text="Use relative offsets",
            variable=self.relative_mode_var,
            command=self.update_relative_entries,
        )
        self.relative_toggle.pack(side=tk.LEFT, padx=5)
        ttk.Label(relative_frame, text="X var:").pack(side=tk.LEFT)
        self.relative_x_entry = ttk.Entry(
            relative_frame, textvariable=self.relative_x_var, width=10
        )
        self.relative_x_entry.pack(side=tk.LEFT, padx=(2, 5))
        ttk.Label(relative_frame, text="Y var:").pack(side=tk.LEFT)
        self.relative_y_entry = ttk.Entry(
            relative_frame, textvariable=self.relative_y_var, width=10
        )
        self.relative_y_entry.pack(side=tk.LEFT, padx=(2, 5))

        grid_frame = ttk.Frame(self)
        grid_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))
        self.grid_toggle = ttk.Checkbutton(
            grid_frame,
            text="Enable grid snapping",
            variable=self.grid_enabled_var,
            command=self.on_grid_toggle,
        )
        self.grid_toggle.pack(side=tk.LEFT, padx=5)
        self.grid_size_label = ttk.Label(
            grid_frame, text=f"Grid: {self.grid_size_var.get()}px"
        )
        self.grid_size_label.pack(side=tk.LEFT, padx=(10, 5))
        self.grid_size_scale = ttk.Scale(
            grid_frame,
            from_=10,
            to=200,
            orient=tk.HORIZONTAL,
            command=self.on_grid_size_change,
        )
        self.grid_size_scale.set(self.grid_size_var.get())
        self.grid_size_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

        self.output_text = tk.Text(self, height=10, width=80)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.output_text.insert(tk.END, "Processing code will appear here after exporting.\n")
        self.output_text.configure(state=tk.DISABLED)

        self.update_relative_entries()
        self.update_method_entry()
        self.draw_grid()
        self.update_custom_controls()

    def required_points(self) -> Optional[int]:
        shape = self.shape_var.get()
        if shape == "Eraser":
            return 0
        if shape == "Custom Shape":
            return None
        return {"Line": 2, "Rectangle": 2, "Ellipse": 2, "Triangle": 3, "Arc": 4}[shape]

    def on_canvas_click(self, event: tk.Event) -> None:
        shape = self.shape_var.get()
        snapped_point = self._apply_grid(event.x, event.y)
        if shape == "Eraser":
            self.erase_shape_at(snapped_point)
            return
        if shape == "Custom Shape":
            self.handle_custom_shape_click(snapped_point)
            self.update_finish_button()
            return

        self.pending_points.append(snapped_point)
        needed = self.required_points()

        if needed is not None and len(self.pending_points) == needed:
            self.add_shape()
            self.pending_points.clear()
            self.clear_preview()
            self.update_finish_button()
        else:
            self.draw_preview(*self.pending_points)

    def on_canvas_motion(self, event: tk.Event) -> None:
        snapped_point = self._apply_grid(event.x, event.y)
        shape = self.shape_var.get()
        if shape == "Eraser":
            return
        if shape == "Custom Shape":
            if self.custom_shape_commands_pending:
                self.draw_custom_shape_preview(hover_point=snapped_point)
            return
        if not self.pending_points:
            return
        if shape in {"Line", "Rectangle", "Ellipse"} and len(self.pending_points) == 1:
            self.draw_preview(self.pending_points[0], snapped_point)
        elif shape == "Triangle" and len(self.pending_points) == 2:
            self.draw_preview(
                self.pending_points[0],
                self.pending_points[1],
                snapped_point,
            )
        elif shape == "Arc":
            preview_points = self.pending_points + [snapped_point]
            self.draw_preview(*preview_points)

    def add_shape(
        self,
        shape_type: Optional[str] = None,
        points: Optional[List[Tuple[int, int]]] = None,
        commands: Optional[List[Tuple[str, Sequence[Tuple[int, int]]]]] = None,
    ) -> None:
        shape_type = shape_type or self.shape_var.get()
        source_points = points if points is not None else self.pending_points
        points_copy = list(source_points)
        if shape_type in {"Rectangle", "Ellipse"}:
            points_copy = _normalize_box(points_copy[0], points_copy[1])
        elif shape_type == "Arc":
            box_p1, box_p2 = _normalize_box(points_copy[0], points_copy[1])
            points_copy = [box_p1, box_p2, points_copy[2], points_copy[3]]
        if shape_type == "Custom Shape" and commands is not None:
            shape = Shape(shape_type, points_copy, commands=list(commands))
        else:
            shape = Shape(shape_type, points_copy)
        self.shapes.append(shape)
        self.shape_items.append(self.draw_shape(shape))

    def draw_shape(self, shape: Shape) -> List[int]:
        item_ids: List[int] = []
        if shape.shape_type == "Line":
            (x1, y1), (x2, y2) = shape.points
            item_ids.append(self.canvas.create_line(x1, y1, x2, y2, fill="black"))
        elif shape.shape_type == "Rectangle":
            (x1, y1), (x2, y2) = shape.points
            item_ids.append(
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="black")
            )
        elif shape.shape_type == "Ellipse":
            (x1, y1), (x2, y2) = shape.points
            item_ids.append(self.canvas.create_oval(x1, y1, x2, y2, outline="black"))
        elif shape.shape_type == "Triangle":
            coords = [coord for point in shape.points for coord in point]
            item_ids.append(
                self.canvas.create_polygon(*coords, outline="black", fill="")
            )
        elif shape.shape_type == "Arc":
            box_p1, box_p2, start_point, end_point = shape.points
            start_rad, _, _, extent_deg, _ = _arc_geometry(
                box_p1, box_p2, start_point, end_point
            )
            # Convert to Tkinter angles (degrees CCW from 3 o'clock); invert for screen Y-down.
            tk_start = (-math.degrees(start_rad)) % 360
            tk_extent = -extent_deg
            item_ids.append(
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
            )
        elif shape.shape_type == "Custom Shape":
            if shape.commands:
                sampled = _sample_custom_shape(list(shape.commands), closed=True)
                if len(sampled) >= 2:
                    coords = [coord for point in sampled for coord in point]
                    item_ids.append(self.canvas.create_line(*coords, fill="black"))
            else:
                coords = [coord for point in shape.points for coord in point]
                item_ids.append(
                    self.canvas.create_polygon(*coords, outline="black", fill="")
                )
        return item_ids

    def draw_preview(self, *points: Tuple[int, int]) -> None:
        self.clear_preview()
        shape = self.shape_var.get()
        preview_items: List[int] = []
        if shape == "Line" and len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            preview_items.append(self.canvas.create_line(x1, y1, x2, y2, dash=(3, 3)))
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
                self.canvas.create_polygon(*coords, dash=(3, 3), outline="black", fill="")
            )
        elif shape == "Arc" and len(points) >= 2:
            box_p1, box_p2 = _normalize_box(points[0], points[1])
            preview_items.append(
                self.canvas.create_oval(box_p1[0], box_p1[1], box_p2[0], box_p2[1], dash=(3, 3))
            )
            center = _box_center(box_p1, box_p2)
            cx, cy = center
            if len(points) >= 3:
                start_point = points[2]
                preview_items.append(
                    self.canvas.create_line(cx, cy, start_point[0], start_point[1], dash=(3, 3))
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
                    self.canvas.create_line(cx, cy, end_point[0], end_point[1], dash=(3, 3))
                )
        self.current_preview_ids = preview_items

    def clear_preview(self) -> None:
        for item_id in self.current_preview_ids:
            self.canvas.delete(item_id)
        self.current_preview_ids = []

    def handle_custom_shape_click(self, point: Tuple[int, int]) -> None:
        if not self.custom_shape_commands_pending:
            self.custom_shape_commands_pending.append(("vertex", [point]))
            self.draw_custom_shape_preview()
            return

        segment = self.custom_segment_type_var.get()
        if segment == "Vertex":
            if self.custom_segment_buffer:
                self.custom_segment_buffer = []
            self.custom_shape_commands_pending.append(("vertex", [point]))
        elif segment == "Quadratic Curve":
            self.custom_segment_buffer.append(point)
            if len(self.custom_segment_buffer) == 2:
                control, end_point = self.custom_segment_buffer
                self.custom_shape_commands_pending.append(
                    ("quadraticVertex", [control, end_point])
                )
                self.custom_segment_buffer = []
        elif segment == "Bezier Curve":
            self.custom_segment_buffer.append(point)
            if len(self.custom_segment_buffer) == 3:
                control1, control2, end_point = self.custom_segment_buffer
                self.custom_shape_commands_pending.append(
                    ("bezierVertex", [control1, control2, end_point])
                )
                self.custom_segment_buffer = []
        else:
            raise ValueError(f"Unsupported segment type: {segment}")

        self.draw_custom_shape_preview()

    def draw_custom_shape_preview(
        self, *, hover_point: Optional[Tuple[int, int]] = None
    ) -> None:
        self.clear_preview()
        preview_items: List[int] = []
        commands = self.custom_shape_commands_pending
        last_anchor: Optional[Tuple[int, int]] = None
        if commands:
            sampled = _sample_custom_shape(commands, closed=False)
            if len(sampled) >= 2:
                coords = [coord for point in sampled for coord in point]
                preview_items.append(
                    self.canvas.create_line(*coords, dash=(3, 3), fill="black")
                )
            last_anchor = self._custom_shape_last_anchor(commands)

        if last_anchor is not None:
            connector_points: List[Tuple[int, int]] = [last_anchor]
            connector_points.extend(self.custom_segment_buffer)
            if hover_point is not None:
                connector_points.append(hover_point)
            if len(connector_points) >= 2:
                for start, end in zip(connector_points, connector_points[1:]):
                    preview_items.append(
                        self.canvas.create_line(
                            start[0],
                            start[1],
                            end[0],
                            end[1],
                            dash=(3, 3),
                            fill="black",
                        )
                    )

        self.current_preview_ids = preview_items

    def undo_last(self) -> None:
        if not self.shapes:
            messagebox.showinfo("Undo", "No shapes to remove.")
            return
        self.shapes.pop()
        if self.shape_items:
            self.shape_items.pop()
        self.redraw_canvas()
        self.update_finish_button()

    def erase_shape_at(self, point: Tuple[int, int]) -> None:
        if not self.shapes:
            return
        x, y = point
        overlapping = set(self.canvas.find_overlapping(x, y, x, y))
        if not overlapping:
            return
        for index in range(len(self.shape_items) - 1, -1, -1):
            items = self.shape_items[index]
            if any(item in overlapping for item in items):
                del self.shapes[index]
                del self.shape_items[index]
                self.redraw_canvas()
                self.update_finish_button()
                return

    def redraw_canvas(self) -> None:
        self.canvas.delete("all")
        self.canvas.configure(width=self.canvas_width, height=self.canvas_height)
        self.grid_item_ids = []
        self.draw_grid()
        self.shape_items = []
        for shape in self.shapes:
            self.shape_items.append(self.draw_shape(shape))

    def export_shapes(self) -> None:
        if not self.shapes:
            messagebox.showinfo("Export", "Draw some shapes before exporting.")
            return

        if self.export_method_var.get():
            method_name = self.method_name_var.get().strip() or "drawShapes"
            parameter_list = self._method_parameter_list()
            lines = [f"void {method_name}{parameter_list} {{"]
            lines.extend(
                shape.to_processing(coord_formatter=self.format_coord)
                for shape in self.shapes
            )
            lines.append("}")
        else:
            lines = [
                "void setup() {",
                f"  size({int(self.canvas_width)}, {int(self.canvas_height)});",
                "  stroke(0);",
                "  noFill();",
                "}",
                "",
                "void draw() {",
                "  background(255);",
            ]
            lines.extend(
                shape.to_processing(coord_formatter=self.format_coord)
                for shape in self.shapes
            )
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
        if self.custom_segment_buffer:
            messagebox.showinfo(
                "Custom Shape", "Complete the current segment before finishing."
            )
            return
        if self._custom_shape_anchor_count() < 3:
            messagebox.showinfo(
                "Custom Shape", "Add at least three points before finishing."
            )
            return
        commands = list(self.custom_shape_commands_pending)
        sampled = _sample_custom_shape(commands, closed=True)
        points = [(int(round(x)), int(round(y))) for x, y in sampled]
        self.add_shape("Custom Shape", points, commands=commands)
        self.reset_custom_shape_state()
        self.custom_segment_type_var.set("Vertex")
        self.clear_preview()
        self.update_finish_button()

    def update_finish_button(self) -> None:
        if self.shape_var.get() == "Custom Shape":
            anchors = self._custom_shape_anchor_count()
            if anchors >= 3 and not self.custom_segment_buffer:
                self.finish_button.state(["!disabled"])
                return
        self.finish_button.state(["disabled"])

    def on_shape_change(self, *_: object) -> None:
        self.pending_points.clear()
        self.clear_preview()
        self.reset_custom_shape_state()
        self.update_custom_controls()
        self.custom_segment_type_var.set("Vertex")
        self.update_finish_button()

    def update_relative_entries(self) -> None:
        if self.relative_mode_var.get():
            self.relative_x_entry.state(["!disabled"])
            self.relative_y_entry.state(["!disabled"])
        else:
            self.relative_x_entry.state(["disabled"])
            self.relative_y_entry.state(["disabled"])

    def update_method_entry(self) -> None:
        if self.export_method_var.get():
            self.method_name_entry.state(["!disabled"])
        else:
            self.method_name_entry.state(["disabled"])

    def update_custom_controls(self) -> None:
        if self.shape_var.get() == "Custom Shape":
            if not self.custom_controls_visible:
                self.custom_controls_frame.pack(
                    side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5)
                )
                self.custom_controls_visible = True
        else:
            if self.custom_controls_visible:
                self.custom_controls_frame.pack_forget()
                self.custom_controls_visible = False

    def apply_canvas_size(self) -> None:
        try:
            width = int(self.canvas_width_var.get())
            height = int(self.canvas_height_var.get())
        except ValueError:
            messagebox.showerror(
                "Canvas Size", "Width and height must be integer values."
            )
            return
        width = max(100, width)
        height = max(100, height)
        if width == self.canvas_width and height == self.canvas_height:
            return
        self.canvas_width = width
        self.canvas_height = height
        self.redraw_canvas()

    def reset_custom_shape_state(self) -> None:
        self.custom_shape_commands_pending = []
        self.custom_segment_buffer = []

    def on_custom_segment_change(self, *_: object) -> None:
        if self.custom_segment_buffer:
            self.custom_segment_buffer = []
            if self.shape_var.get() == "Custom Shape":
                self.draw_custom_shape_preview()
        self.update_finish_button()

    def _custom_shape_last_anchor(
        self, commands: List[Tuple[str, Sequence[Tuple[int, int]]]]
    ) -> Optional[Tuple[int, int]]:
        if not commands:
            return None
        command, points = commands[-1]
        if command == "vertex":
            return points[0]
        return points[-1]

    def _custom_shape_anchor_count(self) -> int:
        if not self.custom_shape_commands_pending:
            return 0
        count = 0
        for command, points in self.custom_shape_commands_pending:
            if command == "vertex":
                count += 1
            elif command in {"quadraticVertex", "bezierVertex"}:
                count += 1
        return count

    def on_grid_toggle(self) -> None:
        if self.grid_enabled_var.get():
            if self.shape_var.get() == "Custom Shape":
                self.custom_shape_commands_pending = [
                    (command, [self._apply_grid(x, y) for x, y in command_points])
                    for command, command_points in self.custom_shape_commands_pending
                ]
                self.custom_segment_buffer = [
                    self._apply_grid(x, y) for x, y in self.custom_segment_buffer
                ]
            else:
                self.pending_points = [
                    self._apply_grid(x, y) for x, y in self.pending_points
                ]
        self.draw_grid()
        self.clear_preview()
        if self.shape_var.get() == "Custom Shape":
            self.draw_custom_shape_preview()
        elif self.pending_points:
            self.draw_preview(*self.pending_points)

    def on_grid_size_change(self, value: str) -> None:
        size = max(5, int(float(value)))
        self.grid_size_var.set(size)
        self.grid_size_label.configure(text=f"Grid: {size}px")
        if self.grid_enabled_var.get():
            self.draw_grid()
            if self.shape_var.get() == "Custom Shape":
                self.draw_custom_shape_preview()

    def draw_grid(self) -> None:
        for item in self.grid_item_ids:
            self.canvas.delete(item)
        self.grid_item_ids = []
        if not self.grid_enabled_var.get():
            return
        size = max(5, self.grid_size_var.get())
        for x in range(0, self.canvas_width + 1, size):
            self.grid_item_ids.append(
                self.canvas.create_line(
                    x, 0, x, self.canvas_height, fill="#e0e0e0", tags="grid"
                )
            )
        for y in range(0, self.canvas_height + 1, size):
            self.grid_item_ids.append(
                self.canvas.create_line(
                    0, y, self.canvas_width, y, fill="#e0e0e0", tags="grid"
                )
            )
        self.canvas.tag_lower("grid")

    def _apply_grid(self, x: int, y: int) -> Tuple[int, int]:
        if not self.grid_enabled_var.get():
            return x, y
        size = max(5, self.grid_size_var.get())
        snapped_x = int(round(x / size) * size)
        snapped_y = int(round(y / size) * size)
        return snapped_x, snapped_y

    def format_coord(self, value: float, axis: str) -> str:
        rounded = int(round(value))
        if not self.relative_mode_var.get():
            return str(rounded)
        var_name = self._relative_var_name(axis)
        if rounded == 0:
            return var_name
        if rounded > 0:
            return f"{var_name} + {rounded}"
        return f"{var_name} - {abs(rounded)}"

    def _relative_var_name(self, axis: str) -> str:
        if axis == "x":
            return self.relative_x_var.get().strip() or "shapex"
        if axis == "y":
            return self.relative_y_var.get().strip() or "shapey"
        raise ValueError(f"Unsupported axis: {axis}")

    def _method_parameter_list(self) -> str:
        if not self.relative_mode_var.get():
            return "()"
        x_var = self._relative_var_name("x")
        y_var = self._relative_var_name("y")
        return f"(float {x_var}, float {y_var})"


def main() -> None:
    app = ProcessingExporterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
