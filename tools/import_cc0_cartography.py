from __future__ import annotations
import base64
import io
import re
import urllib.request
import zipfile
from pathlib import Path

URL = "https://opengameart.org/sites/default/files/cartographypack.zip"
ASSET_MODULE = Path("editor/embedded_assets.py")
CREDITS = Path("editor/ASSET_CREDITS.txt")

def main():
    if not ASSET_MODULE.is_file():
        raise SystemExit(f"Missing embedded asset module: {ASSET_MODULE}")
    req = urllib.request.Request(URL, headers={"User-Agent":"MedievalBattlefieldEditor asset bundler"})
    with urllib.request.urlopen(req, timeout=90) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
        pngs = [i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith(".png")]
        if len(pngs) < 50:
            raise RuntimeError(f"CC0 cartography pack unexpectedly contains only {len(pngs)} PNG files")
        source = ASSET_MODULE.read_text(encoding="utf-8")
        if "cartography_cc0/" in source:
            print("CC0 cartography pack already embedded")
            return
        closing = source.rfind("}")
        if closing < 0:
            raise RuntimeError("ASSETS dictionary closing brace not found")
        lines = []
        added = 0
        for info in pngs:
            # Prefix all names to avoid collisions with the editor's existing sprites.
            stem = Path(info.filename).stem
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:70] or f"item_{added+1}"
            key = f"cartography_cc0/cartography_{safe}.png"
            raw = zf.read(info)
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            encoded = base64.b64encode(raw).decode("ascii")
            lines.append(repr(key) + ":" + repr(encoded) + ",\n")
            added += 1
        if added < 50:
            raise RuntimeError(f"Only {added} valid PNGs could be embedded")
        source = source[:closing] + "".join(lines) + source[closing:]
        ASSET_MODULE.write_text(source, encoding="utf-8")
        CREDITS.write_text(
            "Bundled third-party artwork\n"
            "============================\n"
            "Kenney — Cartography Pack (85 separate PNG tiles plus source files).\n"
            "License: CC0 1.0 Universal (public domain dedication).\n"
            "Official source: https://opengameart.org/content/cartography-pack\n"
            "Attribution is not required; credit to Kenney.nl is appreciated.\n"
            "The editor imports the PNG files from the pack into embedded_assets.py during CI.\n",
            encoding="utf-8"
        )
        print(f"Embedded {added} CC0 cartography PNGs from Kenney's pack.")
if __name__ == "__main__":
    main()
