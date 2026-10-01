from pathlib import Path
import math

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
marker = "# MB_INTERACTION_5_9_4"
if marker in s:
    print("5.9.4 interaction patch already applied")
    raise SystemExit(0)

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)

# State used by Ctrl+left-button rotation. Normal selection/movement stays unchanged.
once(
"        self._render_pending=False;self._render_after=None;self._render_revision=0\n",
"        self._render_pending=False;self._render_after=None;self._render_revision=0\n        # MB_INTERACTION_5_9_4: live rotation drag state.\n        self.rotation_drag=None\n",
"rotation state"
)

# Ctrl+left click selects a rotatable object and starts an angular drag.
once(
"""    def left(self,e):
        self.canvas.focus_set();x,y=self.snap(*self.screen_to_world(e.x,e.y))
""",
"""    def left(self,e):
        self.canvas.focus_set()
        if e.state & 0x0004:
            hit=self.pick(e.x,e.y)
            if hit and hit[0]=='object' and hit[1].get('kind') in ('asset','tree','bridge'):
                self.snapshot()
                obj=hit[1]
                wx,wy=self.screen_to_world(e.x,e.y)
                self.selected=hit
                self.rotation_drag={
                    'obj':obj,
                    'start_angle':math.atan2(wy-obj.get('y',wy),wx-obj.get('x',wx)),
                    'start_rotation':float(obj.get('rotation',0.0))
                }
                self.show_props()
                self.render()
                self.status.set('Поворот объекта: удерживайте Ctrl и ведите ЛКМ вокруг объекта')
            else:
                self.rotation_drag=None
            return
        self.rotation_drag=None
        x,y=self.snap(*self.screen_to_world(e.x,e.y))
""",
"Ctrl-click rotation start"
)

# While Ctrl remains held, dragging changes angle continuously around the object center.
once(
"""    def left_drag(self,e):
        x,y=self.snap(*self.screen_to_world(e.x,e.y))
""",
"""    def left_drag(self,e):
        if self.rotation_drag is not None and (e.state & 0x0004):
            obj=self.rotation_drag['obj']
            wx,wy=self.screen_to_world(e.x,e.y)
            dx=wx-obj.get('x',wx);dy=wy-obj.get('y',wy)
            if abs(dx)+abs(dy)>1:
                current=math.atan2(dy,dx)
                delta=math.degrees(current-self.rotation_drag['start_angle'])
                obj['rotation']=(self.rotation_drag['start_rotation']+delta)%360.0
                self.render()
            return
        x,y=self.snap(*self.screen_to_world(e.x,e.y))
""",
"Ctrl-drag rotation update"
)

once(
"""    def left_up(self,e):
        if self.tool in ('river','road') and self.stroke and len(self.stroke)>1:
""",
"""    def left_up(self,e):
        if self.rotation_drag is not None:
            self.rotation_drag=None
            if self.selected:self.show_props()
            self.render()
            return
        if self.tool in ('river','road') and self.stroke and len(self.stroke)>1:
""",
"rotation release"
)

# Paint intermediate biome stamps between mouse events so fast drags do not leave gaps.
once(
"""        elif self.tool.startswith('biome:'):
            spacing=max(12,self.brush*.28)
            if self.last is None or math.hypot(x-self.last[0],y-self.last[1])>spacing:
                self.paint_biome(self.tool.split(':',1)[1],x,y)
        self.last=(x,y)
""",
"""        elif self.tool.startswith('biome:'):
            spacing=max(12,self.brush*.28)
            biome=self.tool.split(':',1)[1]
            if self.last is None:
                self.paint_biome(biome,x,y)
            else:
                lx,ly=self.last
                distance=math.hypot(x-lx,y-ly)
                steps=max(1,int(distance/spacing))
                if distance>=spacing:
                    for i in range(1,steps+1):
                        t=i/steps
                        self.paint_biome(biome,lx+(x-lx)*t,ly+(y-ly)*t)
        self.last=(x,y)
""",
"continuous biome brush"
)

# Rotate sprite pixels after resizing; include angle in the cache key to avoid stale images.
once(
"""        key=(o['asset'],target)
        if key not in self.sprite_cache:
            ratio=min(target/im.width,target/im.height)
            res=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS)
            if len(self.sprite_cache)>=256:
                self.sprite_cache.pop(next(iter(self.sprite_cache)))
            self.sprite_cache[key]=ImageTk.PhotoImage(res)
""",
"""        # MB_INTERACTION_5_9_4: angle is part of the bounded cache key.
        angle=int(round(float(o.get('rotation',0.0))))%360
        key=(o['asset'],target,angle)
        if key not in self.sprite_cache:
            ratio=min(target/im.width,target/im.height)
            res=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS)
            if angle:
                res=res.rotate(-angle,expand=True,resample=Image.Resampling.BICUBIC)
            if len(self.sprite_cache)>=256:
                self.sprite_cache.pop(next(iter(self.sprite_cache)))
            self.sprite_cache[key]=ImageTk.PhotoImage(res)
""",
"rotated sprite rendering"
)

# Bridges use rotated corners and rotated crossbeams; roads/rivers are not touched.
old_bridge = """        if o['kind']=='bridge':
            x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale;self.canvas.create_rectangle(x-L/2,y-12*self.scale,x+L/2,y+12*self.scale,fill='#68462e',outline='#302117',width=3)
            for xx in range(int(x-L/2+8),int(x+L/2),max(8,int(18*self.scale))):self.canvas.create_line(xx,y-11*self.scale,xx,y+11*self.scale,fill='#b17c47',width=2)
"""
new_bridge = """        if o['kind']=='bridge':
            x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale;H=12*self.scale
            a=math.radians(float(o.get('rotation',0.0)));ca=math.cos(a);sa=math.sin(a)
            def rp(dx,dy):return (x+ca*dx-sa*dy,y+sa*dx+ca*dy)
            corners=[rp(-L/2,-H),rp(L/2,-H),rp(L/2,H),rp(-L/2,H)]
            self.canvas.create_polygon(*[v for pt in corners for v in pt],fill='#68462e',outline='#302117',width=3)
            step=max(8,int(18*self.scale));pos=-L/2+8
            while pos<L/2:
                p1=rp(pos,-H+1);p2=rp(pos,H-1)
                self.canvas.create_line(*p1,*p2,fill='#b17c47',width=2)
                pos+=step
"""
once(old_bridge,new_bridge,"rotatable bridge renderer")

# Expose angle in object properties. Existing projects without rotation default to zero.
once(
"""            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));self.field('Спрайт',o.get('asset',''),lambda v:self.val(o,'asset',v))
""",
"""            if o.get('kind')=='asset':
                self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v))
                self.field('Поворот (°)',round(o.get('rotation',0)),lambda v:self.num(o,'rotation',v))
                self.field('Спрайт',o.get('asset',''),lambda v:self.val(o,'asset',v))
            elif o.get('kind')=='bridge':
                self.field('Поворот (°)',round(o.get('rotation',0)),lambda v:self.num(o,'rotation',v))
""",
"rotation property field"
)

# Ensure Ctrl rotation is described in the UI help.
once(
"        ttk.Label(left,text='ЛКМ: выбор/рисование\\nСКМ: панорама\\nКолесо: масштаб\\nЛастик: зажмите ЛКМ и ведите').pack(padx=7,pady=5,anchor='w')",
"        ttk.Label(left,text='ЛКМ: выбор/рисование\\nCtrl+ЛКМ и ведение: поворот объекта\\nСКМ: панорама\\nКолесо: масштаб\\nЛандшафт: зажмите ЛКМ и ведите').pack(padx=7,pady=5,anchor='w')",
"rotation help"
)

p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("5.9.4 biome brush interpolation and object rotation patch applied; syntax check passed")
