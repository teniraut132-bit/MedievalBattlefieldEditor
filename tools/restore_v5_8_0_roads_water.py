from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
marker = "# MB_ROADS_WATER_V5_8_0"
if marker in s:
    print("5.8.0 road/water renderer already present")
    raise SystemExit(0)

# Keep every post-5.8 feature intact. Replace only the way roads and rivers are
# rasterized: one union mask per network, exactly as the stable 5.8.0 renderer.
method = String.raw'''    def draw_network_layer(self, kind, rect=None):
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
        self.canvas.create_image(0, 0, image=photo, anchor='nw', tags=('network_layer', kind))

'''
anchor = "    def draw_line_obj(self,o):"
if s.count(anchor) != 1:
    raise RuntimeError("Expected exactly one draw_line_obj()")
s = s.replace(anchor, method + anchor, 1)

# Replace only the live river/road render loop. Biomes, objects, units, boundary
# and all other newer features remain untouched.
old_loop = """        for o in self.objects:
            if o['kind'] in ('river','road') and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
"""
new_loop = """        # 5.8.0 road/water geometry: one union mask per network.
        self.draw_network_layer('river',rect)
        self.draw_network_layer('road',rect)
"""
if old_loop not in s:
    raise RuntimeError("Could not find the active river/road render loop; refusing an uncertain rollback")
s = s.replace(old_loop, new_loop, 1)

# The feature patches may have inserted old underlay/junction calls. Remove only
# those calls; they are not part of the v5.8.0 union-mask renderer.
s = s.replace("        self.draw_road_network_underlay()\n", "")
s = s.replace("        self.draw_road_junctions()\n", "")
s = s.replace("        self.draw_junctions()\n", "")

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("PASS: restored v5.8.0 road/river union renderer without touching other layers")
