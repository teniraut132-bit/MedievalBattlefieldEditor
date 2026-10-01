from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
if "# MB_CARTOGRAPHY_5_6_0" in s:
    print("5.6.0 cartography patch already applied")
    raise SystemExit(0)

def replace_once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)

# Store imported user art beside the editor, not in a temporary extraction directory.
replace_once(
    "        self._render_pending=False;self._render_after=None;self._render_revision=0\n",
    """        self._render_pending=False;self._render_after=None;self._render_revision=0
        # MB_CARTOGRAPHY_5_6_0
        asset_root = Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
        if asset_root.name.lower() == 'editor':asset_root = asset_root.parent
        self.user_asset_dir = asset_root / 'user_assets'
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
        self.palette_images = []
""",
    "user asset storage"
)

replace_once(
    "        self.palette_canvas=tk.Canvas(self.palette,height=260,highlightthickness=0);self.palette_canvas.pack(fill='x');self.palette_frame=ttk.Frame(self.palette_canvas);self.palette_canvas.create_window((0,0),window=self.palette_frame,anchor='nw');self.build_palette()\n",
    """        pal_head=ttk.Frame(self.palette);pal_head.pack(fill='x')
        ttk.Button(pal_head,text='＋ Импортировать спрайт',command=self.import_map_sprite).pack(side='left',fill='x',expand=True,padx=3,pady=3)
        self.palette_canvas=tk.Canvas(self.palette,height=300,highlightthickness=0)
        pal_scroll=ttk.Scrollbar(self.palette,orient='vertical',command=self.palette_canvas.yview)
        self.palette_canvas.configure(yscrollcommand=pal_scroll.set)
        pal_scroll.pack(side='right',fill='y');self.palette_canvas.pack(side='left',fill='both',expand=True)
        self.palette_frame=ttk.Frame(self.palette_canvas)
        self.palette_window=self.palette_canvas.create_window((0,0),window=self.palette_frame,anchor='nw')
        self.palette_frame.bind('<Configure>',lambda e:self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox('all')))
        self.palette_canvas.bind('<Configure>',lambda e:self.palette_canvas.itemconfigure(self.palette_window,width=e.width))
        self.palette_canvas.bind('<MouseWheel>',lambda e:self.palette_canvas.yview_scroll(int(-e.delta/120),'units'))
        self.build_palette()
""",
    "scrollable object library"
)

start = s.index("    def build_palette(self):")
end = s.index("    def asset_key(self,name):", start)
new_palette = '''    def build_palette(self):
        # MB_CARTOGRAPHY_5_6_0 — one scrollable catalogue for built-in and user art.
        for w in self.palette_frame.winfo_children():w.destroy()
        self.palette_images=[]
        cats=[
            ('Здания',['house_wood_01','house_wood_02','house_stone_01','house_stone_02','tower_01','keep_01','church_01','gate_01','mill_01','barn_01','barn_02']),
            ('Природа',['tree_01','tree_02','tree_03','rock_01','rock_02','rock_03','field_01','field_02','field_03','bush_01','bush_02','bush_03']),
            ('Декор',['wagon_01','hay_01'])
        ]
        for title,names in cats:
            ttk.Label(self.palette_frame,text=title,font=('Arial',10,'bold')).pack(anchor='w',padx=4,pady=(5,2))
            row=None
            for i,name in enumerate(names):
                if not self.asset_key(name):continue
                if i%3==0:
                    row=ttk.Frame(self.palette_frame);row.pack(fill='x',padx=2)
                im=self.asset_pil(name)
                kw={}
                if im is not None:
                    thumb=im.copy();thumb.thumbnail((42,42),Image.Resampling.LANCZOS)
                    photo=ImageTk.PhotoImage(thumb);self.palette_images.append(photo);kw['image']=photo;kw['compound']='top'
                b=ttk.Button(row,text=name.replace('_',' ').replace('01','1').replace('02','2').replace('03','3'),
                             command=lambda n=name:self.place_asset(n),**kw)
                b.pack(side='left',fill='both',expand=True,padx=2,pady=2)
        custom=[]
        for path in sorted(self.user_asset_dir.iterdir(),key=lambda x:x.name.lower()):
            if path.is_file() and path.suffix.lower() in ('.png','.webp','.jpg','.jpeg'):
                custom.append(path)
        ttk.Label(self.palette_frame,text=f'Пользовательские спрайты ({len(custom)})',font=('Arial',10,'bold')).pack(anchor='w',padx=4,pady=(7,2))
        if not custom:
            ttk.Label(self.palette_frame,text='Нажмите «Импортировать спрайт», чтобы добавить PNG/WebP/JPG.').pack(anchor='w',padx=5,pady=3)
        for start_i in range(0,len(custom),3):
            row=ttk.Frame(self.palette_frame);row.pack(fill='x',padx=2)
            for path in custom[start_i:start_i+3]:
                name='custom:'+path.name
                kw={}
                im=self.asset_pil(name)
                if im is not None:
                    thumb=im.copy();thumb.thumbnail((42,42),Image.Resampling.LANCZOS)
                    photo=ImageTk.PhotoImage(thumb);self.palette_images.append(photo);kw['image']=photo;kw['compound']='top'
                ttk.Button(row,text=path.stem[:18],command=lambda n=name:self.place_asset(n),**kw).pack(side='left',fill='both',expand=True,padx=2,pady=2)

    def import_map_sprite(self):
        files=filedialog.askopenfilenames(
            title='Импортировать спрайты карты',
            filetypes=[('Изображения','*.png *.webp *.jpg *.jpeg'),('Все файлы','*.*')])
        if not files:return
        added=0
        for src in files:
            try:
                src=Path(src)
                # Decode before copying so corrupt/unsupported files never enter the catalogue.
                with Image.open(src) as im:
                    im.verify()
                target=self.user_asset_dir/src.name
                if target.exists():
                    target=self.user_asset_dir/(src.stem+'_import'+src.suffix.lower())
                shutil.copy2(src,target)
                self.user_asset_pil_cache.pop(target.name,None)
                added+=1
            except Exception as exc:
                messagebox.showwarning('Не удалось импортировать',f'{src.name}: {exc}')
        self.build_palette()
        self.status.set(f'Импортировано спрайтов: {added}')

'''
s = s[:start] + new_palette + s[end:]

# The syntax-repair pass normalizes asset_pil() and inserts _write_sprite_error().
# Inject custom-file decoding before the existing embedded-asset lookup.
needle = "    def asset_pil(self,name):\\n        key=self.asset_key(name)\\n"
replacement = """    def asset_pil(self,name):
        if isinstance(name,str) and name.startswith('custom:'):
            filename=name.split(':',1)[1]
            if filename in self.user_asset_pil_cache:return self.user_asset_pil_cache[filename]
            path=self.user_asset_dir/filename
            try:
                with Image.open(path) as source:im=source.convert('RGBA')
                self.user_asset_pil_cache[filename]=im
                return im
            except Exception as exc:
                self._write_sprite_error(name,type(exc).__name__+': '+str(exc))
                return None
        key=self.asset_key(name)
"""
if s.count(needle) != 1:
    raise RuntimeError(f"custom sprite decoding: expected one normalized asset_pil anchor, found {s.count(needle)}")
s = s.replace(needle, replacement, 1)

# Render connected paths as layered ribbons and remove decorative circular junction stamps.
line_method = '''    def draw_line_obj(self,o):
        pts=o.get('points',[])
        if len(pts)<2:return
        p=self.pts(pts)
        wd=max(1.0,float(o.get('width',25))*self.scale)
        if o['kind']=='river':
            # Bank, water, then a restrained highlight. Round caps and joins make
            # connected segments flow into each other instead of forming dots.
            self.canvas.create_line(*p,fill='#4b4238',width=max(5,int(wd+28*self.scale)),
                                    smooth=True,capstyle='round',joinstyle='round')
            self.canvas.create_line(*p,fill='#4fa8a2',width=max(3,int(wd)),
                                    smooth=True,capstyle='round',joinstyle='round')
            if wd*self.scale > 7:
                self.canvas.create_line(*p,fill='#83c7bd',width=max(1,int(1.5*self.scale)),
                                        smooth=True,capstyle='round',joinstyle='round')
        else:
            # The dark roadbed is drawn before the lighter compacted surface.
            self.canvas.create_line(*p,fill='#514437',width=max(5,int(wd+10*self.scale)),
                                    smooth=True,capstyle='round',joinstyle='round')
            self.canvas.create_line(*p,fill='#b7a080',width=max(3,int(wd)),
                                    smooth=True,capstyle='round',joinstyle='round')
            if wd*self.scale > 8:
                self.canvas.create_line(*p,fill='#d7c29b',width=max(1,int(1.4*self.scale)),
                                        smooth=True,capstyle='round',joinstyle='round')

'''
pattern = re.compile(r"(?ms)^    def draw_line_obj\(self,o\):\n.*?(?=^    def draw_obj\(self,o\):)")
m = pattern.search(s)
if not m:raise RuntimeError("Could not locate draw_line_obj()")
s=s[:m.start()]+line_method+s[m.end():]

# Junction circles are what create the visible round dots at crossings.
# Keep network underlays, but do not stamp circles over their joins.
s=s.replace("        self.draw_road_junctions()\n","        # Junctions are blended by overlapping ribbon strokes; no circle stamps.\n")
s=s.replace("        self.draw_junctions()\n","        # No decorative junction dots: continuous line ribbons form the joins.\n")

p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("Applied 5.6.0 cartography patch; Python syntax check passed")
