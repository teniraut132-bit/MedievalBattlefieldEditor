from pathlib import Path
import ast
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
MARK="# MB_ENGINE_6_0_0_SCALING"
if MARK in s:
    print("6.0.0 object scaling already applied")
    raise SystemExit(0)

# Add a single scale property for non-network map objects. Roads and rivers are
# deliberately excluded so the established v5.8.0 renderer is untouched.
needle="""            if o.get('kind')=='asset':
                self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v))
"""
if needle in s:
    repl=needle+"""                self.field('Масштаб (%)',round(float(o.get('obj_scale',1.0))*100),lambda v:self.num(o,'obj_scale',max(10,min(500,float(v)))/100))
"""
    s=s.replace(needle,repl,1)
else:
    # Fallback for a compact one-line property row in older source.
    needle2="            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));"
    if needle2 not in s:
        raise RuntimeError("Could not locate asset property row")
    s=s.replace(needle2,needle2+"self.field('Масштаб (%)',round(float(o.get('obj_scale',1.0))*100),lambda v:self.num(o,'obj_scale',max(10,min(500,float(v)))/100))",1)

# Extend bridge/settlement/asset rendering through a small object-local scale.
# Existing saved projects remain compatible because obj_scale defaults to 1.0.
s=s.replace("x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale;",
            "x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*float(o.get('obj_scale',1.0))*self.scale;",1)
s=s.replace("x,y=self.world_to_screen(o['x'],o['y'])
        self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,",
            "x,y=self.world_to_screen(o['x'],o['y']);os=float(o.get('obj_scale',1.0))
        self.canvas.create_oval(x-520*os*self.scale,y-400*os*self.scale,x+520*os*self.scale,y+400*os*self.scale,",1)

# Asset renderer: only map objects with explicit obj_scale are affected.
asset_marker="    def draw_asset(self,o):"
i=s.find(asset_marker)
if i<0:raise RuntimeError("draw_asset not found")
line_end=s.find("
",i)
s=s[:line_end+1]+"        # "+MARK+"\n        if o.get('obj_scale',1.0)!=1.0:o=dict(o);o['size']=float(o.get('size',70))*float(o.get('obj_scale',1.0))\n"+s[line_end+1:]

s=s.replace("if o.get('kind') in ('biome', 'terrain_patch', 'landscape', 'biome_brush', 'terrain_brush')",
            "if o.get('kind') in ('biome', 'terrain_patch', 'landscape', 'biome_brush', 'terrain_brush')")
p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("PASS: 6.0.0 non-network object scaling patch")
