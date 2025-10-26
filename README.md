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

1. (Optional) Enter a custom width/height in the **Canvas size** inputs and
   press **Apply** to resize the drawing area.
2. Select the shape type from the drop-down menu (choose **Eraser** to remove
   existing shapes).
3. Click on the canvas to define the required points:
   - **Line**: two clicks (start, end).
   - **Rectangle/Ellipse**: click-and-release (top-left, bottom-right).
   - **Ellipse export**: the exported code now uses the ellipse center and size
     to match Processing's coordinate system.
   - **Triangle**: three clicks (each vertex).
   - **Arc**: four clicks – two for the bounding box corners and two more for
     the start and end directions (relative to the arc's center).
   - **Custom Shape**: choose the segment type (straight vertex, quadratic
     curve, or bezier curve), click to define the required control/end points,
     and press **Finish Shape** once at least three anchors are added to close
     the shape.
4. Press **Undo** to remove the most recent shape, or use **Eraser** to click a
   specific shape on the canvas and delete it.
5. Press **Export** to copy the Processing code for the drawing to your
   clipboard and display it in the text box.

The exported code defines a basic Processing sketch with `size()`, `stroke()`,
`noFill()`, and `background()` calls plus the shape commands required to
reproduce the drawing.
