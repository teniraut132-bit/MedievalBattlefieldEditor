from pathlib import Path
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
MARK="# MB_RUNTIME_RENDER_GUARD_6_0_1"
if MARK in s:
    print("6.0.1 render guard already applied")
    raise SystemExit(0)

# Add a safe "fit map to viewport" helper. This does not modify map geometry,
# roads, rivers, biomes, sprites, or saved data.
anchor="    def world_to_screen(self,x,y):"
if anchor not in s:
    raise RuntimeError("world_to_screen anchor not found")
fit = """    # MB_RUNTIME_RENDER_GUARD_6_0_1
    def fit_map_view(self):
        w=max(1,self.canvas.winfo_width()-40)
        h=max(1,self.canvas.winfo_height()-40)
        self.scale=max(.05,min(2.0,min(w/WORLD_W,h/WORLD_H)))
        self.pan_x=0
        self.pan_y=0

"""
s=s.replace(anchor,fit+anchor,1)

# Add a compact "fit" button next to any existing view controls.
needle="ttk.Button(zoomrow,text='Сброс',command=self.reset_view).pack(side='left',expand=True,fill='x',padx=1)"
if needle in s and "command=self.fit_map_view" not in s:
    s=s.replace(needle,needle+";ttk.Button(zoomrow,text='Вписать',command=lambda:(self.fit_map_view(),self.render())).pack(side='left',expand=True,fill='x',padx=1)",1)

# Bind F5 and Home to a deterministic view reset.
bind_anchor="self.canvas.pack(fill='both',expand=True)"
if bind_anchor in s and "<F5>" not in s:
    s=s.replace(bind_anchor,bind_anchor+"\n        self.root.bind('<F5>',lambda e:(self.fit_map_view(),self.render()))\n        self.root.bind('<Home>',lambda e:(self.reset_view(),self.render()))",1)

# When loading a project, render synchronously once after the scheduler request.
load_anchor="self.selected=None;self.tkimg.clear();self.sprite_cache.clear();self.empty_props();self.render();self.refresh();self.status.set('Проект загружен')"
if load_anchor in s:
    replacement="self.selected=None;self.tkimg.clear();self.sprite_cache.clear();self.empty_props();self.render();self._render_now() if hasattr(self,'_render_now') else None;self.refresh();self.status.set('Проект загружен')"
    s=s.replace(load_anchor,replacement,1)

# Likewise, after generation force one immediate frame. The scheduler remains for
# interaction; this only guarantees the first generated map cannot remain blank.
gen_anchor="self.objects=[];self.units=[];self.selected=None;self.oid_n=self.uid_n=0"
if gen_anchor in s:
    # Do not inject multiple times if generation code contains another state reset.
    pos=s.find(gen_anchor)
    after=s.find("\n",pos)
    # Only add a later call near the existing generate/render sequence if no sync call exists.
    if "self._render_now() if hasattr(self,'_render_now') else None" not in s[s.find("def generate"):s.find("def generate")+5000]:
        gend=s.find("        self.render()",pos)
        if gend>=0:
            lineend=s.find("\n",gend)
            s=s[:lineend+1]+"        self._render_now() if hasattr(self,'_render_now') else None\n"+s[lineend+1:]

# Critical guard: if a map has objects but the current camera produces zero
# visible items, automatically fit the whole map and rerender. This targets the
# exact failure mode where the object tree is populated but the canvas is empty.
guard="        rect=self._visible_world_rect()\n"
if s.count(guard)==0:
    raise RuntimeError("render rect anchor not found")
idx=s.find(guard)
# Choose the rect inside _render_now, not another helper.
render_start=s.find("    def _render_now(self):")
idx=s.find(guard,render_start)
if idx<0: raise RuntimeError("_render_now rect anchor not found")
insert="""        rect=self._visible_world_rect()
        # If the scene contains objects but none are in the current viewport,
        # recover the camera instead of showing an apparently empty map.
        if self.objects:
            visible_count=sum(1 for obj in self.objects if self._bbox_visible(obj,rect))
            if visible_count==0:
                self.fit_map_view()
                rect=self._visible_world_rect()
"""
s=s[:idx]+insert+s[idx+len(guard):]

p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("PASS: 6.0.1 runtime render guard and fit-view patch syntax check")
