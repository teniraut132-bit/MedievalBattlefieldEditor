from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
MARK = "# MB_ENGINE_6_0_0_SCALING"
if MARK in s:
    print("6.0.0 object scaling already applied")
    raise SystemExit(0)

# Non-network map objects only. Roads and rivers are intentionally untouched.
asset_prop = """            if o.get('kind')=='asset':
                self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v))
"""
if asset_prop in s:
    s = s.replace(asset_prop, asset_prop + """                self.field('Масштаб (%)',round(float(o.get('obj_scale',1.0))*100),lambda v:self.num(o,'obj_scale',max(10,min(500,float(v)))/100))
""", 1)
else:
    asset_prop2 = "            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));"
    if asset_prop2 not in s:
        raise RuntimeError("Could not locate asset property row")
    s = s.replace(asset_prop2, asset_prop2 + "self.field('Масштаб (%)',round(float(o.get('obj_scale',1.0))*100),lambda v:self.num(o,'obj_scale',max(10,min(500,float(v)))/100))", 1)

bridge_old = "x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale;"
bridge_new = "x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*float(o.get('obj_scale',1.0))*self.scale;"
if bridge_old in s:
    s = s.replace(bridge_old, bridge_new, 1)

settlement_old = """        x,y=self.world_to_screen(o['x'],o['y'])
        self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,
"""
settlement_new = """        x,y=self.world_to_screen(o['x'],o['y']);os=float(o.get('obj_scale',1.0))
        self.canvas.create_oval(x-520*os*self.scale,y-400*os*self.scale,x+520*os*self.scale,y+400*os*self.scale,
"""
if settlement_old in s:
    s = s.replace(settlement_old, settlement_new, 1)

# Scale the rendered sprite size by obj_scale without modifying the source asset.
marker = "    def draw_asset(self,o):"
idx = s.find(marker)
if idx < 0:
    raise RuntimeError("draw_asset not found")
line_end = s.find("\n", idx)
insert = (
    "        # " + MARK + "\n"
    "        if o.get('obj_scale',1.0)!=1.0:\n"
    "            o=dict(o)\n"
    "            o['size']=float(o.get('size',70))*float(o.get('obj_scale',1.0))\n"
)
s = s[:line_end+1] + insert + s[line_end+1:]

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("PASS: Engine 6 non-network object scaling patch syntax check")
