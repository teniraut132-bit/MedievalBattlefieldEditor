import ast
from pathlib import Path

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
tree=ast.parse(s,str(p))
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="App")
names={"render","_render_now","draw_network_layer","draw_obj","draw_asset","draw_biome_layer","draw_map_boundary","_bbox_visible","world_to_screen","load_project"}
print("=== ENGINE 6 FINAL RENDER INSPECTION ===")
for n in app.body:
    if isinstance(n,ast.FunctionDef) and n.name in names:
        print(f"\n--- {n.name} lines {n.lineno}-{n.end_lineno} ---")
        print(ast.get_source_segment(s,n))
print("\n=== INITIALIZATION MARKERS ===")
for i,line in enumerate(s.splitlines(),1):
    if any(k in line for k in ("_render_pending","canvas=","self.objects=","self.units=","self.scale=")):
        if i<240: print(f"{i}: {line}")
