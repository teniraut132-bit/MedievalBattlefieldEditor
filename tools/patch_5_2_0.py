from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# 5.1.1 already adds line intersections. Replace that renderer with a
# true round-junction renderer: the road surface is drawn over the seam,
# so crossing/branching roads visually become one continuous network.
start = s.find("    def draw_road_junctions(self):")
if start >= 0:
    end = s.find("    def draw_obj(self,o):", start)
    if end < 0:
        raise RuntimeError("draw_obj() was not found")
    new = """    def draw_road_junctions(self):
        roads = [o for o in self.objects if o.get('kind') == 'road']
        for i, a in enumerate(roads):
            for b in roads[i+1:]:
                radius = max(4, (a.get('width', 25) + b.get('width', 25)) * 0.55 * self.scale)
                for sa, sb in self.line_segments(a):
                    for sc, sd in self.line_segments(b):
                        q = self.seg_intersection(sa, sb, sc, sd)
                        if not q:
                            continue
                        x, y = self.world_to_screen(*q)

                        # Dark foundation hides the seam between two strokes.
                        self.canvas.create_oval(
                            x-radius-3*self.scale, y-radius-3*self.scale,
                            x+radius+3*self.scale, y+radius+3*self.scale,
                            fill='#4a3b2d', outline=''
                        )

                        rt = a.get('road_type', 'Просёлочная')
                        surfaces = {
                            'Просёлочная': '#b79a70',
                            'Мощенная': '#756b5d',
                            'Брусчаточная': '#8b7b67'
                        }
                        details = {
                            'Просёлочная': '#dbc79f',
                            'Мощенная': '#b9ad96',
                            'Брусчаточная': '#c5b69a'
                        }
                        surface = surfaces.get(rt, surfaces['Просёлочная'])
                        detail = details.get(rt, details['Просёлочная'])

                        self.canvas.create_oval(
                            x-radius, y-radius, x+radius, y+radius,
                            fill=surface, outline=''
                        )

                        # Small texture keeps the junction from looking like a
                        # separate blob while preserving the road's style.
                        if rt == 'Брусчаточная':
                            r = max(2, radius * 0.10)
                            self.canvas.create_oval(
                                x-r, y-r, x+r, y+r,
                                fill=detail, outline=''
                            )

    """
    s = s[:start] + new + s[end:]
else:
    raise RuntimeError("draw_road_junctions() was not found; previous road patch did not run")

# Also make sure the renderer calls the junction pass after roads are drawn.
if "self.draw_road_junctions()" not in s:
    needle = "        self.draw_road_network_underlay()"
    if needle in s:
        s = s.replace(
            needle,
            needle + "\n        self.draw_road_junctions()",
            1
        )

p.write_text(s, encoding="utf-8")
print("Applied 5.2.0 road junction rendering patch")
