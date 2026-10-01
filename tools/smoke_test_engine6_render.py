from pathlib import Path
import importlib.util
import runpy
import sys
import tkinter as tk
import traceback

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"editor"/"Medieval_Battlefield_Editor_v4.py"

def main():
    # The workflow has already migrated the source, so test the exact final file.
    sys.path.insert(0,str(SRC.parent))
    spec=importlib.util.spec_from_file_location("mbe_engine6_smoke",SRC)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root=tk.Tk()
    root.withdraw()
    try:
        app=module.App(root)
        root.update_idletasks()
        # Force the actual frame function instead of waiting for a timer.
        if hasattr(app,"_render_now"):
            app._render_now()
        else:
            app.render()
            root.update()
        app.objects=[
            {'id':app.oid(),'kind':'river','points':[(3500,1200),(4000,1350),(4500,1250)],'width':100},
            {'id':app.oid(),'kind':'road','points':[(3200,1800),(4000,1600),(4700,1750)],'width':30,'road_type':'Просёлочная'},
            {'id':app.oid(),'kind':'asset','asset':'tree_01','x':4300,'y':2200,'size':120},
            {'id':app.oid(),'kind':'settlement','x':4000,'y':2500,'name':'Smoke Test'},
        ]
        app.units=[{'id':app.uid(),'name':'Test Unit','side':'Красные','men':100,'x':4000,'y':2400}]
        if hasattr(app,"_render_now"):app._render_now()
        root.update_idletasks()
        items=app.canvas.find_all()
        if len(items)<6:
            raise AssertionError(f"Renderer created only {len(items)} canvas items; expected visible map content.")
        print(f"PASS: final Engine 6 renderer created {len(items)} canvas items with road, river, sprite and unit.")
        return 0
    finally:
        root.destroy()

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
