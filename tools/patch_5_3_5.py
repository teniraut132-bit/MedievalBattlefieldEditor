from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# Restore the simple layered renderer: biome/ground first, rivers second,
# roads third. Remove intersection circles and road underlays, which were
# the source of blobs and the apparent road/river overlap.

def replace_method(source, name, replacement):
    pat = re.compile(
        rf"(?ms)^    def {re.escape(name)}\(self[^\n]*\):\n.*?(?=^    def |\Z)"
    )
    m = pat.search(source)
    if not m:
        return source, False
    return source[:m.start()] + replacement.rstrip() + "\n\n" + source[m.end():], True

# Junction paint is intentionally disabled. Connected strokes meet naturally
# through their rounded caps, without circles painted over the map.
for method in ("draw_junctions", "draw_road_junctions", "draw_road_network_underlay"):
    s, _ = replace_method(
        s, method,
        f"    def {method}(self):\n        return"
    )

# Remove legacy calls wherever the older patches inserted them.
for call in (
    "self.draw_junctions()",
    "self.draw_road_junctions()",
    "self.draw_road_network_underlay()",
):
    s = s.replace(call, "")

# Force predictable line layering. Rivers are always below roads, regardless
# of creation order. This avoids a river segment being repainted on top of a
# road simply because it was created later.
old = """        for o in self.objects:
            if o['kind'] in ('river','road') and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
"""
new = """        # Surface/biome paint is a ground layer and must be rendered before
        # hydrology and infrastructure. Existing biome painting is retained.
        for o in self.objects:
            if o.get('kind') in ('biome', 'terrain_patch', 'landscape') and self._bbox_visible(o,rect):
                self.draw_obj(o)
        for o in self.objects:
            if o.get('kind') == 'river' and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
        for o in self.objects:
            if o.get('kind') == 'road' and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
"""
if old in s:
    s = s.replace(old, new, 1)
else:
    # Fail rather than silently shipping a build whose draw order was not fixed.
    if "self.draw_line_obj(o)" in s and "self.draw_road_network_underlay()" not in s:
        raise RuntimeError("Could not locate the expected line-render loop; refusing to apply uncertain layer ordering")
    raise RuntimeError("Expected line-render loop was not found")

# Normalize legacy biome names to a single explicit ground-layer vocabulary.
# Do not change saved data; this is a render-time classification only.
s = s.replace(
    "if o.get('kind') in ('biome', 'terrain_patch', 'landscape')",
    "if o.get('kind') in ('biome', 'terrain_patch', 'landscape', 'biome_brush', 'terrain_brush')"
)

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("5.3.5 layered rendering patch applied; Python syntax check passed")
