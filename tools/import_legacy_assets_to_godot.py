from __future__ import annotations

import ast
import base64
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_CANDIDATES = [
    ROOT / "Medieval_Battlefield_Editor_v5(2).zip",
    ROOT / "Medieval_Battlefield_Editor_v5.zip",
]
DEST = ROOT / "godot" / "assets" / "legacy"


def read_assets_module(archive: zipfile.ZipFile) -> str:
    candidates = [
        n for n in archive.namelist()
        if n.replace("\\", "/").endswith("embedded_assets.py")
    ]
    if not candidates:
        raise RuntimeError("embedded_assets.py not found in legacy source archive")
    return archive.read(candidates[0]).decode("utf-8")


def extract_assets(source: str) -> dict[str, str]:
    tree = ast.parse(source, filename="embedded_assets.py")
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets:
            if any(isinstance(t, ast.Name) and t.id == "ASSETS" for t in node.targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, dict):
                    return {str(k): str(v) for k, v in value.items()}
    raise RuntimeError("ASSETS dictionary not found")


def safe_name(name: str) -> str:
    stem = Path(name.replace("\\", "/")).stem
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    return cleaned.strip("_") or "asset"


def main() -> int:
    archive_path = next((p for p in ZIP_CANDIDATES if p.is_file()), None)
    if archive_path is None:
        raise RuntimeError("Legacy source ZIP not found")
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        assets = extract_assets(read_assets_module(archive))
    written = 0
    used: set[str] = set()
    for original_name, encoded in assets.items():
        raw = encoded
        if raw.lower().startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        data = base64.b64decode(raw, validate=False)
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            continue
        filename = safe_name(original_name) + ".png"
        if filename in used or (DEST / filename).exists():
            n = 2
            while f"{safe_name(original_name)}_{n}.png" in used or (DEST / f"{safe_name(original_name)}_{n}.png").exists():
                n += 1
            filename = f"{safe_name(original_name)}_{n}.png"
        used.add(filename)
        (DEST / filename).write_bytes(data)
        written += 1
    manifest = DEST / "legacy_asset_manifest.txt"
    manifest.write_text(
        "Medieval Battlefield Editor legacy sprite migration\n"
        + f"Source: {archive_path.name}\n"
        + f"Exported PNGs: {written}\n"
        + "Original asset keys are preserved by filename stem where possible.\n",
        encoding="utf-8",
    )
    print(f"PASS: migrated {written} legacy embedded sprites to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
