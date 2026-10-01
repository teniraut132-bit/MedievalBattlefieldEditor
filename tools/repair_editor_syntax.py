from pathlib import Path
import re
import ast

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# 5.2.6: replace the final rendering section with a single canonical version.
# The previous 5.2.x road patches could create visual junction circles and the
# sprite renderer was too implicit for frozen PyInstaller builds.

render_re = re.compile(
    r"(?ms)^[ 	]*def render\(self\):\r?\n.*?(?=^[ 	]*def pts\(self,p\):)"
)
m = render_re.search(s)
if not m:
    raise RuntimeError("Could not locate render() before pts()")

base_m = re.search(r"(?m)^([ 	]*)def pts\(self,p\):", s[m.start():])
if not base_m:
    raise RuntimeError("Could not determine class indentation")
base = base_m.group(1)

render_body = [
    "def render(self):",
    "    self._render_revision += 1",
    "    self.canvas.delete('all')",
    "    w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())",
    "    self.canvas.create_rectangle(0,0,w,h,fill='#b8a97c',outline='',tags='background')",
    "    rect=self._visible_world_rect()",
    "",
    "    # Z-order is intentional: water first, roads second. This makes a",
    "    # road crossing a river read as one uninterrupted road, with no",
    "    # circular junction marker and no river painted over the road.",
    "    for o in self.objects:",
    "        if o.get('kind')=='river' and self._bbox_visible(o,rect):",
    "            self.draw_line_obj(o)",
    "    self.draw_road_network_underlay()",
    "    for o in self.objects:",
    "        if o.get('kind')=='road' and self._bbox_visible(o,rect):",
    "            self.draw_line_obj(o)",
    "    self.draw_road_junctions()",
    "",
    "    for o in self.objects:",
    "        if o.get('kind') not in ('river','road') and self._bbox_visible(o,rect):",
    "            self.draw_obj(o)",
    "    for u in self.units:",
    "        if rect[0]-100 <= u['x'] <= rect[2]+100 and rect[1]-100 <= u['y'] <= rect[3]+100:",
    "            self.draw_unit(u)",
    "    if self.selected:",
    "        self.draw_selection(self.selected[1])",
]
s = s[:m.start()] + "\n".join(base + line for line in render_body) + "\n" + s[m.end():]

section_re = re.compile(
    r"(?ms)^[ 	]*def pts\(self,p\):.*?(?=^[ 	]*def draw_asset\(self,o\):)"
)
m = section_re.search(s)
if not m:
    raise RuntimeError("Could not locate pts()/road methods section")

road_body = [
    "def pts(self,p):",
    "    return [v for x,y in p for v in self.world_to_screen(x,y)]",
    "",
    "def draw_line_obj(self,o):",
    "    p=self.pts(o.get('points',[]));wd=o.get('width',25)*self.scale",
    "    if not p:return",
    "    if o.get('kind')=='river':",
    "        self.canvas.create_line(*p,fill='#4b4238',width=max(8,int(wd+32*self.scale)),smooth=True,capstyle='round')",
    "        self.canvas.create_line(*p,fill='#4fa8a2',width=max(5,int(wd)),smooth=True,capstyle='round')",
    "        self.canvas.create_line(*p,fill='#8ccbc1',width=max(1,int(3*self.scale)),smooth=True)",
    "        return",
    "    rt=o.get('road_type','Просёлочная')",
    "    colors={'Просёлочная':('#624b37','#b79a70','#dbc79f'),'Мощенная':('#51483e','#756b5d','#b9ad96'),'Брусчаточная':('#4a3b2d','#8b7b67','#c5b69a')}",
    "    edge,surf,detail=colors.get(rt,colors['Просёлочная'])",
    "    self.canvas.create_line(*p,fill=edge,width=max(5,int(wd+12*self.scale)),smooth=True,capstyle='round')",
    "    self.canvas.create_line(*p,fill=surf,width=max(3,int(wd)),smooth=True,capstyle='round')",
    "    dash=(2,5) if rt=='Брусчаточная' else (7,6) if rt=='Мощенная' else ()",
    "    self.canvas.create_line(*p,fill=detail,width=max(1,int(wd*.13)),smooth=True,capstyle='round',dash=dash)",
    "",
    "def line_segments(self,o):",
    "    pts=o.get('points',[])",
    "    return list(zip(pts,pts[1:]))",
    "",
    "def closest_on_seg(self,p,a,b):",
    "    x,y=p;x1,y1=a;x2,y2=b;dx=x2-x1;dy=y2-y1",
    "    if dx==dy==0:return a,math.hypot(x-x1,y-y1)",
    "    t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))",
    "    q=(x1+t*dx,y1+t*dy)",
    "    return q,math.hypot(x-q[0],y-q[1])",
    "",
    "def snap_line_endpoints(self,kind,points):",
    "    out=list(points);threshold=130 if kind=='river' else 90",
    "    for idx in (0,-1):",
    "        best=None",
    "        for o in self.objects:",
    "            if o.get('kind')!=kind:continue",
    "            for a,b in self.line_segments(o):",
    "                q,d=self.closest_on_seg(out[idx],a,b)",
    "                if d<=threshold and (best is None or d<best[0]):best=(d,q)",
    "        if best:out[idx]=best[1]",
    "    return out",
    "",
    "def seg_intersection(self,a,b,c,d):",
    "    x1,y1=a;x2,y2=b;x3,y3=c;x4,y4=d",
    "    den=(x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)",
    "    if abs(den)<1e-9:return None",
    "    px=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/den",
    "    py=((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/den",
    "    if (min(x1,x2)-1<=px<=max(x1,x2)+1 and min(y1,y2)-1<=py<=max(y1,y2)+1 and",
    "        min(x3,x4)-1<=px<=max(x3,x4)+1 and min(y3,y4)-1<=py<=max(y3,y4)+1):",
    "        return px,py",
    "    return None",
    "",
    "def draw_road_network_underlay(self):",
    "    # Only the dark road foundation is drawn here. It is placed after",
    "    # rivers, so even the foundation cannot sit visibly on top of water.",
    "    roads=[o for o in self.objects if o.get('kind')=='road']",
    "    for o in roads:",
    "        p=self.pts(o.get('points',[]));wd=o.get('width',25)*self.scale",
    "        if p:",
    "            self.canvas.create_line(*p,fill='#4a3b2d',width=max(5,int(wd+10*self.scale)),smooth=True,capstyle='round')",
    "",
    "def draw_road_junctions(self):",
    "    # Deliberately no circle/point is painted at intersections.",
    "    # Roads are already drawn in full width over the river and over other",
    "    # roads, so the crossing itself is a normal piece of road.",
    "    return",
    "",
    "def draw_junctions(self):",
    "    return self.draw_road_junctions()",
    "",
    "def draw_obj(self,o):",
    "    if o['kind']=='bridge':",
    "        x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale",
    "        self.canvas.create_rectangle(x-L/2,y-12*self.scale,x+L/2,y+12*self.scale,fill='#68462e',outline='#302117',width=3)",
    "        for xx in range(int(x-L/2+8),int(x+L/2),max(8,int(18*self.scale))):",
    "            self.canvas.create_line(xx,y-11*self.scale,xx,y+11*self.scale,fill='#b17c47',width=2)",
    "    elif o['kind']=='settlement':",
    "        x,y=self.world_to_screen(o['x'],o['y'])",
    "        self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,outline='#655039',dash=(8,5),width=2)",
    "        self.canvas.create_text(x,y-420*self.scale,text=o.get('name','Поселение'),font=('Georgia',max(9,int(18*self.scale)),'bold'),fill='#38291e')",
    "    elif o['kind']=='asset':",
    "        self.draw_asset(o)",
    "    elif o['kind']=='tree':",
    "        self.draw_asset({'asset':o['asset'],'x':o['x'],'y':o['y'],'size':o.get('size',70)})",
]
s = s[:m.start()] + "\n".join(base + line for line in road_body) + "\n" + s[m.end():]

# Replace the sprite renderer with a frozen-build-safe implementation.
asset_re = re.compile(
    r"(?ms)^[ 	]*def draw_asset\(self,o\):\r?\n.*?(?=^[ 	]*def draw_unit\(self,u\):)"
)
m = asset_re.search(s)
if not m:
    raise RuntimeError("Could not locate draw_asset()")

asset_body = [
    "def draw_asset(self,o):",
    "    name=o.get('asset')",
    "    if not name:return",
    "    im=self.asset_pil(name)",
    "    if im is None:",
    "        # Never silently lose an object: draw a visible placeholder.",
    "        x,y=self.world_to_screen(o.get('x',0),o.get('y',0));r=max(8,o.get('size',100)*self.scale*.35)",
    "        self.canvas.create_oval(x-r,y-r,x+r,y+r,fill='#8d3f2f',outline='#2c2118',width=2,tags=('obj',o.get('id','')))",
    "        self.canvas.create_text(x,y,text='?',fill='white',font=('Arial',max(8,int(10*self.scale)),'bold'))",
    "        return",
    "    x,y=self.world_to_screen(o.get('x',0),o.get('y',0))",
    "    target=max(12,min(1400,int(o.get('size',100)*self.scale)))",
    "    key=(name,target)",
    "    photo=self.sprite_cache.get(key)",
    "    if photo is None:",
    "        ratio=min(target/im.width,target/im.height)",
    "        res=im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio))),Image.Resampling.LANCZOS)",
    "        photo=ImageTk.PhotoImage(res,master=self.root)",
    "        self.sprite_cache[key]=photo",
    "        self.tkimg[key]=photo",
    "    self.canvas.create_image(x,y,image=photo,anchor='center',tags=('obj',o.get('id','')))",
]
s = s[:m.start()] + "\n".join(base + line for line in asset_body) + "\n" + s[m.end():]

# Make asset loading deterministic and validate all embedded sprites.
asset_pil_re = re.compile(
    r"(?ms)^[ 	]*def asset_pil\(self,name\):\r?\n.*?(?=^[ 	]*def place_asset\(self,name\):)"
)
m = asset_pil_re.search(s)
if not m:
    raise RuntimeError("Could not locate asset_pil()")

asset_pil_body = [
    "def asset_pil(self,name):",
    "    if name in self.asset_pil_cache:return self.asset_pil_cache[name]",
    "    key=self.asset_key(name)",
    "    if not key:return None",
    "    try:",
    "        raw=__import__('base64').b64decode(ASSETS[key])",
    "        im=Image.open(io.BytesIO(raw)).convert('RGBA')",
    "        if im.width<2 or im.height<2:return None",
    "        self.asset_pil_cache[name]=im",
    "        return im",
    "    except Exception:",
    "        return None",
]
s = s[:m.start()] + "\n".join(base + line for line in asset_pil_body) + "\n" + s[m.end():]

# Give palette buttons a tiny thumbnail when possible. This also exercises the
# exact same embedded sprite path used by the map renderer.
palette_re = re.compile(
    r"(?ms)^[ 	]*def build_palette\(self\):\r?\n.*?(?=^[ 	]*def asset_key\(self,name\):)"
)
m = palette_re.search(s)
if not m:
    raise RuntimeError("Could not locate build_palette()")

palette_body = [
    "def build_palette(self):",
    "    for w in self.palette_frame.winfo_children():w.destroy()",
    "    self.palette_imgs={}",
    "    cats=[('Здания',['house_wood_01','house_wood_02','house_stone_01','house_stone_02','tower_01','keep_01','church_01','gate_01','mill_01','barn_01','barn_02']),('Природа',['tree_01','tree_02','tree_03','rock_01','rock_02','rock_03','field_01','field_02','field_03','bush_01','bush_02','bush_03']),('Декор',['wagon_01','hay_01'])]",
    "    for title,names in cats:",
    "        ttk.Label(self.palette_frame,text=title,font=('Arial',10,'bold')).pack(anchor='w',padx=4,pady=(4,1))",
    "        row=ttk.Frame(self.palette_frame);row.pack(fill='x')",
    "        for name in names:",
    "            if self.asset_key(name) is None:continue",
    "            im=self.asset_pil(name)",
    "            photo=None",
    "            if im is not None:",
    "                thumb=im.copy();thumb.thumbnail((46,34),Image.Resampling.LANCZOS)",
    "                photo=ImageTk.PhotoImage(thumb,master=self.root);self.palette_imgs[name]=photo",
    "            b=ttk.Button(row,text=name.replace('_',' ').replace('01','1').replace('02','2').replace('03','3'),image=photo,compound='top' if photo else 'none',command=lambda n=name:self.place_asset(n))",
    "            b.pack(side='left',padx=2,pady=2)",
]
s = s[:m.start()] + "\n".join(base + line for line in palette_body) + "\n" + s[m.end():]


# 5.2.7: normalize embedded sprite names and render line networks by layers.
# This makes branches merge without circular junction marks or dark underlay
# dots, and makes asset lookup independent of path/suffix variations.
render_re = re.compile(r"(?ms)^[ \t]*def render\(self\):\r?\n.*?(?=^[ \t]*def pts\(self,p\):)")
m = render_re.search(s)
if not m:
    raise RuntimeError("Could not locate render() for layered network rendering")
base_m = re.search(r"(?m)^([ \t]*)def pts\(self,p\):", s[m.start():])
base = base_m.group(1)
render_body = [
    "def render(self):",
    "    self._render_revision += 1",
    "    self.canvas.delete('all')",
    "    w=max(1,self.canvas.winfo_width());h=max(1,self.canvas.winfo_height())",
    "    self.canvas.create_rectangle(0,0,w,h,fill='#b8a97c',outline='',tags='background')",
    "    rect=self._visible_world_rect()",
    "    rivers=[o for o in self.objects if o.get('kind')=='river' and self._bbox_visible(o,rect)]",
    "    roads=[o for o in self.objects if o.get('kind')=='road' and self._bbox_visible(o,rect)]",
    "    # Draw each network as global layers: all outlines, then all surfaces,",
    "    # then all fine details. Branches merge as continuous shapes, not dots.",
    "    for layer in ('outline','surface','detail'):",
    "        for o in rivers:self.draw_line_obj(o,layer)",
    "    for layer in ('outline','surface','detail'):",
    "        for o in roads:self.draw_line_obj(o,layer)",
    "    for o in self.objects:",
    "        if o.get('kind') not in ('river','road') and self._bbox_visible(o,rect):self.draw_obj(o)",
    "    for u in self.units:",
    "        if rect[0]-100 <= u['x'] <= rect[2]+100 and rect[1]-100 <= u['y'] <= rect[3]+100:self.draw_unit(u)",
    "    if self.selected:self.draw_selection(self.selected[1])",
]
s=s[:m.start()]+"\n".join(base+line for line in render_body)+"\n"+s[m.end():]

line_re = re.compile(r"(?ms)^[ \t]*def draw_line_obj\(self,o.*?\):\r?\n.*?(?=^[ \t]*def line_segments\(self,o\):)")
m=line_re.search(s)
if not m: raise RuntimeError("Could not locate draw_line_obj()")
base=re.match(r"^([ \t]*)",m.group(0)).group(1)
line_body=[
"def draw_line_obj(self,o,layer='all'):",
"    p=self.pts(o.get('points',[]))",
"    if len(p)<4:return",
"    wd=max(1,o.get('width',25)*self.scale)",
"    layers=('outline','surface','detail') if layer=='all' else (layer,)",
"    if o.get('kind')=='river':",
"        specs={'outline':('#4b4238',wd+32*self.scale),'surface':('#4fa8a2',wd),'detail':('#8ccbc1',max(1,3*self.scale))}",
"        for part in layers:",
"            color,width=specs[part]",
"            self.canvas.create_line(*p,fill=color,width=max(1,int(width)),smooth=True,capstyle='round',joinstyle='round')",
"        return",
"    rt=o.get('road_type','Просёлочная')",
"    colors={'Просёлочная':('#624b37','#b79a70','#dbc79f'),'Мощенная':('#51483e','#756b5d','#b9ad96'),'Брусчаточная':('#4a3b2d','#8b7b67','#c5b69a')}",
"    edge,surf,detail=colors.get(rt,colors['Просёлочная'])",
"    specs={'outline':(edge,wd+12*self.scale),'surface':(surf,wd),'detail':(detail,max(1,wd*.13))}",
"    for part in layers:",
"        color,width=specs[part]",
"        dash=(2,5) if part=='detail' and rt=='Брусчаточная' else (7,6) if part=='detail' and rt=='Мощенная' else ()",
"        self.canvas.create_line(*p,fill=color,width=max(1,int(width)),smooth=True,capstyle='round',joinstyle='round',dash=dash)",
]
s=s[:m.start()]+"\n".join(base+line for line in line_body)+"\n"+s[m.end():]

asset_re = re.compile(r"(?ms)^[ \t]*def asset_pil\(self,name\):\r?\n.*?(?=^[ \t]*def place_asset\(self,name\):)")
m=asset_re.search(s)
if not m: raise RuntimeError("Could not locate asset_pil() for robust lookup")
base=re.match(r"^([ \t]*)",m.group(0)).group(1)
asset_body=[
"def asset_pil(self,name):",
"    # Normalize both bare asset names and paths such as terrain/tree_01.png.",
"    normalized=Path(str(name)).stem.lower()",
"    if normalized in self.asset_pil_cache:return self.asset_pil_cache[normalized]",
"    key=next((k for k in ASSETS if Path(k).stem.lower()==normalized),None)",
"    if not key:return None",
"    try:",
"        raw=__import__('base64').b64decode(ASSETS[key],validate=True)",
"        im=Image.open(io.BytesIO(raw)).convert('RGBA')",
"        im.load()",
"        if im.width<2 or im.height<2:return None",
"        self.asset_pil_cache[normalized]=im",
"        return im",
"    except Exception as exc:",
"        if not hasattr(self,'asset_load_errors'):self.asset_load_errors={}",
"        self.asset_load_errors[normalized]=repr(exc)",
"        return None",
]
s=s[:m.start()]+"\n".join(base+line for line in asset_body)+"\n"+s[m.end():]


# 5.2.8: normalize asset aliases so "tree_01", "tree 1", and
# "tree1.png" resolve to the same embedded resource key.
asset_key_re = re.compile(
    r"(?ms)^[ \t]*def asset_key\(self,name\):\r?\n.*?(?=^[ \t]*def place_asset\(self,name\):)"
)
m = asset_key_re.search(s)
if not m:
    raise RuntimeError("Could not locate asset_key()")
base = re.match(r"^([ \t]*)",m.group(0)).group(1)
asset_key_body = [
    "def asset_key(self,name):",
    "    def normalize(value):",
    "        value=str(value).replace('\\\\','/').rsplit('/',1)[-1]",
    "        if '.' in value:value=value.rsplit('.',1)[0]",
    "        value=''.join(ch.lower() for ch in value if ch.isalnum())",
    "        split=len(value)",
    "        while split>0 and value[split-1].isdigit():split-=1",
    "        prefix,digits=value[:split],value[split:]",
    "        if digits:digits=str(int(digits))",
    "        return prefix+digits",
    "    target=normalize(name)",
    "    for key in ASSETS.keys():",
    "        if normalize(key)==target:return key",
    "    return None",
]
s=s[:m.start()]+"\n".join(base+line for line in asset_key_body)+"\n"+s[m.end():]

tree=ast.parse(s,filename=str(p))
app=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App'),None)
if app is None:raise RuntimeError("App class not found")
methods={n.name for n in app.body if isinstance(n,ast.FunctionDef)}
required={'render','draw_line_obj','line_segments','closest_on_seg','snap_line_endpoints','seg_intersection','draw_road_network_underlay','draw_road_junctions','draw_junctions','draw_obj','draw_asset','asset_pil','build_palette'}
missing=required-methods
if missing:raise RuntimeError("Missing App methods: "+", ".join(sorted(missing)))
p.write_text(s,encoding='utf-8')
compile(s,str(p),'exec')
print("5.2.8 renderer/sprite alias repair passed syntax and App-method validation")
