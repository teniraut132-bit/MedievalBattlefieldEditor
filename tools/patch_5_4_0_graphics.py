from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
if "# MB_GFX_5_4_0" in s:
    print("5.4.0 graphics patch already applied")
    raise SystemExit(0)

def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    s = s.replace(old, new, 1)

replace_once(
    "LABELS=dict(TOOLS)\n",
    """LABELS=dict(TOOLS)
# MB_GFX_5_4_0
TERRAINS = {
    'Луг':       {'color':'#a5b47e','edge':'#78865a','mark':'#d2d6a0','style':'grass'},
    'Лес':       {'color':'#627d58','edge':'#3e5a40','mark':'#8ca273','style':'forest'},
    'Пустыня':   {'color':'#d8bf88','edge':'#b29561','mark':'#f0d9a0','style':'desert'},
    'Пашня':     {'color':'#ad9167','edge':'#806746','mark':'#d4b887','style':'field'},
    'Болото':    {'color':'#788f7c','edge':'#4d6d62','mark':'#a9b59a','style':'marsh'},
    'Скалы':     {'color':'#8f8b7d','edge':'#625f57','mark':'#c2bba8','style':'rock'},
    'Редколесье':{'color':'#8b9a69','edge':'#64734d','mark':'#b3bd83','style':'scrub'},
    'Снег':      {'color':'#d5d8cf','edge':'#a8b0ac','mark':'#f5f1df','style':'snow'},
}
""",
    "terrain definitions"
)

replace_once(
    "self.undo_stack=[];self.redo_stack=[];self.tkimg={};self.sprite_cache={};self.asset_pil_cache={};self.project_tmp=None",
    "self.undo_stack=[];self.redo_stack=[];self.tkimg={};self.sprite_cache={};self.asset_pil_cache={};self.project_tmp=None;self.terrain_type='Луг';self.ground_tile=None",
    "initial graphics state"
)

replace_once(
    "ttk.Button(vf,text='Очистить природный слой',command=self.clear_nature).pack(fill='x',padx=3,pady=3)\n",
    """ttk.Button(vf,text='Очистить природный слой',command=self.clear_nature).pack(fill='x',padx=3,pady=3)
        tf=ttk.LabelFrame(left,text='Текстуры ландшафта');tf.pack(fill='x',pady=4)
        ttk.Label(tf,text='Выбери тип и закрашивай карту кистью').pack(anchor='w',padx=4,pady=(2,3))
        for i,name in enumerate(TERRAINS):
            b=ttk.Button(tf,text=name,command=lambda n=name:self.set_terrain(n))
            b.grid(row=i//2,column=i%2,sticky='ew',padx=2,pady=2)
        tf.columnconfigure(0,weight=1);tf.columnconfigure(1,weight=1)
""",
    "terrain palette UI"
)

replace_once(
    "    def brush_update(self):self.brush=int(self.brushvar.get());self.brushlabel.config(text=f'Размер: {self.brush}')\n",
    """    def set_terrain(self,name):
        self.terrain_type=name
        self.set_tool('terrain')
        self.status.set(f'Ландшафт: {name} — рисуйте ЛКМ; размер кисти слева')

    def brush_update(self):self.brush=int(self.brushvar.get());self.brushlabel.config(text=f'Размер: {self.brush}')
""",
    "terrain selector"
)

# Replace the complete renderer because the earlier road patches add
# road-network passes to render(), so the original renderer text no longer matches.
render_patch = """    def render(self):
        self._render_revision += 1
        self.canvas.delete('all')
        w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())
        self.canvas.create_rectangle(0,0,w,h,fill='#b8a97c',outline='',tags='background')
        self._draw_ground_texture(w,h)
        rect=self._visible_world_rect()
        # Paint biome strokes first, then water, road underlays and road surfaces.
        for o in self.objects:
            if o.get('kind')=='terrain' and self._bbox_visible(o,rect):
                self.draw_terrain_obj(o)
        for o in self.objects:
            if o.get('kind')=='river' and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
        self.draw_road_network_underlay()
        for o in self.objects:
            if o.get('kind')=='road' and self._bbox_visible(o,rect):
                self.draw_line_obj(o)
        self.draw_road_junctions()
        self.draw_junctions()
        for o in self.objects:
            if o.get('kind') not in ('river','road','terrain') and self._bbox_visible(o,rect):
                self.draw_obj(o)
        for u in self.units:
            if rect[0]-100 <= u['x'] <= rect[2]+100 and rect[1]-100 <= u['y'] <= rect[3]+100:
                self.draw_unit(u)
        if self.selected:
            self.draw_selection(self.selected[1])

"""
render_pattern = re.compile(r"(?ms)^    def render\(self\):\n.*?(?=^    def pts\(self,p\):)")
# The pattern above is intentionally line-anchored; keep class methods after render untouched.
m = render_pattern.search(s)
if not m:
    raise RuntimeError("Could not locate render() method before pts()")
s = s[:m.start()] + render_patch + s[m.end():]


replace_once(
    "        if o.get('kind') in ('river','road'):\n",
    "        if o.get('kind') in ('river','road','terrain'):\n",
    "terrain viewport bounds"
)

insert_before = "    def draw_line_obj(self,o):\n"
terrain_methods = """    def _draw_ground_texture(self,w,h):
        # A reusable illustrated parchment/grass tile. The tile remains aligned
        # to world coordinates while the camera pans.
        if self.ground_tile is None:
            from PIL import ImageDraw
            rng=random.Random(540)
            tile=Image.new('RGB',(128,128),'#b8ad83')
            d=ImageDraw.Draw(tile)
            for _ in range(1050):
                x=rng.randrange(128);y=rng.randrange(128)
                c=rng.choice(['#b1a57a','#c3b78e','#a99f76','#c8bd96','#ada27a'])
                r=rng.choice([1,1,1,2])
                d.ellipse((x-r,y-r,x+r,y+r),fill=c)
            for _ in range(28):
                x=rng.randrange(128);y=rng.randrange(128)
                d.line((x,y,x+rng.randrange(-5,6),y+rng.randrange(3,10)),fill='#a59a70',width=1)
            self.ground_tile=ImageTk.PhotoImage(tile)
        tw=128;th=128
        ox=(w/2+self.pan_x-WORLD_W/2*self.scale)%tw
        oy=(h/2+self.pan_y-WORLD_H/2*self.scale)%th
        y=oy-th
        while y<h+th:
            x=ox-tw
            while x<w+tw:
                self.canvas.create_image(x,y,image=self.ground_tile,anchor='nw',tags=('ground_texture',))
                x+=tw
            y+=th

    def draw_terrain_obj(self,o):
        pts=o.get('points',[])
        if not pts:return
        style=TERRAINS.get(o.get('terrain','Луг'),TERRAINS['Луг'])
        p=self.pts(pts);wd=max(3,int(o.get('width',100)*self.scale))
        # Dark, uneven edge makes painted biomes blend like inked map regions.
        if len(p)>=4:
            self.canvas.create_line(*p,fill=style['edge'],width=wd+max(2,int(10*self.scale)),smooth=True,capstyle='round',joinstyle='round')
            self.canvas.create_line(*p,fill=style['color'],width=wd,smooth=True,capstyle='round',joinstyle='round')
        else:
            x,y=self.world_to_screen(*pts[0]);r=wd/2
            self.canvas.create_oval(x-r,y-r,x+r,y+r,fill=style['color'],outline=style['edge'])
        # Small hand-drawn marks give each terrain a distinct readable texture.
        if self.scale < .16:return
        rng=random.Random(sum(ord(c) for c in str(o.get('id','')))+len(pts)*37)
        spacing=max(30,int(72/max(.2,self.scale)))
        for i,(wx,wy) in enumerate(pts):
            if i and math.hypot(wx-pts[i-1][0],wy-pts[i-1][1])<spacing:continue
            sx,sy=self.world_to_screen(wx,wy)
            for _ in range(3 if self.scale<.35 else 6):
                jx=rng.uniform(-wd*.28,wd*.28);jy=rng.uniform(-wd*.28,wd*.28)
                x=sx+jx;y=sy+jy;rr=max(1,min(3.5,self.scale*2.2))
                if style['style']=='field':
                    self.canvas.create_line(x-rr*2,y+rr,x+rr*2,y-rr,fill=style['mark'],width=1)
                elif style['style'] in ('forest','scrub'):
                    self.canvas.create_oval(x-rr,y-rr,x+rr,y+rr,fill=style['mark'],outline=style['edge'],width=1)
                elif style['style']=='rock':
                    self.canvas.create_line(x-rr,y+rr,x,y-rr,x+rr,y+rr,fill=style['mark'],width=1)
                elif style['style']=='marsh':
                    self.canvas.create_oval(x-rr*1.7,y-rr*.7,x+rr*1.7,y+rr*.7,outline=style['mark'],width=1)
                else:
                    self.canvas.create_oval(x-rr/2,y-rr/2,x+rr/2,y+rr/2,fill=style['mark'],outline='')

"""
if s.count(insert_before) != 1:
    raise RuntimeError("draw_line_obj insertion point missing")
s=s.replace(insert_before,terrain_methods+insert_before,1)

replace_once(
    "        if self.tool in ('river','road'):\n            self.snapshot();self.stroke=[(x,y)];return\n",
    """        if self.tool=='terrain':
            self.snapshot();self.stroke=[(x,y)];self.last=(x,y);return
        if self.tool in ('river','road'):
            self.snapshot();self.stroke=[(x,y)];return
""",
    "terrain stroke start"
)

replace_once(
    "        elif self.tool in ('river','road') and self.stroke is not None:\n            if math.hypot(x-self.stroke[-1][0],y-self.stroke[-1][1])>12:self.stroke.append((x,y));self.preview()\n",
    """        elif self.tool=='terrain' and self.stroke is not None:
            if math.hypot(x-self.stroke[-1][0],y-self.stroke[-1][1])>max(12,self.brush*.12):self.stroke.append((x,y));self.preview()
        elif self.tool in ('river','road') and self.stroke is not None:
            if math.hypot(x-self.stroke[-1][0],y-self.stroke[-1][1])>12:self.stroke.append((x,y));self.preview()
""",
    "terrain stroke drag"
)

replace_once(
    "    def left_up(self,e):\n        if self.tool in ('river','road') and self.stroke and len(self.stroke)>1:\n",
    """    def left_up(self,e):
        if self.tool=='terrain' and self.stroke:
            if len(self.stroke)==1:self.stroke.append(self.stroke[0])
            self.objects.append({'id':self.oid(),'kind':'terrain','terrain':self.terrain_type,'points':self.stroke,'width':max(80,self.brush)})
            self.stroke=None;self.render();self.refresh()
        elif self.tool in ('river','road') and self.stroke and len(self.stroke)>1:
""",
    "terrain stroke finish"
)

replace_once(
    "            p=self.pts(self.stroke);self.canvas.create_line(*p,fill='#55aaa3' if self.tool=='river' else '#9e8055',width=max(3,int(self.brush*.5*self.scale)),smooth=True,capstyle='round',dash=(6,4))\n",
    """            if self.tool=='terrain':
                style=TERRAINS.get(self.terrain_type,TERRAINS['Луг'])
                p=self.pts(self.stroke);self.canvas.create_line(*p,fill=style['color'],width=max(3,int(self.brush*self.scale)),smooth=True,capstyle='round',dash=(4,3))
            else:
                p=self.pts(self.stroke);self.canvas.create_line(*p,fill='#55aaa3' if self.tool=='river' else '#9e8055',width=max(3,int(self.brush*.5*self.scale)),smooth=True,capstyle='round',dash=(6,4))
""",
    "terrain preview"
)

replace_once(
    "            if o['kind'] in ('river','road'):\n                for a,b in zip(o['points'],o['points'][1:]):\n                    if self.segdist((x,y),a,b)<o.get('width',25)*1.5:return ('object',o)\n",
    """            if o['kind'] in ('river','road','terrain'):
                for a,b in zip(o['points'],o['points'][1:]):
                    if self.segdist((x,y),a,b)<o.get('width',25)*1.5:return ('object',o)
""",
    "terrain hit test"
)

replace_once(
    "            if o.get('kind') in ('river','road'):\n                hit=any(self.segdist((x,y),a,b) <= max(radius,o.get('width',25)*1.5)\n",
    "            if o.get('kind') in ('river','road','terrain'):\n                hit=any(self.segdist((x,y),a,b) <= max(radius,o.get('width',25)*1.5)\n",
    "terrain eraser"
)

replace_once(
    "        names={'asset':'Спрайт','river':'🌊 Река','road':'🛣 Дорога','bridge':'🌉 Мост','settlement':'🏘 Поселение'}\n",
    "        names={'asset':'Спрайт','river':'🌊 Река','road':'🛣 Дорога','terrain':'Ландшафт: ','bridge':'🌉 Мост','settlement':'🏘 Поселение'}\n",
    "terrain layer labels"
)

replace_once(
    "            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));self.field('Спрайт',o.get('asset',''),lambda v:self.val(o,'asset',v))\n",
    """            if o.get('kind')=='asset':self.field('Размер',o.get('size',100),lambda v:self.num(o,'size',v));self.field('Спрайт',o.get('asset',''),lambda v:self.val(o,'asset',v))
            if o.get('kind')=='terrain':self.field('Тип ландшафта',o.get('terrain','Луг'),lambda v:self.val(o,'terrain',v));self.field('Ширина кисти',o.get('width',100),lambda v:self.num(o,'width',v))
""",
    "terrain properties"
)

# Keep old projects valid while writing the new schema version.
replace_once("    def serial(self):return {'version':5,", "    def serial(self):return {'version':6,", "project schema version")

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("PASS: 5.4.0 graphics patch applied and Python syntax compiles")
