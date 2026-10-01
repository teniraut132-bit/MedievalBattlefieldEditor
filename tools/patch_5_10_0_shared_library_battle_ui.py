from pathlib import Path
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
MARK="# MB_5_10_0_SHARED_LIBRARY_AND_BATTLE_UI"
if MARK in s:
    print("5.10.0 feature patch already applied")
    raise SystemExit(0)

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s=s.replace(old,new,1)

# ---------------------------------------------------------------------------
# Shared sprite/photo library
# ---------------------------------------------------------------------------
old="""        # MB_FEATURES_5_9_6: stable per-user library survives launcher updates.
        self.user_asset_dir = Path(os.environ.get('APPDATA', str(Path.home()))) / 'MedievalBattlefieldEditor' / 'Sprites'
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
        self.custom_sprite_dir = self.user_asset_dir
        self.custom_sprite_meta_path = self.custom_sprite_dir / 'library.json'
        try:self.custom_sprite_meta=json.loads(self.custom_sprite_meta_path.read_text(encoding='utf-8'))
        except Exception:self.custom_sprite_meta={}
"""
new="""        # MB_5_10_0_SHARED_LIBRARY_AND_BATTLE_UI:
        # Keep imported art outside the installation so launcher updates never
        # erase it, and put it in a machine-shared Public folder so different
        # Windows users of the editor see the same library.
        public_root=Path(os.environ.get('PUBLIC', str(Path.home())))
        shared_root=public_root/'Documents'/'Medieval Battlefield Editor'
        try:
            shared_root.mkdir(parents=True,exist_ok=True)
        except Exception:
            shared_root=Path(os.environ.get('APPDATA', str(Path.home())))/'MedievalBattlefieldEditor'
            shared_root.mkdir(parents=True,exist_ok=True)
        self.shared_library_root=shared_root
        self.user_asset_dir=shared_root/'SharedSprites'
        self.user_asset_dir.mkdir(parents=True,exist_ok=True)
        self.shared_photo_dir=shared_root/'SharedPhotos'
        self.shared_photo_dir.mkdir(parents=True,exist_ok=True)
        self.user_asset_pil_cache={}
        self.custom_sprite_dir=self.user_asset_dir
        self.custom_sprite_meta_path=self.custom_sprite_dir/'library.json'
        try:self.custom_sprite_meta=json.loads(self.custom_sprite_meta_path.read_text(encoding='utf-8'))
        except Exception:self.custom_sprite_meta={}
        self.migrate_legacy_sprite_library()
"""
once(old,new,"shared library storage")

# Insert migration before the existing custom_sprite_names method.
anchor="    def custom_sprite_names(self):"
if s.count(anchor)!=1: raise RuntimeError("custom_sprite_names anchor mismatch")
migration="""    def migrate_legacy_sprite_library(self):
        # 5.9.x stored custom art in the current Windows user's APPDATA.
        # Copy it once into the shared library without deleting the old files.
        try:
            legacy=Path(os.environ.get('APPDATA', str(Path.home())))/'MedievalBattlefieldEditor'/'Sprites'
            if legacy.resolve()==self.custom_sprite_dir.resolve() or not legacy.exists():
                return
            changed=False
            for src in legacy.iterdir():
                if not src.is_file() or src.name=='library.json':
                    continue
                target=self.custom_sprite_dir/src.name
                if not target.exists():
                    shutil.copy2(src,target);changed=True
            old_meta=legacy/'library.json'
            if old_meta.exists():
                try:
                    data=json.loads(old_meta.read_text(encoding='utf-8'))
                    if isinstance(data,dict):
                        for k,v in data.items():
                            self.custom_sprite_meta.setdefault(k,v)
                        changed=True
                except Exception:
                    pass
            if changed:self.save_sprite_meta()
        except Exception:
            # A failed migration must never stop the editor from starting.
            pass

"""
s=s.replace(anchor,migration+anchor,1)

# Shared unit photos: imported photos are copied to the shared library.
old_import="""    def import_unit_image(self,u=None):
        if u is None:
            if not self.selected or self.selected[0]!='unit':self.add_unit()
            u=self.selected[1]
        p=filedialog.askopenfilename(filetypes=[('Изображения','*.png *.webp *.jpg *.jpeg *.bmp *.gif'),('Все файлы','*.*')])
        if not p:return
        self.snapshot();u['image']=os.path.abspath(p);u['image_size']=110;self.tkimg.clear();self.selected=('unit',u);self.show_props();self.render();self.status.set('Изображение подключено без изменения исходного файла.')
"""
new_import="""    def store_shared_photo(self,src_path):
        src=Path(src_path)
        try:
            with Image.open(src) as im:im.load()
            stem=re.sub(r'[^A-Za-z0-9_-]+','_',src.stem).strip('_')[:56] or 'photo'
            target=self.shared_photo_dir/(stem+src.suffix.lower())
            idx=2
            while target.exists():
                target=self.shared_photo_dir/(f'{stem}_{idx}'+src.suffix.lower());idx+=1
            shutil.copy2(src,target)
            return str(target)
        except Exception:
            return os.path.abspath(src_path)

    def import_unit_image(self,u=None):
        if u is None:
            if not self.selected or self.selected[0]!='unit':self.add_unit()
            u=self.selected[1]
        p=filedialog.askopenfilename(filetypes=[('Изображения','*.png *.webp *.jpg *.jpeg *.bmp *.gif'),('Все файлы','*.*')])
        if not p:return
        self.snapshot()
        u['image']=self.store_shared_photo(p)
        u['image_size']=110
        self.tkimg.clear();self.selected=('unit',u);self.show_props();self.render()
        self.status.set('Фотография добавлена в общую библиотеку пользователей.')
"""
once(old_import,new_import,"shared unit photos")

# ---------------------------------------------------------------------------
# Stable, always-visible map frame. Do not touch road/river renderers.
# ---------------------------------------------------------------------------
boundary_pat=re.compile(r"(?ms)^    # MB_MAP_BOUNDARY_5_9_5\n    def draw_map_boundary\(self\):\n.*?(?=^    def draw_line_obj\(self,o\):)")
bm=boundary_pat.search(s)
if not bm:
    raise RuntimeError("Could not locate 5.9.5 map boundary method")
boundary="""    # MB_5_10_0_SHARED_LIBRARY_AND_BATTLE_UI
    def draw_map_boundary(self):
        # Fixed screen-pixel widths keep the frame visually stable at every zoom.
        # Use the current global map dimensions, so custom map sizes are framed too.
        world_w,world_h=WORLD_W,WORLD_H
        x1,y1=self.world_to_screen(0,0);x2,y2=self.world_to_screen(world_w,world_h)
        left,top,right,bottom=min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)
        outer=9
        middle=4
        inner=2
        self.canvas.create_rectangle(left,top,right,bottom,outline='#2e2118',width=outer,tags=('map_boundary',))
        self.canvas.create_rectangle(left+11,top+11,right-11,bottom-11,outline='#8b693d',width=middle,tags=('map_boundary',))
        self.canvas.create_rectangle(left+18,top+18,right-18,bottom-18,outline='#d3b879',width=inner,dash=(6,5),tags=('map_boundary',))
        span=34
        for cx,cy,sx,sy in ((left+11,top+11,1,1),(right-11,top+11,-1,1),
                            (left+11,bottom-11,1,-1),(right-11,bottom-11,-1,-1)):
            self.canvas.create_line(cx,cy+sy*span,cx,cy,cx+sx*span,cy,fill='#5d4026',width=4,tags=('map_boundary',))
            self.canvas.create_line(cx+sx*7,cy+sy*7,cx+sx*24,cy+sy*24,fill='#b28b50',width=2,tags=('map_boundary',))
            self.canvas.create_oval(cx-3,cy-3,cx+3,cy+3,fill='#8b6237',outline='#2e2118',width=2,tags=('map_boundary',))
        self.canvas.create_text(left+48,top+17,text='✦ КАРТА ПОЛЯ БИТВЫ ✦',anchor='nw',
            fill='#493421',font=('Georgia',11,'bold'),tags=('map_boundary',))

"""
s=s[:bm.start()]+boundary+s[bm.end():]

# ---------------------------------------------------------------------------
# Make the existing battle model more explicit about equipment + weapon impact
# and expose percentage breakdowns in the result window.
# ---------------------------------------------------------------------------
# The 5.9.6 battle method already applies training, morale, weapons and armor.
# Add an explicit power line to the stored result without changing road/water data.
old_result="""            result={
                'time':__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'attacker':A['name'],'defender':B['name'],'winner':winner['name'],'loser':loser['name'],
"""
new_result="""            result={
                'time':__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'attacker':A['name'],'defender':B['name'],'winner':winner['name'],'loser':loser['name'],
                'power_ratio':round(max(sa,sb)/max(1,min(sa,sb)),2),
"""
once(old_result,new_result,"battle power result")

# Show battle result as percentages as well as absolute losses.
old_tree="""                    f"−{unit['casualties']} / {unit['remaining']}",
                    f"−{unit['gear_damage']}% → {unit['gear_remaining']}%",
"""
new_tree="""                    f"−{unit['casualties']} ({unit['casualties']/max(1,unit['men'])*100:.1f}%) / {unit['remaining']}",
                    f"−{unit['gear_damage']}% → {unit['gear_remaining']}%",
"""
once(old_tree,new_tree,"battle percentage display")

# Mark the new code before writing so a rebuild cannot double-patch.
s=MARK+"\n"+s
p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("5.10.0 shared library, stable boundary and battle result patch passed syntax check")
