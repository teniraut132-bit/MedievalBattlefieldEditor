from pathlib import Path
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
marker="# MB_PERF_5_9_0"
if marker in s:
    print("5.9.0 performance patch already applied")
    raise SystemExit(0)

# 1) Coalesce bursts of render() calls into a single idle callback.
old="""    def render(self):
        # Coalesce repeated render requests during mouse movement.
        self._render_revision += 1
"""
new="""    def render(self):
        # MB_PERF_5_9_0: coalesce bursts of mouse/zoom events into one redraw.
        # A short delay keeps Tk responsive while panning/zooming instead of
        # rendering a full frame for every mouse event.
        if self._render_pending:
            return
        self._render_pending=True
        try:
            self._render_after=self.root.after(16,self._render_now)
        except tk.TclError:
            self._render_pending=False

    def _render_now(self):
        self._render_pending=False
        self._render_after=None
        self._render_revision += 1
"""
if s.count(old)!=1:
    raise RuntimeError(f"render scheduler anchor mismatch: {s.count(old)}")
s=s.replace(old,new,1)

# 2) Bound the resized-sprite cache so zooming does not retain every size forever.
old="""        target=max(8,min(1200,int(o.get('size',100)*self.scale)))
        key=(o['asset'],target)
        if key not in self.sprite_cache:
            ratio=min(target/im.width,target/im.height)
            res=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS)
            self.sprite_cache[key]=ImageTk.PhotoImage(res)
        self.canvas.create_image(x,y,image=self.sprite_cache[key],tags=('obj',o['id']))
"""
new="""        # MB_PERF_5_9_0: quantize output dimensions to reuse cached sizes across
        # nearby zoom levels, cap expensive raster sizes, and bound memory use.
        raw=max(8,min(900,int(o.get('size',100)*self.scale)))
        target=max(8,int(round(raw/8.0))*8)
        key=(o['asset'],target)
        if key not in self.sprite_cache:
            ratio=min(target/im.width,target/im.height)
            res=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS)
            if len(self.sprite_cache)>=256:
                self.sprite_cache.pop(next(iter(self.sprite_cache)))
            self.sprite_cache[key]=ImageTk.PhotoImage(res)
        self.canvas.create_image(x,y,image=self.sprite_cache[key],tags=('obj',o['id']))
"""
if s.count(old)!=1:
    raise RuntimeError(f"sprite cache anchor mismatch: {s.count(old)}")
s=s.replace(old,new,1)

# 3) Bound imported unit-image size variants too; these are created at different zoom levels.
old="""        if key in self.tkimg:return self.tkimg[key]
        try:
            im=Image.open(p).convert('RGBA');target=max(20,key[1]);ratio=min(target/im.width,target/im.height);im=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS);q=ImageTk.PhotoImage(im);self.tkimg[key]=q;return q
"""
new="""        if key in self.tkimg:return self.tkimg[key]
        try:
            im=Image.open(p).convert('RGBA');target=max(20,min(900,int(round(key[1]/8.0))*8));ratio=min(target/im.width,target/im.height);im=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS);q=ImageTk.PhotoImage(im)
            if len(self.tkimg)>=128:self.tkimg.pop(next(iter(self.tkimg)))
            self.tkimg[key]=q;return q
"""
if s.count(old)!=1:
    raise RuntimeError(f"unit cache anchor mismatch: {s.count(old)}")
s=s.replace(old,new,1)

# 4) With onedir, keep user art next to the install root so updates can preserve it.
old="""        asset_root = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        if asset_root.name.lower() == 'editor':asset_root = asset_root.parent
"""
new="""        asset_root = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        if asset_root.name.lower() in ('editor','medievalbattlefieldeditor'):asset_root = asset_root.parent
"""
if old in s:
    s=s.replace(old,new,1)
elif "asset_root.name.lower() in ('editor','medievalbattlefieldeditor')" not in s:
    raise RuntimeError("could not find user-asset root setup to adapt for onedir")

s=s.replace("self._render_pending=False;self._render_after=None;self._render_revision=0",
            "self._render_pending=False;self._render_after=None;self._render_revision=0")
s=s.replace("        self._render_pending=False;self._render_after=None;self._render_revision=0\n",
            "        self._render_pending=False;self._render_after=None;self._render_revision=0\n        # MB_PERF_5_9_0: render scheduling state is initialized before UI bindings.\n")

p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("5.9.0 render coalescing, bounded sprite caches, and asset-root patch passed syntax check")
