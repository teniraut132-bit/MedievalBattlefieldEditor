from pathlib import Path
p=Path('editor/Medieval_Battlefield_Editor_v4.py')
s=p.read_text(encoding='utf-8')
start=s.index('    def draw_line_obj(self,o):')
end=s.index('    def draw_obj(self,o):',start)
new='''    def draw_line_obj(self,o):
        p=self.pts(o['points']);wd=o.get('width',25)*self.scale
        if o['kind']=='river':
            self.canvas.create_line(*p,fill='#4b4238',width=max(8,int(wd+32*self.scale)),smooth=True,capstyle='round')
            self.canvas.create_line(*p,fill='#4fa8a2',width=max(5,int(wd)),smooth=True,capstyle='round')
            self.canvas.create_line(*p,fill='#8ccbc1',width=max(1,int(3*self.scale)),smooth=True)
            return
        rt=o.get('road_type','Просёлочная')
        colors={'Просёлочная':('#b79a70','#dbc79f'),'Мощенная':('#756b5d','#b9ad96'),'Брусчаточная':('#8b7b67','#c5b69a')}
        surf,detail=colors.get(rt,colors['Просёлочная'])
        self.canvas.create_line(*p,fill=surf,width=max(3,int(wd)),smooth=True,capstyle='round')
        dash=(2,5) if rt=='Брусчаточная' else (7,6) if rt=='Мощенная' else ()
        self.canvas.create_line(*p,fill=detail,width=max(1,int(wd*.13)),smooth=True,capstyle='round',dash=dash)

    def line_segments(self,o):
        pts=o.get('points',[])
        return list(zip(pts,pts[1:]))

    def closest_on_seg(self,p,a,b):
        x,y=p; x1,y1=a; x2,y2=b
        dx=x2-x1; dy=y2-y1
        if dx==dy==0:
            return a,math.hypot(x-x1,y-y1)
        t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))
        q=(x1+t*dx,y1+t*dy)
        return q,math.hypot(x-q[0],y-q[1])

    def snap_line_endpoints(self,kind,points):
        out=list(points)
        threshold=130 if kind=='river' else 90
        for idx in (0,-1):
            best=None
            for o in self.objects:
                if o.get('kind')!=kind:
                    continue
                for a,b in self.line_segments(o):
                    q,d=self.closest_on_seg(out[idx],a,b)
                    if d<=threshold and (best is None or d<best[0]):
                        best=(d,q)
            if best:
                out[idx]=best[1]
        return out

    def seg_intersection(self,a,b,c,d):
        x1,y1=a; x2,y2=b; x3,y3=c; x4,y4=d
        den=(x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
        if abs(den)<1e-9:
            return None
        px=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/den
        py=((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/den
        if (min(x1,x2)-1<=px<=max(x1,x2)+1 and
            min(y1,y2)-1<=py<=max(y1,y2)+1 and
            min(x3,x4)-1<=px<=max(x3,x4)+1 and
            min(y3,y4)-1<=py<=max(y3,y4)+1):
            return px,py
        return None

    def draw_road_network_underlay(self):
        roads=[o for o in self.objects if o.get('kind')=='road']
        for o in roads:
            p=self.pts(o.get('points',[]));wd=o.get('width',25)*self.scale
            self.canvas.create_line(*p,fill='#4a3b2d',width=max(5,int(wd+10*self.scale)),smooth=True,capstyle='round')

    def draw_road_junctions(self):
        roads=[o for o in self.objects if o.get('kind')=='road']
        for i,a in enumerate(roads):
            for b in roads[i+1:]:
                ra=max(3,a.get('width',25)*self.scale*.50);rb=max(3,b.get('width',25)*self.scale*.50)
                radius=max(ra,rb)+3*self.scale
                for sa,sb in self.line_segments(a):
                    for sc,sd in self.line_segments(b):
                        q=self.seg_intersection(sa,sb,sc,sd)
                        if q:
                            x,y=self.world_to_screen(*q)
                            self.canvas.create_oval(x-radius,y-radius,x+radius,y+radius,fill='#9b8567',outline='')

'''
s=s[:start]+new+s[end:]
needle='        self.draw_junctions()
        for o in self.objects:'
replacement='        self.draw_road_network_underlay()
        for o in self.objects:
            if o.get('kind')=='road' and self._bbox_visible(o,rect): self.draw_line_obj(o)
        self.draw_road_junctions()
        self.draw_junctions()
        for o in self.objects:'
if needle in s:
    s=s.replace(needle,replacement)
s=s.replace("return {'version':6,","return {'version':7,")
p.write_text(s,encoding='utf-8')
