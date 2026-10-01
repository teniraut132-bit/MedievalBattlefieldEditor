from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# Make road rendering self-contained: never paint a second road underlay over
# rivers, then redraw road surfaces above them. This avoids object-order seams.
start = s.index("    def draw_line_obj(self,o):")
end = s.index("    def line_segments(self,o):", start)
new = r'''    def draw_line_obj(self,o):
        p=self.pts(o.get('points',[]))
        if len(p)<4:
            return
        wd=max(1.0,o.get('width',25)*self.scale)
        if o.get('kind')=='river':
            self.canvas.create_line(*p,fill='#4b4238',width=max(8,int(wd+32*self.scale)),smooth=True,capstyle='round',joinstyle='round')
            self.canvas.create_line(*p,fill='#4fa8a2',width=max(5,int(wd)),smooth=True,capstyle='round',joinstyle='round')
            self.canvas.create_line(*p,fill='#8ccbc1',width=max(1,int(2*self.scale)),smooth=True,capstyle='round',joinstyle='round')
            return
        rt=o.get('road_type','Просёлочная')
        colors={
            'Просёлочная':('#4a3b2d','#b79a70','#dbc79f'),
            'Мощенная':('#51483e','#756b5d','#b9ad96'),
            'Брусчаточная':('#4a3b2d','#8b7b67','#c5b69a')
        }
        edge,surf,detail=colors.get(rt,colors['Просёлочная'])
        self.canvas.create_line(*p,fill=edge,width=max(5,int(wd+10*self.scale)),smooth=True,capstyle='round',joinstyle='round')
        self.canvas.create_line(*p,fill=surf,width=max(3,int(wd)),smooth=True,capstyle='round',joinstyle='round')
        dash=(2,5) if rt=='Брусчаточная' else (7,6) if rt=='Мощенная' else ()
        self.canvas.create_line(*p,fill=detail,width=max(1,int(wd*.13)),smooth=True,capstyle='round',joinstyle='round',dash=dash)

'''
s = s[:start] + new + s[end:]

# The old underlay painted all road outlines after rivers, causing a broad
# second pass that visually swallowed river banks. Remove every call to it.
s = re.sub(r"(?m)^\s*self\.draw_road_network_underlay\(\)\s*\n", "", s)

# Round blobs at road intersections are no longer needed: the actual road
# strokes have rounded caps and their own outline, so junctions join naturally.
start = s.find("    def draw_road_junctions(self):")
if start >= 0:
    end = s.find("    def draw_obj(self,o):", start)
    if end < 0:
        raise RuntimeError("Could not find draw_obj() after draw_road_junctions()")
    noop = """    def draw_road_junctions(self):
        # Road joins are rendered by the road strokes themselves. Do not paint
        # large intersection circles over nearby rivers or terrain.
        return

"""
    s = s[:start] + noop + s[end:]

# Ensure the post-pass redraws roads on top of the initial line pass, which
# gives crossings a consistent visual order independent of object creation order.
if "self.draw_road_junctions()" not in s:
    needle = "        self.draw_junctions()"
    if needle in s:
        s = s.replace(needle, "        for o in self.objects:\n            if o.get('kind')=='road' and self._bbox_visible(o,rect):\n                self.draw_line_obj(o)\n        self.draw_road_junctions()\n        self.draw_junctions()", 1)

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("5.2.5 layer-order patch applied; Python syntax check passed")
