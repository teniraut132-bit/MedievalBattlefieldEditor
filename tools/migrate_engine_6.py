from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[1]
STEPS=[
 "tools/patch_5_6_0_cartography.py",
 "tools/optimize_5_9_0.py",
 "tools/patch_5_9_3_landscape.py",
 "tools/patch_5_9_4_interaction.py",
 "tools/patch_5_9_5_map_boundary.py",
 "tools/patch_5_9_6_library_battle.py",
 "tools/patch_5_9_9_import.py",
 "tools/engine6_scaling.py",
 # Must remain last: this is the locked v5.8 road/water renderer.
 "tools/restore_v5_8_0_roads_water.py",
 "tools/patch_6_1_0_shared_library_battle_ui.py",
]

def main():
    for rel in STEPS:
        path=ROOT/rel
        if not path.is_file():
            raise RuntimeError(f"Missing migration step: {rel}")
        print(f"=== ENGINE 6.0 MIGRATION: {rel} ===")
        runpy.run_path(str(path),run_name="__main__")
    src=ROOT/"editor"/"Medieval_Battlefield_Editor_v4.py"
    compile(src.read_text(encoding="utf-8"),str(src),"exec")
    required=[
        "# MB_ROADS_WATER_V5_8_0",
        "# MB_LANDSCAPE_5_9_3",
        "# MB_INTERACTION_5_9_4",
        "# MB_MAP_BOUNDARY_5_9_5",
        "# MB_FEATURES_5_9_6",
        "# MB_IMPORT_FIX_5_9_9",
        "# MB_PERF_5_9_0",
        "# MB_ENGINE_6_0_0_SCALING",
        "# MB_FEATURES_6_1_0_SHARED_LIBRARY_BATTLE_UI",
    ]
    text=src.read_text(encoding="utf-8")
    missing=[m for m in required if m not in text]
    if missing:raise RuntimeError("Engine 6 feature migration incomplete: "+", ".join(missing))
    for fn in ("draw_network_layer","paint_biome","show_battle_results","import_sprites","import_sprite_pack","export_sprite_pack","draw_map_boundary","refresh_shared_sprite_library"):
        if f"def {fn}" not in text:raise RuntimeError(f"Engine 6 required method missing: {fn}")
    print("PASS: all remaining features migrated into engine 6 build source.")
    print("PASS: v5.8 road/water renderer preserved as final migration step.")

if __name__=="__main__":
    main()
