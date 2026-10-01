from pathlib import Path
import ast
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
tree=ast.parse(s,str(p))
app=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="App"),None)
if app is None:raise RuntimeError("App class missing")
methods={n.name for n in app.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
required={"render","draw_network_layer","paint_biome","draw_biome_layer","draw_map_boundary","build_palette",
          "import_sprites","import_sprite_pack","export_sprite_pack","battle","show_battle_results","set_tool","refresh_shared_sprite_library"}
missing=sorted(required-methods)
if missing:raise RuntimeError("Missing App methods: "+", ".join(missing))
for marker in ("MB_ROADS_WATER_V5_8_0","MB_LANDSCAPE_5_9_3","MB_INTERACTION_5_9_4","MB_MAP_BOUNDARY_5_9_5",
               "MB_FEATURES_5_9_6","MB_IMPORT_FIX_5_9_9","MB_PERF_5_9_0","MB_ENGINE_6_0_0_SCALING","MB_FEATURES_6_1_0_SHARED_LIBRARY_BATTLE_UI"):
    if marker not in s:raise RuntimeError("Missing feature marker: "+marker)

# Road/water invariants: the final renderer must use the v5.8 network union,
# and not individually paint road/river layers from render().
render_nodes=[n for n in app.body if isinstance(n,ast.FunctionDef) and n.name in ("render","_render_now")]
render_text="\n".join(ast.get_source_segment(s,n) or "" for n in render_nodes)
if "draw_network_layer('river',rect)" not in render_text or "draw_network_layer('road',rect)" not in render_text:
    raise RuntimeError("Road/water renderer invariant failed: unified v5.8 network calls missing from render/_render_now")
if "draw_line_obj(o)" in render_text:
    raise RuntimeError("Road/water renderer invariant failed: render path still draws per-segment line objects")

# Non-network scaling should exist, but the v5.8 road/river network itself is not
# changed by the new scaling feature.
if "obj_scale" not in s:raise RuntimeError("Object scaling not present")
if "MB_RUNTIME_RENDER_GUARD_6_0_1" not in s:raise RuntimeError("Blank-map runtime guard missing")
if "def fit_map_view(self)" not in s:raise RuntimeError("Fit-view method missing")
print("PASS: engine 6 structural validation.")
