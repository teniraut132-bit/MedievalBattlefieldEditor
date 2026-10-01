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

# Reparse after insertion and replace the per-segment renderer with a no-op.
# The v5.8.0 appearance is produced by draw_network_layer(), so individual
# draw_line_obj() calls must not paint additional outlines on top of the union.
tree = ast.parse(s, filename=str(p))
app = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App"), None)
if app is None:
    raise RuntimeError("App class not found after network renderer insertion")
draw_line = next((n for n in app.body if isinstance(n, ast.FunctionDef) and n.name == "draw_line_obj"), None)
if draw_line is None:
    raise RuntimeError("draw_line_obj() not found after network renderer insertion")

source_lines = s.splitlines(keepends=True)
a = draw_line.lineno - 1
b = draw_line.end_lineno
indent = source_lines[a][:len(source_lines[a]) - len(source_lines[a].lstrip())]
source_lines[a:b] = [indent + "def draw_line_obj(self,o):\n", indent + "    return\n"]
s = ''.join(source_lines)

# Inject the v5.8 network layers immediately after the biome layer if available.
# This preserves all newer biome, boundary, unit and battle rendering code.
if "self.draw_biome_layer(rect)" in s:
    anchor = "        self.draw_biome_layer(rect)\n"
    s = s.replace(
        anchor,
        anchor
        + "        # MB_ROADS_WATER_V5_8_0: unified river/road surfaces.\n"
        + "        self.draw_network_layer('river',rect)\n"
        + "        self.draw_network_layer('road',rect)\n",
        1
    )
elif "rect=self._visible_world_rect()" in s:
    anchor = "        rect=self._visible_world_rect()\n"
    s = s.replace(
        anchor,
        anchor
        + "        # MB_ROADS_WATER_V5_8_0: unified river/road surfaces.\n"
        + "        self.draw_network_layer('river',rect)\n"
        + "        self.draw_network_layer('road',rect)\n",
        1
    )
else:
    raise RuntimeError("Could not find render viewport anchor for network layers")

# Old circular-junction/underlay calls are incompatible with the v5.8 union renderer.
for call in (
    "        self.draw_road_network_underlay()\\n",
    "        self.draw_road_junctions()\\n",
    "        self.draw_junctions()\\n",
):
    s = s.replace(call, "")

compile(s, str(p), "exec")
p.write_text(s, encoding="utf-8")
print("PASS: restored v5.8.0 road/river union renderer without per-segment stacking")
