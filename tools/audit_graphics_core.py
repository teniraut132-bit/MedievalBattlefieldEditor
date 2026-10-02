#!/usr/bin/env python3
"""Static graphics-core audit for Medieval Battlefield Editor.

This deliberately does not rewrite road/river rendering. It checks the source
bundle, Python syntax, embedded image payloads, renderer entry points, and
archive image integrity before a Windows release is packaged.
"""
from __future__ import annotations
import ast, base64, io, re, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"Medieval_Battlefield_Editor_v5(2).zip"
SOURCE_ROOT=ROOT/"source"
errors=[]
warnings=[]
checks=[]

def ok(label, detail=""):
    checks.append((label, detail))
    print(f"[OK] {label}" + (f": {detail}" if detail else ""))

def fail(label, detail):
    errors.append((label, detail))
    print(f"[FAIL] {label}: {detail}")

def warn(label, detail):
    warnings.append((label, detail))
    print(f"[WARN] {label}: {detail}")

if not ARCHIVE.exists():
    fail("source archive", f"not found: {ARCHIVE}")
else:
    try:
        with zipfile.ZipFile(ARCHIVE) as z:
            bad=z.testzip()
            if bad: fail("ZIP integrity", f"corrupt member {bad}")
            else: ok("ZIP integrity", f"{len(z.namelist())} entries")
            pyfiles=[n for n in z.namelist() if n.endswith(".py")]
            imagefiles=[n for n in z.namelist() if Path(n).suffix.lower() in (".png",".jpg",".jpeg",".webp")]
            if not pyfiles: fail("Python sources", "no .py files in source archive")
            else: ok("Python sources", f"{len(pyfiles)} files")
            if imagefiles: ok("external image resources", f"{len(imagefiles)} files")
            else: warn("external image resources", "none found; checking embedded assets")
            extracted=ROOT/"graphics_audit_source"
            import shutil
            shutil.rmtree(extracted,ignore_errors=True)
            z.extractall(extracted)
            candidates=list(extracted.rglob("Medieval_Battlefield_Editor_v4.py"))
            if not candidates: candidates=list(extracted.rglob("*.py"))
            source_files=candidates
            if not source_files: fail("editor source", "could not locate editor .py file")
            else:
                for p in source_files:
                    try:
                        text=p.read_text(encoding="utf-8-sig")
                        ast.parse(text,filename=str(p))
                        ok("Python syntax",p.name)
                        if "class App" in text or "class Editor" in text:
                            for name in ("render","draw_line_obj","draw_obj","draw_asset","asset_pil"):
                                if re.search(r"^\s+def\s+"+name+r"\s*\(",text,re.M):
                                    ok("renderer entry point",name)
                                elif name in ("draw_line_obj","draw_obj","draw_asset"):
                                    warn("renderer entry point",f"{name} not found under expected name")
                            if not ("river" in text and "road" in text):
                                warn("road/water references","expected identifiers not both found")
                    except Exception as e: fail("Python parse",f"{p}: {e}")
            embedded=list(extracted.rglob("embedded_assets.py"))
            for p in embedded:
                try:
                    ast.parse(p.read_text(encoding="utf-8-sig"),filename=str(p))
                    raw=p.read_text(encoding="utf-8-sig")
                    # Verify literal base64 image payloads without executing imported code.
                    payloads=re.findall(r"""['"]([A-Za-z0-9+/=]{128,})['"]""",raw)
                    valid=0
                    for payload in payloads:
                        try:
                            b=base64.b64decode(payload,validate=True)
                            if b.startswith((b"\x89PNG\r\n\x1a\n",b"\xff\xd8\xff",b"RIFF")):
                                valid+=1
                        except Exception: pass
                    if valid: ok("embedded image payloads",f"{valid} recognizable image payloads")
                    else: warn("embedded image payloads","no large literal base64 image strings recognized; verify asset format")
                except Exception as e: fail("embedded asset module",str(e))
            if imagefiles:
                try:
                    from PIL import Image
                    verified=0
                    for n in imagefiles:
                        try:
                            with z.open(n) as f, Image.open(io.BytesIO(f.read())) as im: im.verify()
                            verified+=1
                        except Exception as e: fail("image integrity",f"{n}: {e}")
                    if verified: ok("image integrity",f"{verified}/{len(imagefiles)} verified")
                except ImportError: warn("image integrity","Pillow unavailable; skipped external image decode test")
    except Exception as e:
        fail("source archive inspection",repr(e))

print("\nGraphics audit summary")
print(f"Passed: {len(checks)} | Warnings: {len(warnings)} | Failed: {len(errors)}")
if warnings:
    print("Warnings:")
    for label,detail in warnings: print(f" - {label}: {detail}")
if errors:
    print("Failures:")
    for label,detail in errors: print(f" - {label}: {detail}")
    sys.exit(1)
print("Static audit completed. GUI rendering and zoom/pan performance require Windows runtime testing.")
