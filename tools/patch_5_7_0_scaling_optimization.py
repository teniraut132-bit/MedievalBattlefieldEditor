from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
if "# MB_CARTOGRAPHY_5_7_0" in s:
    print("5.7.0 scaling/optimization patch already applied")
    raise SystemExit(0)

# 1) Add one uniform scale control to the object property inspector.
anchor = "            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));self.field('Спрайт',o.get('asset',''),lambda v:self.val(o,'asset',v))\n"
if s.count(anchor) != 1:
    raise RuntimeError("Could not find asset property row to anchor universal object scale")
s = s.replace(anchor, anchor + """            # MB_CARTOGRAPHY_5_7_0 — all map objects have an independent scale.
            self.field('Масштаб (%)',round(float(o.get('obj_scale',1.0))*100),lambda v:self.num(o,'obj_scale',max(10,min(500,float(v)))/100))
""", 1)

# 2) Scale line widths consistently for roads, rivers and painted biomes.
old = "        wd=max(1.0,float(o.get('width',25))*self.scale)\n"
if s.count(old) != 1:
    raise RuntimeError("Could not find line-width calculation")
s = s.replace(old, "        wd=max(1.0,float(o.get('width',25))*float(o.get('obj_scale',1.0))*self.scale)\n", 1)

# 3) Sprite objects already expose their base Size field in the inspector; keep it
# independent from map zoom and avoid mutating embedded PIL assets.

# 4) Scale bridges and settlement outlines/text using a local copy.
bridge_anchor = "        x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale\n"
if s.count(bridge_anchor) == 1:
    s = s.replace(bridge_anchor, "        x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*float(o.get('obj_scale',1.0))*self.scale\n", 1)
settle_anchor = "        x,y=self.world_to_screen(o['x'],o['y'])\n        self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,outline='#655039',dash=(8,5),width=2)\n        self.canvas.create_text(x,y-420*self.scale,text=o.get('name','Поселение'),font=('Georgia',max(9,int(18*self.scale)),'bold'),fill='#38291e')\n"
if s.count(settle_anchor) == 1:
    s = s.replace(settle_anchor, """        x,y=self.world_to_screen(o['x'],o['y']);os=float(o.get('obj_scale',1.0))
        self.canvas.create_oval(x-520*os*self.scale,y-400*os*self.scale,x+520*os*self.scale,y+400*os*self.scale,outline='#655039',dash=(8,5),width=2)
        self.canvas.create_text(x,y-420*os*self.scale,text=o.get('name','Поселение'),font=('Georgia',max(9,int(18*os*self.scale)),'bold'),fill='#38291e')
""", 1)

# 5) Performance: avoid drawing a second full road network over the visible, clipped ribbons.
# The duplicated network pass caused a large number of extra Canvas items during zoom.
s = s.replace("        self.draw_road_network_underlay()\n", "        # MB_CARTOGRAPHY_5_7_0: road ribbons are drawn once in viewport order; skip duplicate full-network underlay.\n")
s = s.replace("        self.draw_road_junctions()\n", "        # Smooth ribbon overlap replaces per-junction stamp items.\n")
s = s.replace("        self.draw_junctions()\n", "        # No separate junction stamps; prevents round dots and reduces Canvas item count.\n")

# Terrain texture marks become sparse at close zooms, where each mark would otherwise
# multiply Canvas items while the user is zooming and panning.
s = s.replace("        if self.scale < .16:return\n", "        if self.scale < .16 or self.scale > 1.35:return\n")
s = s.replace("            for _ in range(3 if self.scale<.35 else 6):\n", "            for _ in range(2 if self.scale<.35 else 4):\n")

# Use a modest sampling distance at high zoom to keep freehand strokes smooth without
# storing hundreds of nearly identical points.
s = s.replace("if math.hypot(x-self.stroke[-1][0],y-self.stroke[-1][1])>max(12,self.brush*.12):self.stroke.append((x,y));self.preview()",
              "if math.hypot(x-self.stroke[-1][0],y-self.stroke[-1][1])>max(8,min(24,self.brush*.10)):self.stroke.append((x,y));self.preview()")

s = s.replace("def serial(self):return {'version':6,", "def serial(self):return {'version':7,", 1)
p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("PASS: 5.7.0 universal scaling and rendering optimization patch; Python syntax compiles")
