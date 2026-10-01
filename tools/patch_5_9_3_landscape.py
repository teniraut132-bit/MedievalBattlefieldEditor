from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
if "# MB_LANDSCAPE_5_9_3" in s:
    print("5.9.3 landscape patch already applied")
    raise SystemExit(0)

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)

# Add a dedicated terrain panel. These tools paint only biome overlays; the road
# and river tools, their geometry, and their renderer are intentionally untouched.
once(
"""        ttk.Label(left,text='ЛКМ: выбор/рисование\\nСКМ: панорама\\nКолесо: масштаб\\nЛастик: зажмите ЛКМ и ведите\\nShift+ЛКМ: не менять выбор').pack(padx=7,pady=5,anchor='w')
""",
"""        ttk.Label(left,text='ЛКМ: выбор/рисование\\nСКМ: панорама\\nКолесо: масштаб\\nЛастик: зажмите ЛКМ и ведите').pack(padx=7,pady=5,anchor='w')
        # MB_LANDSCAPE_5_9_3: biome brush tools are separate from roads and rivers.
        bio=ttk.LabelFrame(left,text='Текстуры ландшафта')
        bio.pack(fill='x',pady=(2,5))
        for row in (('Луг','meadow'),('Лес','forest'),('Пустыня','desert'),('Пашня','farmland'),
                    ('Болото','swamp'),('Скалы','rocky'),('Речные отмели','riverbank'),('Снег','snow')):
            ttk.Button(bio,text=row[0],command=lambda k=row[1]:self.set_tool('biome:'+k)).pack(fill='x',padx=3,pady=1)
""",
"terrain tool panel"
)

# Friendly status text for terrain tools.
once(
"    def set_tool(self,k):self.tool=k;self.status.set('Инструмент: '+LABELS.get(k,k));self.canvas.configure(cursor='hand2' if k in ('select','pan') else 'crosshair')",
"""    def set_tool(self,k):
        self.tool=k
        biome_labels={'meadow':'Луг','forest':'Лес','desert':'Пустыня','farmland':'Пашня','swamp':'Болото','rocky':'Скалы','riverbank':'Речные отмели','snow':'Снег'}
        label=('Ландшафт: '+biome_labels.get(k.split(':',1)[1],k) if k.startswith('biome:') else LABELS.get(k,k))
        self.status.set('Инструмент: '+label)
        self.canvas.configure(cursor='hand2' if k in ('select','pan') else 'crosshair')""",
"terrain tool labels"
)

# Route mouse clicks and drags to the biome brush before the generic prop painter.
once(
"""        self.snapshot();self.paint(self.tool,x,y)
    def left_drag(self,e):
""",
"""        if self.tool.startswith('biome:'):
            self.snapshot();self.last=None;self.paint_biome(self.tool.split(':',1)[1],x,y);self.last=(x,y);return
        self.snapshot();self.paint(self.tool,x,y)
    def left_drag(self,e):
""",
"biome click handler"
)

once(
"""        elif self.tool in ('forest','tree'):
            if self.last is None or math.hypot(x-self.last[0],y-self.last[1])>self.brush*.5:self.paint(self.tool,x,y)
        self.last=(x,y)
""",
"""        elif self.tool in ('forest','tree'):
            if self.last is None or math.hypot(x-self.last[0],y-self.last[1])>self.brush*.5:self.paint(self.tool,x,y)
        elif self.tool.startswith('biome:'):
            spacing=max(12,self.brush*.28)
            if self.last is None or math.hypot(x-self.last[0],y-self.last[1])>spacing:
                self.paint_biome(self.tool.split(':',1)[1],x,y)
        self.last=(x,y)
""",
"biome drag handler"
)

# Render the terrain beneath roads/rivers and objects. Existing road/river calls
# remain in their original order and are not changed by this patch.
once(
"""        rect=self._visible_world_rect()
        # Draw only objects intersecting the current viewport.
""",
"""        rect=self._visible_world_rect()
        # MB_LANDSCAPE_5_9_3: terrain is an underlay; rivers and roads are drawn above it.
        self.draw_biome_layer(rect)
        # Draw only objects intersecting the current viewport.
""",
"terrain render layer"
)

# Insert biome methods before draw_line_obj; no changes to draw_line_obj itself.
anchor = "    def draw_line_obj(self,o):"
if s.count(anchor) != 1:
    raise RuntimeError("draw_line_obj insertion anchor mismatch")
methods = '''    # MB_LANDSCAPE_5_9_3
    BIOME_STYLE = {
        'meadow': ('#87966a','#9ba77a'),
        'forest': ('#526b4d','#647b59'),
        'desert': ('#c7ad72','#d5bc83'),
        'farmland': ('#9b805e','#b09a70'),
        'swamp': ('#65785b','#78876a'),
        'rocky': ('#858071','#a09a87'),
        'riverbank': ('#b8aa85','#c9bb96'),
        'snow': ('#d5d4c7','#e5e3d7'),
    }

    def paint_biome(self,biome,x,y):
        if biome not in self.BIOME_STYLE:return
        radius=max(30,int(self.brush/2))
        self.objects.append({'id':self.oid(),'kind':'biome','biome':biome,
                             'x':x,'y':y,'radius':radius,
                             'seed':random.randrange(1,2**31-1)})
        self.render()

    def draw_biome_layer(self,rect):
        for o in self.objects:
            if o.get('kind')!='biome':continue
            r=o.get('radius',75);x=o.get('x',0);y=o.get('y',0)
            if x+r<rect[0] or x-r>rect[2] or y+r<rect[1] or y-r>rect[3]:continue
            colors=self.BIOME_STYLE.get(o.get('biome'))
            if not colors:continue
            rng=random.Random(o.get('seed',0))
            count=24
            points=[]
            for i in range(count):
                a=2*math.pi*i/count
                rr=r*rng.uniform(.78,1.12)
                points.extend(self.world_to_screen(x+math.cos(a)*rr,y+math.sin(a)*rr))
            self.canvas.create_polygon(*points,fill=colors[0],outline='',smooth=True,tags=('biome',o['id']))
            # A low-contrast inset wash adds cartographic texture without outlines,
            # avoiding seams between adjacent brush stamps of the same biome.
            inset=[]
            for i in range(count):
                a=2*math.pi*i/count
                rr=r*rng.uniform(.28,.68)
                inset.extend(self.world_to_screen(x+math.cos(a)*rr,y+math.sin(a)*rr))
            self.canvas.create_polygon(*inset,fill=colors[1],outline='',smooth=True,stipple='gray50',tags=('biome',o['id']))

'''
s=s.replace(anchor,methods+anchor,1)

# Biome stamps must be selectable and erasable like other map objects.
once(
"""        for o in reversed(self.objects):
            if 'x' in o and abs(x-o['x'])<max(80,o.get('size',100)/2) and abs(y-o['y'])<max(70,o.get('size',100)/2):return ('object',o)
""",
"""        for o in reversed(self.objects):
            if o.get('kind')=='biome' and math.hypot(x-o.get('x',0),y-o.get('y',0))<=o.get('radius',75):return ('object',o)
            if 'x' in o and abs(x-o['x'])<max(80,o.get('size',100)/2) and abs(y-o['y'])<max(70,o.get('size',100)/2):return ('object',o)
""",
"biome hit testing"
)

# Don't render a biome overlay as a sprite or a default object.
once(
"""        elif o['kind']=='asset':self.draw_asset(o)
        elif o['kind']=='tree':self.draw_asset({'asset':o['asset'],'x':o['x'],'y':o['y'],'size':o.get('size',70)})
""",
"""        elif o['kind']=='asset':self.draw_asset(o)
        elif o['kind']=='tree':self.draw_asset({'asset':o['asset'],'x':o['x'],'y':o['y'],'size':o.get('size',70)})
        elif o['kind']=='biome':return
""",
"biome object dispatch"
)

p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("Landscape brush patch applied; Python syntax check passed")
