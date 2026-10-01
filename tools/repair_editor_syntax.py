from pathlib import Path
import re
import ast

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# Final canonical renderer. Earlier road patches were intentionally made
# independent, but the released 5.2.x builds proved too fragile when several
# patches touched the same methods. Rebuild the complete render/road section
# here so the packaged editor always contains the methods that render() calls.

render_re = re.compile(
    r"(?ms)^[ \t]*def render\(self\):\r?\n.*?(?=^[ \t]*def pts\(self,p\):)"
)
m = render_re.search(s)
if not m:
    raise RuntimeError("Could not locate render() before pts()")

base_m = re.search(r"(?m)^([ \t]*)def pts\(self,p\):", s[m.start():])
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
    "    # Road underlay closes seams before the visible road strokes.",
    "    self.draw_road_network_underlay()",
    "    for o in self.objects:",
    "        if o.get('kind') in ('river','road') and self._bbox_visible(o,rect):",
    "            self.draw_line_obj(o)",
    "    self.draw_road_junctions()",
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
    r"(?ms)^[ \t]*def pts\(self,p\):.*?(?=^[ \t]*def draw_asset\(self,o\):)"
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
    "    roads=[o for o in self.objects if o.get('kind')=='road']",
    "    for o in roads:",
    "        p=self.pts(o.get('points',[]));wd=o.get('width',25)*self.scale",
    "        if p:",
    "            self.canvas.create_line(*p,fill='#4a3b2d',width=max(5,int(wd+10*self.scale)),smooth=True,capstyle='round')",
    "",
    "def draw_road_junctions(self):",
    "    roads=[o for o in self.objects if o.get('kind')=='road']",
    "    for i,a in enumerate(roads):",
    "        for b in roads[i+1:]:",
    "            radius=max(4,(a.get('width',25)+b.get('width',25))*0.55*self.scale)",
    "            for sa,sb in self.line_segments(a):",
    "                for sc,sd in self.line_segments(b):",
    "                    q=self.seg_intersection(sa,sb,sc,sd)",
    "                    if not q:continue",
    "                    x,y=self.world_to_screen(*q)",
    "                    self.canvas.create_oval(x-radius,y-radius,x+radius,y+radius,fill='#9b8567',outline='')",
    "",
    "# Compatibility alias for older patched calls.",
    "def draw_junctions(self):",
    "    self.draw_road_junctions()",
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

tree=ast.parse(s,filename=str(p))
app=next((n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App'),None)
if app is None: raise RuntimeError("App class not found")
methods={n.name for n in app.body if isinstance(n,ast.FunctionDef)}
required={'render','draw_line_obj','line_segments','closest_on_seg','snap_line_endpoints','seg_intersection','draw_road_network_underlay','draw_road_junctions','draw_junctions','draw_obj','draw_asset'}
missing=required-methods
if missing: raise RuntimeError("Missing App methods after repair: "+", ".join(sorted(missing)))

p.write_text(s,encoding='utf-8')
compile(s,str(p),'exec')
print("Final renderer repair passed syntax and App-method validation")
