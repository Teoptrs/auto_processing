# auto_processing

Interactive utility for drawing Processing 2D primitives via a Tkinter GUI and
exporting the equivalent Processing sketch code.

## Requirements

- Python 3.8+
- Tkinter (bundled with most Python distributions)

## Usage

```bash
python processing_exporter.py
```

1. Select the shape type from the drop-down menu.
2. Click on the canvas to define the required points:
   - **Line**: two clicks (start, end).
   - **Rectangle/Ellipse**: click-and-release (top-left, bottom-right).
   - **Ellipse export**: the exported code now uses the ellipse center and size
     to match Processing's coordinate system.
   - **Triangle**: three clicks (each vertex).
   - **Arc**: four clicks – two for the bounding box corners and two more for
     the start and end directions (relative to the arc's center).
   - **Custom Shape**: click to add as many vertices as you like, then press
     **Finish Shape** (enabled after three points) to close the polygon.
3. Press **Undo** to remove the most recent shape.
4. Press **Export** to copy the Processing code for the drawing to your
   clipboard and display it in the text box.

The exported code defines a basic Processing sketch with `size()`, `stroke()`,
`noFill()`, and `background()` calls plus the shape commands required to
reproduce the drawing.
