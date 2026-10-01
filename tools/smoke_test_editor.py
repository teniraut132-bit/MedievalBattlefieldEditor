from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "editor" / "Medieval_Battlefield_Editor_v4.py"


def main() -> int:
    if not EDITOR.is_file():
        print(f"FAIL: editor source missing: {EDITOR}")
        return 1

    spec = importlib.util.spec_from_file_location("mbe_editor_smoke", EDITOR)
    if spec is None or spec.loader is None:
        print("FAIL: cannot load editor module")
        return 1

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import tkinter as tk
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        app = module.App(root)
        root.update_idletasks()
        root.update()

        required = ("canvas", "objects", "units", "render", "draw_asset", "asset_pil", "set_terrain")
        missing = [name for name in required if not hasattr(app, name)]
        if missing:
            raise AssertionError("App missing required attributes/methods: " + ", ".join(missing))

        # Exercise a terrain selection and the full renderer, not just import/compile.
        app.set_terrain("Лес")
        app.objects.append({
            "id": app.oid(),
            "kind": "terrain",
            "terrain": "Лес",
            "points": [(1200, 1200), (1320, 1250), (1450, 1220)],
            "width": 110,
        })
        app.render()
        root.update_idletasks()
        root.update()

        if not app.canvas.find_all():
            raise AssertionError("Renderer produced no canvas items")

        # Resolve and decode a known embedded sprite through the editor's own path.
        key = app.asset_key("tree_01") if hasattr(app, "asset_key") else None
        if not key:
            raise AssertionError("Known sprite alias tree_01 did not resolve")
        image = app.asset_pil(key) if hasattr(app, "asset_pil") else None
        if image is None or image.width < 2 or image.height < 2:
            raise AssertionError("Known embedded sprite failed to decode")

        print("PASS: Tkinter App initialized without geometry-manager conflicts.")
        print("PASS: terrain selection, map rendering, and embedded sprite decoding.")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
