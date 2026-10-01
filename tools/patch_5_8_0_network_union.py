from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
if "# MB_CARTOGRAPHY_5_8_0_NETWORK_UNION" in s:
    print("5.8.0 network-union patch already applied")
    raise SystemExit(0)

# Render all roads / all rivers into one raster mask per network. Painting each
# segment independently with an outline is the root cause of dark stacked seams
# and bulb-shaped junctions. A union mask paints the shared footprint only once.
method = r'''    def draw_network_layer(self, kind, rect=None):
        # MB_CARTOGRAPHY_5_8_0_NETWORK_UNION
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

        # Each mask is a union of every segment in this network. Edges and
        # surfaces are applied to the union, not repeatedly on each segment.
        edge_mask = Image.new('L', (w, h), 0)
        surface_mask = Image.new('L', (w, h), 0)
        edge_draw = ImageDraw.Draw(edge_mask)
        surface_draw = ImageDraw.Draw(surface_mask)
        if kind == 'river':
            edge_color, surface_color = '#4b4238', '#4fa8a2'
            edge_extra, surface_factor = 28.0, 1.0
        else:
            edge_color, surface_color = '#514437', '#b7a080'
            edge_extra, surface_factor = 10.0, 1.0
        for points, base in paths:
            coords = [(int(round(x)), int(round(y))) for x, y in points]
            edge_width = max(3, int(round(base + edge_extra * self.scale)))
            surface_width = max(2, int(round(base * surface_factor)))
            # Pillow's joint='curve' keeps bends connected without round stamps.
            edge_draw.line(coords, fill=255, width=edge_width, joint='curve')
            surface_draw.line(coords, fill=255, width=surface_width, joint='curve')
            # Explicit endpoint discs are part of the mask union; they prevent
            # tiny gaps at acute bends without drawing a separate visible dot.
            r1 = edge_width // 2
            r2 = surface_width // 2
            for x, y in (coords[0], coords[-1]):
                edge_draw.ellipse((x-r1, y-r1, x+r1, y+r1), fill=255)
                surface_draw.ellipse((x-r2, y-r2, x+r2, y+r2), fill=255)

        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        layer.paste(edge_color, (0, 0, w, h), edge_mask)
        layer.paste(surface_color, (0, 0, w, h), surface_mask)

        # A single subtle river highlight is clipped to the water surface mask.
        # Road details are intentionally omitted at junctions so no line can
        # create a second stroke or a dark seam across a merged road.
        if kind == 'river' and self.scale > .18:
            highlight = Image.new('L', (w, h), 0)
            hd = ImageDraw.Draw(highlight)
            for points, base in paths:
                coords = [(int(round(x)), int(round(y))) for x, y in points]
                hd.line(coords, fill=110, width=max(1, int(round(min(2.0, self.scale*1.4))),), joint='curve')
            # Keep the highlight subtle and inside the merged river surface.
            import PIL.ImageChops
            highlight = PIL.ImageChops.multiply(highlight, surface_mask)
            layer.paste('#83c7bd', (0, 0, w, h), highlight)

        photo = ImageTk.PhotoImage(layer)
        if not hasattr(self, '_network_layer_photos'):
            self._network_layer_photos = {}
        self._network_layer_photos[kind] = photo
        self.canvas.create_image(0, 0, image=photo, anchor='nw', tags=('network_layer', kind))

'''
# Insert immediately before the current line renderer, replacing it only if needed.
anchor = re.search(r"(?m)^    def draw_line_obj\(self,o\):", s)
if not anchor:
    raise RuntimeError("Could not find draw_line_obj() for network renderer insertion")
s = s[:anchor.start()] + method + s[anchor.start():]

# Replace render() as a whole so no earlier road/river per-segment passes survive.
render = '''    def render(self):
        self._render_revision += 1
        self.canvas.delete('all')
        w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())
        self.canvas.create_rectangle(0,0,w,h,fill='#b8a97c',outline='',tags='background')
        self._draw_ground_texture(w,h)
        rect=self._visible_world_rect()
        for o in self.objects:
            if o.get('kind')=='terrain' and self._bbox_visible(o,rect):
                self.draw_terrain_obj(o)
        # Network layers are rasterized once each; segment overlaps are unions.
        self.draw_network_layer('river',rect)
        self.draw_network_layer('road',rect)
        for o in self.objects:
            if o.get('kind') not in ('river','road','terrain') and self._bbox_visible(o,rect):
                self.draw_obj(o)
        for u in self.units:
            if rect[0]-100 <= u['x'] <= rect[2]+100 and rect[1]-100 <= u['y'] <= rect[3]+100:
                self.draw_unit(u)
        if self.selected:
            self.draw_selection(self.selected[1])

'''
pattern = re.compile(r"(?ms)^    def render\(self\):\r?\n.*?(?=^    def pts\(self,p\):)")
m = pattern.search(s)
if not m:
    raise RuntimeError("Could not replace render(): expected render() before pts()")
s = s[:m.start()] + render + s[m.end():]

# Line objects remain editable/selectable; they are no longer individually painted.
# Ensure previews remain available while drawing new paths.
p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("PASS: 5.8.0 network-union renderer syntax check")
