from pathlib import Path
import re
import ast

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
MARK = "# MB_FEATURES_6_1_0_SHARED_LIBRARY_BATTLE_UI"
if MARK in s:
    print("6.1.0 shared library/UI patch already applied")
    raise SystemExit(0)

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)

# Shared image library: use a public Windows documents location so every Windows
# account using the same installation can see the same imported sprites/photos.
# Keep the old per-user library as a migration source.
old = """        self.user_asset_dir = Path(os.environ.get('APPDATA', str(Path.home()))) / 'MedievalBattlefieldEditor' / 'Sprites'
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
        self.custom_sprite_dir = self.user_asset_dir
"""
new = """        # MB_FEATURES_6_1_0_SHARED_LIBRARY_BATTLE_UI
        public_root = Path(os.environ.get('PUBLIC', str(Path.home()))) / 'Documents' / 'MedievalBattlefieldEditor'
        legacy_root = Path(os.environ.get('APPDATA', str(Path.home()))) / 'MedievalBattlefieldEditor'
        try:
            public_root.mkdir(parents=True, exist_ok=True)
            shared_dir = public_root / 'SharedSprites'
            shared_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            shared_dir = legacy_root / 'Sprites'
            shared_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_dir = shared_dir
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
        self.custom_sprite_dir = self.user_asset_dir
"""
once(old, new, "shared sprite directory")

# Migrate the old per-user library into the shared library once, without deleting it.
anchor = "        self.custom_sprite_meta_path = self.custom_sprite_dir / 'library.json'\n"
insert = """        self.custom_sprite_meta_path = self.custom_sprite_dir / 'library.json'
        self._migrate_legacy_sprite_library(legacy_root / 'Sprites')
"""
once(anchor, insert, "legacy sprite migration anchor")

# Add migration helper before save_sprite_meta().
anchor = "    def save_sprite_meta(self):\n"
method = """    def _migrate_legacy_sprite_library(self, legacy_dir):
        try:
            if not legacy_dir.is_dir() or legacy_dir.resolve() == self.custom_sprite_dir.resolve():
                return
            self.custom_sprite_meta = getattr(self, 'custom_sprite_meta', {})
            for src in legacy_dir.iterdir():
                if not src.is_file() or src.suffix.lower() not in ('.png','.webp','.jpg','.jpeg','.bmp','.gif'):
                    continue
                dst = self.custom_sprite_dir / src.name
                if not dst.exists():
                    shutil.copy2(src, dst)
                self.custom_sprite_meta.setdefault(src.stem, {'category':'other','source_name':src.name})
            legacy_meta = legacy_dir / 'library.json'
            if legacy_meta.is_file():
                try:
                    old_meta = json.loads(legacy_meta.read_text(encoding='utf-8'))
                    if isinstance(old_meta, dict):
                        for name, meta in old_meta.items():
                            if name in self.custom_sprite_meta:
                                self.custom_sprite_meta[name] = meta
                except Exception:
                    pass
        except Exception:
            # A failed migration must never prevent the editor from starting.
            pass

"""
if s.count(anchor) != 1: raise RuntimeError("save_sprite_meta anchor mismatch")
s = s.replace(anchor, method + anchor, 1)

# Add an explicit refresh button and shared-library path hint to the palette.
old = """        ttk.Button(sprite_buttons,text='⇧ Импорт набора',command=self.import_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(sprite_buttons,text='⇩ Экспорт набора',command=self.export_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
"""
new = """        ttk.Button(sprite_buttons,text='⇧ Импорт набора',command=self.import_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(sprite_buttons,text='⇩ Экспорт набора',command=self.export_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(sprite_buttons,text='⟳ Обновить',command=self.refresh_shared_sprite_library).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Label(self.palette,text='Общая библиотека: доступна всем пользователям этого ПК').pack(anchor='w',padx=5,pady=(0,3))
"""
once(old, new, "shared palette controls")

# Add a safe refresh method.
anchor = "    def export_sprite_pack(self):\n"
method = """    def refresh_shared_sprite_library(self):
        try:
            self.custom_sprite_meta_path = self.custom_sprite_dir / 'library.json'
            try:
                meta = json.loads(self.custom_sprite_meta_path.read_text(encoding='utf-8'))
                if isinstance(meta, dict):
                    self.custom_sprite_meta = meta
            except Exception:
                pass
            self.asset_pil_cache.clear()
            self.sprite_cache.clear()
            self.build_palette()
            self.status.set(f'Общая библиотека обновлена: {len(self.custom_sprite_names())} спрайтов.')
        except Exception as exc:
            messagebox.showwarning('Библиотека', str(exc), parent=self.root)

"""
if s.count(anchor) != 1: raise RuntimeError("export anchor mismatch")
s=s.replace(anchor,method+anchor,1)

# Generator variation: expose all compatible custom categories through asset_choices,
# while preserving the existing built-in fallback set and never touching road/river data.
old = """    def asset_choices(self,category,fallback):
        result=list(fallback)
        for name,meta in self.custom_sprite_meta.items():
            if not isinstance(meta,dict):continue
            cat=meta.get('category','other')
            if cat==category or (category=='nature' and cat in ('forest','field')) or (category=='buildings' and cat=='buildings'):
                result.append('user__'+name)
        return result or list(fallback)
"""
new = """    def asset_choices(self,category,fallback):
        result=list(fallback)
        for name,meta in self.custom_sprite_meta.items():
            if not isinstance(meta,dict):continue
            cat=str(meta.get('category','other')).lower()
            compatible = (
                cat == category
                or (category == 'nature' and cat in ('forest','field','nature'))
                or (category == 'buildings' and cat == 'buildings')
                or (category == 'decor' and cat in ('decor','other'))
            )
            if compatible:
                result.append('user__'+name)
        # De-duplicate while retaining stable order, so the generator genuinely
        # varies assets instead of repeatedly selecting the same imported file.
        return list(dict.fromkeys(result)) or list(fallback)
"""
once(old,new,"generator asset choices")

# Stable map boundary: use screen-pixel line widths so it remains visible at every zoom.
start = s.find("    def draw_map_boundary(self):")
if start < 0: raise RuntimeError("draw_map_boundary not found")
end = s.find("\n    def draw_line_obj(self,o):", start)
if end < 0: raise RuntimeError("draw_line_obj anchor after boundary not found")
boundary = """    def draw_map_boundary(self):
        # MB_FEATURES_6_1_0_SHARED_LIBRARY_BATTLE_UI
        world_w = int(getattr(self, 'world_w', getattr(self, 'WORLD_W', 8000)))
        world_h = int(getattr(self, 'world_h', getattr(self, 'WORLD_H', 5000)))
        x1, y1 = self.world_to_screen(0, 0)
        x2, y2 = self.world_to_screen(world_w, world_h)
        left, top, right, bottom = min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)

        # Widths are screen-pixel based, not world-scale based: zooming cannot
        # make the frame collapse or disappear.
        self.canvas.delete('map_boundary')
        self.canvas.create_rectangle(left, top, right, bottom,
            outline='#2f2118', width=8, tags=('map_boundary',))
        self.canvas.create_rectangle(left+5, top+5, right-5, bottom-5,
            outline='#8f6c3d', width=3, tags=('map_boundary',))
        self.canvas.create_rectangle(left+10, top+10, right-10, bottom-10,
            outline='#d4b77b', width=2, dash=(7,5), tags=('map_boundary',))

        span = 32
        for cx, cy, sx, sy in (
            (left+8, top+8, 1, 1),
            (right-8, top+8, -1, 1),
            (left+8, bottom-8, 1, -1),
            (right-8, bottom-8, -1, -1),
        ):
            self.canvas.create_line(cx, cy+sy*span, cx, cy, cx+sx*span, cy,
                fill='#5a3f26', width=4, tags=('map_boundary',))
            self.canvas.create_line(cx+sx*8, cy+sy*8, cx+sx*24, cy+sy*24,
                fill='#c19a58', width=2, tags=('map_boundary',))
            self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                fill='#8b6237', outline='#2f2118', width=2, tags=('map_boundary',))

        # Draw the frame above map content but keep it non-interactive.
        self.canvas.tag_lower('map_boundary')
"""
s = s[:start] + boundary + s[end:]

# Dedicated battle results: keep the existing battle mechanics, but make the
# result window reopenable and show a concise battle summary above the table.
old = """    def show_battle_results(self):
        win=tk.Toplevel(self.root);win.title('Журнал итогов сражений');win.geometry('820x480')
"""
new = """    def show_battle_results(self):
        win=tk.Toplevel(self.root);win.title('Итоги сражений');win.geometry('900x560')
        if self.battle_history:
            latest=self.battle_history[-1]
            ttk.Label(win,text=f"Последний бой: {latest['attacker']} против {latest['defender']}",
                      font=('Georgia',12,'bold')).pack(anchor='w',padx=10,pady=(8,2))
            ttk.Label(win,text=f"Победитель: {latest['winner']}  •  Проигравший: {latest['loser']}").pack(anchor='w',padx=10,pady=(0,8))
"""
once(old,new,"battle result window summary")

# Ensure the current battle result button is always accessible from the main UI.
anchor = "        ttk.Button(w,text='⚔ Провести бой',command=fight).pack(pady=14)\n"
if anchor not in s: raise RuntimeError("battle button anchor missing")
replacement = anchor + "        ttk.Button(w,text='Открыть журнал итогов',command=self.show_battle_results).pack(pady=(0,10))\n"
s=s.replace(anchor,replacement,1)

# Mark the feature without changing road or river methods.
s = MARK + "\n" + s
p.write_text(s,encoding='utf-8')
compile(s,str(p),'exec')
print('PASS: 6.1.0 shared sprite library, stable boundary, generator variants and battle UI patch')
