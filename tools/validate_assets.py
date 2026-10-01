from __future__ import annotations

import base64
import importlib.util
import io
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSET_MODULE = ROOT / "editor" / "embedded_assets.py"

def normalize(value: str) -> str:
    value = str(value).replace("\\\\", "/").rsplit("/", 1)[-1]
    if "." in value:
        value = value.rsplit(".", 1)[0]
    value = "".join(ch.lower() for ch in value if ch.isalnum())
    split = len(value)
    while split > 0 and value[split - 1].isdigit():
        split -= 1
    prefix, digits = value[:split], value[split:]
    return prefix + (str(int(digits)) if digits else "")

def main() -> int:
    if not ASSET_MODULE.is_file():
        print(f"ERROR: embedded asset module missing: {ASSET_MODULE}")
        return 1
    spec = importlib.util.spec_from_file_location("embedded_assets", ASSET_MODULE)
    if spec is None or spec.loader is None:
        print("ERROR: could not load embedded_assets.py")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assets = getattr(module, "ASSETS", None)
    if not isinstance(assets, dict) or not assets:
        print("ERROR: ASSETS is missing or empty")
        return 1

    errors, sizes = [], {}
    for name, encoded in assets.items():
        try:
            if isinstance(encoded, str) and encoded.lstrip().lower().startswith("data:") and "," in encoded:
                encoded = encoded.split(",", 1)[1]
            raw = base64.b64decode(encoded, validate=False)
            with Image.open(io.BytesIO(raw)) as im:
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                if im.width < 2 or im.height < 2:
                    raise ValueError(f"invalid dimensions {im.size}")
                sizes[name] = (im.width, im.height, im.format)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    expected = [
        "house_wood_01", "house_wood_02", "house_stone_01", "house_stone_02",
        "tower_01", "keep_01", "church_01", "gate_01", "mill_01", "barn_01", "barn_02",
        "tree_01", "tree_02", "tree_03", "rock_01", "rock_02", "rock_03",
        "field_01", "field_02", "field_03", "bush_01", "bush_02", "bush_03",
        "wagon_01", "hay_01",
    ]
    available = {normalize(k) for k in assets}
    missing = [name for name in expected if normalize(name) not in available]
    if errors:
        print("CORRUPT ASSETS:")
        print("\\n".join(errors))
    if missing:
        print("MISSING EXPECTED ASSET ALIASES: " + ", ".join(missing))
    print(f"Embedded sprites checked: {len(assets)}")
    print(f"Valid image files: {len(sizes)}")
    if sizes:
        print("Formats: " + ", ".join(sorted({str(v[2]) for v in sizes.values()})))
    if errors or missing:
        return 1
    print("PASS: all embedded images decode and expected palette names resolve.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
