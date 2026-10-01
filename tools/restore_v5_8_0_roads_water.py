from pathlib import Path
import ast

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
MARKER = "# MB_ROADS_WATER_V5_8_0"

if MARKER in s:
    print("5.8.0 road/river renderer already present")
    raise SystemExit(0)

NETWORK_METHOD = """    def draw_network_layer(self, kind, rect=None):
        # MB_ROADS_WATER_V5_8_0
        from PIL import Image, ImageDraw
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        if rect is None:
            rect = self._visible_world_rect()
        paths = []
        for obj in self.objects:
            if obj.get('kind') != kind or not self._bbox_visible(obj, rect):
                continue
            points = obj.get('points', [])
            if len(points) < 2:
                continue
            screen = [self.world_to_screen(x, y) for x, y in points]
            scale = float(getattr(self, 'scale', 1.0))
            obj_scale = max(.1, min(5.0, float(obj.get('obj_scale', 1.0))))
            base = max(1.0, float(obj.get('width', 25)) * obj_scale * scale)
            paths.append((screen, base))
        if not paths:
            return

        edge_mask = Image.new('L', (w, h), 0)
        surface_mask = Image.new('L', (w, h), 0)
        edge_draw = ImageDraw.Draw(edge_mask)
        surface_draw = ImageDraw.Draw(surface_mask)
        if kind == 'river':
            edge_color, surface_color = '#4b4238', '#4fa8a2'
            edge_extra = 28.0
        else:
            edge_color, surface_color = '#514437', '#b7a080'
            edge_extra = 10.0

        for points, base in paths:
            coords = [(int(round(x)), int(round(y))) for x, y in points]
            edge_width = max(3, int(round(base + edge_extra * self.scale)))
            surface_width = max(2, int(round(base)))
            edge_draw.line(coords, fill=255, width=edge_width, joint='curve')
            surface_draw.line(coords, fill=255, width=surface_width, joint='curve')
            r1 = edge_width // 2
            r2 = surface_width // 2
            for x, y in (coords[0], coords[-1]):
                edge_draw.ellipse((x-r1, y-r1, x+r1, y+r1), fill=255)
                surface_draw.ellipse((x-r2, y-r2, x+r2, y+r2), fill=255)

        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        layer.paste(edge_color, (0, 0, w, h), edge_mask)
        layer.paste(surface_color, (0, 0, w, h), surface_mask)

        if kind == 'river' and self.scale > .18:
            highlight = Image.new('L', (w, h), 0)
            hd = ImageDraw.Draw(highlight)
            for points, base in paths:
                coords = [(int(round(x)), int(round(y))) for x, y in points]
                hd.line(
                    coords,
                    fill=110,
                    width=max(1, int(round(min(2.0, self.scale * 1.4)))),
                    joint='curve'
                )
            from PIL import ImageChops
            highlight = ImageChops.multiply(highlight, surface_mask)
            layer.paste('#83c7bd', (0, 0, w, h), highlight)

        photo = ImageTk.PhotoImage(layer)
        if not hasattr(self, '_network_layer_photos'):
            self._network_layer_photos = {}
        self._network_layer_photos[kind] = photo
        self.canvas.create_image(
            0, 0, image=photo, anchor='nw',
            tags=('network_layer', kind)
        )

"""

tree = ast.parse(s, filename=str(p))
app = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App"), None)
if app is None:
    raise RuntimeError("App class not found")

draw_line = next((n for n in app.body if isinstance(n, ast.FunctionDef) and n.name == "draw_line_obj"), None)
if draw_line is None:
    raise RuntimeError("draw_line_obj() not found")

# Insert the v5.8 network union method immediately before draw_line_obj().
lines = s.splitlines(keepends=True)
insert_index = draw_line.lineno - 1
lines.insert(insert_index, NETWORK_METHOD)
s = ''.join(lines)

# Reparse after insertion and locate the actual drawing function produced by
# the 5.9 performance patch. We preserve every statement except road/river
# per-segment loops.
tree = ast.parse(s, filename=str(p))
app = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App")
render_fn = next((n for n in app.body if isinstance(n, ast.FunctionDef) and n.name == "_render_now"), None)
if render_fn is None:
    render_fn = next((n for n in app.body if isinstance(n, ast.FunctionDef) and n.name == "render"), None)
if render_fn is None:
    raise RuntimeError("Neither _render_now() nor render() found")

def contains_draw_line(node):
    return any(
        isinstance(x, ast.Call)
        and isinstance(x.func, ast.Attribute)
        and x.func.attr == "draw_line_obj"
        for x in ast.walk(node)
    )

all_loops = [
    n for n in ast.walk(render_fn)
    if isinstance(n, ast.For) and contains_draw_line(n)
]
if not all_loops:
    raise RuntimeError("No active river/road drawing loop found anywhere in the live renderer")

# Keep only outermost matching loops, so a nested helper loop is not replaced twice.
targets=[]
for node in sorted(all_loops,key=lambda n:(n.lineno,-n.end_lineno)):
    if not any(parent.lineno <= node.lineno and parent.end_lineno >= node.end_lineno for parent in targets):
        targets.append(node)

source_lines = s.splitlines(keepends=True)
first = min(targets,key=lambda n:n.lineno)
replacement_indent = source_lines[first.lineno - 1]
indent = replacement_indent[:len(replacement_indent)-len(replacement_indent.lstrip())]
replacement = (
    indent + "# MB_ROADS_WATER_V5_8_0: one union mask per network; no segment stacking.\n"
    + indent + "self.draw_network_layer('river',rect)\n"
    + indent + "self.draw_network_layer('road',rect)\n"
)

for node in sorted(targets,key=lambda n:n.lineno,reverse=True):
    aa=node.lineno-1
    bb=node.end_lineno
    if node is first:
        source_lines[aa:bb]=[replacement]
    else:
        del source_lines[aa:bb]
s=''.join(source_lines)

# Old circular-junction/underlay calls are incompatible with the v5.8 union renderer.
for call in (
    "        self.draw_road_network_underlay()\\n",
    "        self.draw_road_junctions()\\n",
    "        self.draw_junctions()\\n",
):
    s = s.replace(call, "")

compile(s, str(p), "exec")
p.write_text(s, encoding="utf-8")
print(f"PASS: restored v5.8.0 road/river union renderer; replaced {len(targets)} old line loops")
