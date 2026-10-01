from pathlib import Path
import ast

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
marker = "# MB_MAP_BOUNDARY_5_9_5"
if marker in s:
    print("5.9.5 map boundary patch already applied")
    raise SystemExit(0)

# Discover the existing renderer structurally, rather than relying on fragile
# line numbers. The boundary is called at the end of render(), after map content.
tree = ast.parse(s)
app_class = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App"), None)
if app_class is None:
    raise RuntimeError("Could not find App class")
render_node = next((n for n in app_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "render"), None)
if render_node is None:
    raise RuntimeError("Could not find App.render()")
lines = s.splitlines(keepends=True)
indent = " " * (render_node.col_offset + 4)
insert_at = render_node.end_lineno
# Insert at the end of render(), immediately before the next class method.
call = indent + "self.draw_map_boundary()  # MB_MAP_BOUNDARY_5_9_5\\n"
lines.insert(insert_at, call)
s = "".join(lines)

# Add a restrained parchment-cartography frame. It is drawn in world coordinates,
# so it stays attached to the actual map edges while zooming/panning. Road and
# river geometry is untouched.
anchor = "    def draw_line_obj(self,o):"
if s.count(anchor) != 1:
    raise RuntimeError("Could not find unique draw_line_obj() insertion point")
method = '''    # MB_MAP_BOUNDARY_5_9_5
    def draw_map_boundary(self):
        # The editor's playable world is 8000 x 5000 world units.
        # Fall back to these dimensions for old projects lacking explicit bounds.
        world_w = int(getattr(self, 'world_w', getattr(self, 'WORLD_W', 8000)))
        world_h = int(getattr(self, 'world_h', getattr(self, 'WORLD_H', 5000)))
        x1, y1 = self.world_to_screen(0, 0)
        x2, y2 = self.world_to_screen(world_w, world_h)
        left, top, right, bottom = min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)
        # A dark ink outer stroke, muted ochre inner rule, and a fine highlight
        # evoke a framed medieval parchment without covering the map interior.
        pad = max(2, 5*self.scale)
        self.canvas.create_rectangle(left, top, right, bottom,
            outline='#3b2b20', width=max(2, 4*self.scale), tags=('map_boundary',))
        inset = max(3, 10*self.scale)
        self.canvas.create_rectangle(left+inset, top+inset, right-inset, bottom-inset,
            outline='#8d6b3e', width=max(1, 1.6*self.scale), tags=('map_boundary',))
        inner = max(5, 15*self.scale)
        self.canvas.create_rectangle(left+inner, top+inner, right-inner, bottom-inner,
            outline='#d0b77c', width=max(1, self.scale), dash=(max(2,int(4*self.scale)), max(2,int(5*self.scale))),
            tags=('map_boundary',))
        # Corner flourishes: short engraved diagonals, kept within the frame.
        span = max(8, 28*self.scale)
        stroke = max(1, 1.5*self.scale)
        for cx, cy, sx, sy in (
            (left+inset, top+inset, 1, 1),
            (right-inset, top+inset, -1, 1),
            (left+inset, bottom-inset, 1, -1),
            (right-inset, bottom-inset, -1, -1),
        ):
            self.canvas.create_line(cx, cy+sy*span, cx, cy, cx+sx*span, cy,
                fill='#6f4e2d', width=max(1,2*self.scale), tags=('map_boundary',))
            self.canvas.create_line(cx+sx*span*.24, cy+sy*span*.24,
                cx+sx*span*.68, cy+sy*span*.68,
                fill='#b18b50', width=stroke, tags=('map_boundary',))
            self.canvas.create_oval(cx-2*self.scale, cy-2*self.scale,
                cx+2*self.scale, cy+2*self.scale,
                fill='#8b6237', outline='#3b2b20', tags=('map_boundary',))
        # Small title cartouche attached to the upper-left edge; only visible
        # when that part of the map is in the viewport.
        label_x = left + max(22, 38*self.scale)
        label_y = top + max(12, 20*self.scale)
        self.canvas.create_text(label_x, label_y, text='✦ КАРТА ПОЛЯ БИТВЫ ✦',
            anchor='nw', fill='#493421',
            font=('Georgia', max(7, int(10*self.scale)), 'bold'),
            tags=('map_boundary',))

'''
s = s.replace(anchor, method + anchor, 1)
p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("5.9.5 stylized map boundary patch applied; Python syntax check passed")
