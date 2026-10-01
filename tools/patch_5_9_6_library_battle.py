from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")
marker = "# MB_FEATURES_5_9_6"
if marker in s:
    print("5.9.6 feature patch already applied")
    raise SystemExit(0)

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)

# Imports and per-user persistent sprite library. The library is stored outside
# the install directory, so launcher updates do not delete it.
once("from tkinter import ttk, filedialog, messagebox",
     "from tkinter import ttk, filedialog, messagebox, simpledialog",
     "simpledialog import")
once("        self._render_pending=False;self._render_after=None;self._render_revision=0\n",
"""        self._render_pending=False;self._render_after=None;self._render_revision=0
        # MB_FEATURES_5_9_6: battle result history.
        self.battle_history=[]
""", "battle history state")

once("""        self.user_asset_dir = asset_root / 'user_assets'
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
""",
"""        # MB_FEATURES_5_9_6: stable per-user library survives launcher updates.
        self.user_asset_dir = Path(os.environ.get('APPDATA', str(Path.home()))) / 'MedievalBattlefieldEditor' / 'Sprites'
        self.user_asset_dir.mkdir(parents=True, exist_ok=True)
        self.user_asset_pil_cache = {}
        self.custom_sprite_dir = self.user_asset_dir
        self.custom_sprite_meta_path = self.custom_sprite_dir / 'library.json'
        try:self.custom_sprite_meta=json.loads(self.custom_sprite_meta_path.read_text(encoding='utf-8'))
        except Exception:self.custom_sprite_meta={}
""", "persistent sprite storage")

# Compact tabbed tool shelf. Tool identifiers and all road/water drawing code remain unchanged.
start = s.index("        lf=ttk.LabelFrame(left,text='Инструменты')")
end = s.index("        center=ttk.Frame(body)", start)
replacement = """        # MB_FEATURES_5_9_6: compact category tabs instead of a long full-height tool list.
        toolbook=ttk.Notebook(left)
        toolbook.pack(fill='x', expand=False)
        tool_groups=[
            ('Выбор',[('↖ Выбор','select'),('✋ Панорама','pan'),('⌫ Ластик','erase')]),
            ('Дороги',[('🛣 Дорога','road')]),
            ('Вода',[('🌊 Река','river'),('🌉 Мост','bridge')]),
            ('Природа',[('🌲 Лес','forest'),('🌳 Дерево','tree'),('☘ Куст','bush'),('⛰ Скалы','rock')]),
            ('Здания',[('🏠 Дом','house'),('🗼 Башня','tower'),('🏰 Замок','keep'),('⛪ Церковь','church'),('🧱 Ворота','gate'),('⚙ Мельница','mill'),('🐄 Амбар','barn'),('🚚 Телега','wagon'),('✦ Сено','hay')]),
            ('Биомы',[('Луг','biome:meadow'),('Лес','biome:forest'),('Пустыня','biome:desert'),('Пашня','biome:farmland'),('Болото','biome:swamp'),('Скалы','biome:rocky'),('Отмели','biome:riverbank'),('Снег','biome:snow')])
        ]
        for tab_name, entries in tool_groups:
            tab=ttk.Frame(toolbook,padding=3)
            toolbook.add(tab,text=tab_name)
            for label,key in entries:
                ttk.Button(tab,text=label,command=lambda k=key:self.set_tool(k)).pack(fill='x',padx=1,pady=1)
        vf=ttk.LabelFrame(left,text='Кисть и вид')
        vf.pack(fill='x',pady=5)
        self.brushvar=tk.IntVar(value=150)
        ttk.Scale(vf,from_=30,to=350,variable=self.brushvar,orient='horizontal',command=lambda _:self.brush_update()).pack(fill='x',padx=4)
        self.brushlabel=ttk.Label(vf,text='Размер: 150');self.brushlabel.pack()
        zoomrow=ttk.Frame(vf);zoomrow.pack(fill='x')
        ttk.Button(zoomrow,text='＋',command=lambda:self.zoom(1.12)).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(zoomrow,text='−',command=lambda:self.zoom(.89)).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(zoomrow,text='Сброс',command=self.reset_view).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(vf,text='🗺 8000×5000',command=lambda:self.set_map_size(8000,5000)).pack(fill='x',padx=3,pady=2)
        ttk.Button(vf,text='Очистить природный слой',command=self.clear_nature).pack(fill='x',padx=3,pady=2)
        ttk.Label(left,text='ЛКМ: выбор/рисование\\\\nCtrl+ЛКМ: поворот объекта\\\\nСКМ: панорама\\\\nКолесо: масштаб\\\\nБиомы: рисуйте с зажатой ЛКМ',wraplength=190).pack(padx=5,pady=4,anchor='w')
"""
s = s[:start] + replacement + s[end:]

# Scrollable object library and controls for import/export packs.
once("""        pal_head=ttk.Frame(self.palette);pal_head.pack(fill='x')
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
"""        pal_head=ttk.Frame(self.palette);pal_head.pack(fill='x')
        ttk.Button(pal_head,text='＋ Импортировать спрайты',command=self.import_sprites).pack(side='left',fill='x',expand=True,padx=3,pady=3)
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
        sprite_buttons=ttk.Frame(self.palette);sprite_buttons.pack(fill='x',padx=3,pady=3)
        ttk.Button(sprite_buttons,text='⇧ Импорт набора',command=self.import_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
        ttk.Button(sprite_buttons,text='⇩ Экспорт набора',command=self.export_sprite_pack).pack(side='left',expand=True,fill='x',padx=1)
""", "scrollable sprite palette")

# Replace palette builder with categorized embedded + user sprites.
pat = re.compile(r"(?ms)^    def build_palette\(self\):\n.*?(?=^    def asset_key\(self,name\):)")
m = pat.search(s)
if not m: raise RuntimeError("Could not locate build_palette()")
build_palette = """    # MB_FEATURES_5_9_6
    def build_palette(self):
        for w in self.palette_frame.winfo_children():w.destroy()
        cats=[
            ('Здания','buildings',['house_wood_01','house_wood_02','house_stone_01','house_stone_02','tower_01','keep_01','church_01','gate_01','mill_01','barn_01','barn_02']),
            ('Природа','nature',['tree_01','tree_02','tree_03','rock_01','rock_02','rock_03','field_01','field_02','field_03','bush_01','bush_02','bush_03']),
            ('Декор','decor',['wagon_01','hay_01'])
        ]
        custom=self.custom_sprite_names()
        for title,category,names in cats:
            user_names=[n for n in custom if self.custom_sprite_meta.get(n,{}).get('category')==category]
            if not names and not user_names:continue
            ttk.Label(self.palette_frame,text=title,font=('Arial',10,'bold')).pack(anchor='w',padx=4,pady=(4,1))
            row=ttk.Frame(self.palette_frame);row.pack(fill='x')
            for name in names:
                if not any(k.endswith(name+'.png') for k in ASSETS):continue
                ttk.Button(row,text=name.replace('_',' ').replace('01','1').replace('02','2').replace('03','3'),command=lambda n=name:self.place_asset(n)).pack(side='left',padx=1,pady=1)
            for name in user_names:
                ttk.Button(row,text='★ '+name,command=lambda n='user__'+n:self.place_asset(n)).pack(side='left',padx=1,pady=1)
        # Any sprites without a known category remain visible in their own group.
        uncategorized=[n for n in custom if self.custom_sprite_meta.get(n,{}).get('category') not in ('buildings','nature','decor')]
        if uncategorized:
            ttk.Label(self.palette_frame,text='Пользовательские',font=('Arial',10,'bold')).pack(anchor='w',padx=4,pady=(4,1))
            for name in uncategorized:
                ttk.Button(self.palette_frame,text='★ '+name,command=lambda n='user__'+name:self.place_asset(n)).pack(fill='x',padx=2,pady=1)
        self.palette_frame.update_idletasks()
        self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox('all'))

    def custom_sprite_names(self):
        valid={'.png','.webp','.jpg','.jpeg','.bmp','.gif'}
        return sorted(p.stem for p in self.custom_sprite_dir.iterdir() if p.is_file() and p.suffix.lower() in valid)

    def save_sprite_meta(self):
        self.custom_sprite_meta_path.write_text(json.dumps(self.custom_sprite_meta,ensure_ascii=False,indent=2),encoding='utf-8')

    def import_sprites(self):
        files=filedialog.askopenfilenames(title='Добавить пользовательские спрайты',filetypes=[('Изображения','*.png *.webp *.jpg *.jpeg *.bmp *.gif')])
        if not files:return
        category=simpledialog.askstring('Категория спрайтов','Категория: buildings (здания), nature (природа), decor (декор), forest (лес), field (поля), other (прочее).',initialvalue='other',parent=self.root)
        if category is None:return
        category=category.strip().lower()
        if category not in ('buildings','nature','decor','forest','field','other'):category='other'
        added=0
        for src in files:
            try:
                with Image.open(src) as im:im.verify()
                source=Path(src);stem=re.sub(r'[^A-Za-z0-9_-]+','_',source.stem).strip('_')[:48] or 'sprite'
                dest_stem=stem;idx=2
                while any(p.stem.lower()==dest_stem.lower() for p in self.custom_sprite_dir.iterdir() if p.is_file()):
                    dest_stem=f'{stem}_{idx}';idx+=1
                dest=self.custom_sprite_dir/(dest_stem+source.suffix.lower())
                shutil.copy2(src,dest)
                self.custom_sprite_meta[dest_stem]={'category':category,'source_name':source.name}
                added+=1
            except Exception as exc:
                messagebox.showwarning('Спрайт пропущен',f'{Path(src).name}: {exc}',parent=self.root)
        self.save_sprite_meta();self.asset_pil_cache.clear();self.sprite_cache.clear();self.build_palette()
        self.status.set(f'В библиотеку добавлено спрайтов: {added}. Они сохраняются после обновления редактора.')

    def export_sprite_pack(self):
        names=self.custom_sprite_names()
        if not names:
            messagebox.showinfo('Библиотека спрайтов','Пользовательская библиотека пока пуста.',parent=self.root);return
        p=filedialog.asksaveasfilename(defaultextension='.mbsprites',filetypes=[('Набор спрайтов','*.mbsprites')],initialfile='MedievalBattlefield_Sprites.mbsprites')
        if not p:return
        with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(self.custom_sprite_meta_path,'library.json')
            for name in names:
                for file in self.custom_sprite_dir.glob(name+'.*'):
                    if file.suffix.lower() in ('.png','.webp','.jpg','.jpeg','.bmp','.gif'):z.write(file,'Sprites/'+file.name)
        self.status.set(f'Набор спрайтов экспортирован: {len(names)}')

    def import_sprite_pack(self):
        p=filedialog.askopenfilename(filetypes=[('Набор спрайтов','*.mbsprites *.zip')])
        if not p:return
        added=0
        try:
            with zipfile.ZipFile(p) as z:
                entries=[n for n in z.namelist() if Path(n).suffix.lower() in ('.png','.webp','.jpg','.jpeg','.bmp','.gif')]
                incoming={}
                try:incoming=json.loads(z.read('library.json').decode('utf-8'))
                except Exception:pass
                for entry in entries:
                    data=z.read(entry);stem=Path(entry).stem
                    dest_stem=stem;idx=2
                    while any(q.stem.lower()==dest_stem.lower() for q in self.custom_sprite_dir.iterdir() if q.is_file()):
                        dest_stem=f'{stem}_{idx}';idx+=1
                    ext=Path(entry).suffix.lower()
                    target=self.custom_sprite_dir/(dest_stem+ext)
                    target.write_bytes(data)
                    meta=incoming.get(stem,{'category':'other'})
                    self.custom_sprite_meta[dest_stem]=meta if isinstance(meta,dict) else {'category':'other'}
                    added+=1
            self.save_sprite_meta();self.asset_pil_cache.clear();self.sprite_cache.clear();self.build_palette()
            self.status.set(f'Импортировано общих спрайтов: {added}')
        except Exception as exc:messagebox.showerror('Ошибка набора спрайтов',str(exc),parent=self.root)

"""
s = s[:m.start()] + build_palette + s[m.end():]

# Custom asset loading is disk-backed and cached, never bundled into the executable.
once("""        key=self.asset_key(name)
""",
"""        if isinstance(name,str) and name.startswith('user__'):
            stem=name[6:]
            candidates=[q for q in self.custom_sprite_dir.glob(stem+'.*') if q.suffix.lower() in ('.png','.webp','.jpg','.jpeg','.bmp','.gif')]
            if candidates:
                try:
                    im=Image.open(candidates[0]).convert('RGBA');self.asset_pil_cache[name]=im;return im
                except Exception:return None
            return None
        key=self.asset_key(name)
""", "custom sprite loading")

# Let random generation and landscape painting use imported variants by category.
once("        assets=['house_wood_01','house_wood_02','house_stone_01','barn_01','mill_01']",
     "        assets=self.asset_choices('buildings',['house_wood_01','house_wood_02','house_stone_01','barn_01','mill_01'])",
     "generated building variation")
anchor="    def place_asset(self,name):"
if s.count(anchor)!=1:raise RuntimeError("place_asset insertion anchor mismatch")
s=s.replace(anchor,"""    def asset_choices(self,category,fallback):
        result=list(fallback)
        for name,meta in self.custom_sprite_meta.items():
            if not isinstance(meta,dict):continue
            cat=meta.get('category','other')
            if cat==category or (category=='nature' and cat in ('forest','field')) or (category=='buildings' and cat=='buildings'):
                result.append('user__'+name)
        return result or list(fallback)

"""+anchor,1)

# Keep imported custom sprites in project packages if a map uses them.
once("""            for u in d['units']:
                if u.get('image') and os.path.exists(u['image']):dest=td/'assets'/(u['id']+Path(u['image']).suffix.lower());shutil.copy2(u['image'],dest);u['image']=str(Path('assets')/dest.name)
            (td/'map.json').write_text""",
"""            for u in d['units']:
                if u.get('image') and os.path.exists(u['image']):dest=td/'assets'/(u['id']+Path(u['image']).suffix.lower());shutil.copy2(u['image'],dest);u['image']=str(Path('assets')/dest.name)
            for o in d.get('objects',[]):
                asset=o.get('asset','')
                if asset.startswith('user__'):
                    stem=asset[6:]
                    matches=[q for q in self.custom_sprite_dir.glob(stem+'.*') if q.is_file()]
                    if matches:
                        dest=td/'assets'/('sprite__'+matches[0].name)
                        shutil.copy2(matches[0],dest)
            (td/'map.json').write_text""", "package custom sprites")
once("""                d=json.loads((td/'map.json').read_text(encoding='utf-8'));base=td
""",
"""                d=json.loads((td/'map.json').read_text(encoding='utf-8'));base=td
                # Import sprites embedded in the project into this user's persistent library.
                for file in (td/'assets').glob('sprite__*'):
                    original=file.name[len('sprite__'):]
                    stem=Path(original).stem
                    target=self.custom_sprite_dir/original
                    if not target.exists():shutil.copy2(file,target)
                    self.custom_sprite_meta.setdefault(stem,{'category':'other','source_name':original})
                self.save_sprite_meta()
""", "restore packaged custom sprites")

# Use user sprite variants in the existing nature generator without changing roads or rivers.
once("if kind=='forest':o={'id':self.oid(),'kind':'asset','asset':r.choice(['bush_01','bush_02','bush_03'])",
     "if kind=='forest':o={'id':self.oid(),'kind':'asset','asset':r.choice(self.asset_choices('forest',['bush_01','bush_02','bush_03']))",
     "forest random variants")
once("elif kind=='field':o={'id':self.oid(),'kind':'asset','asset':r.choice(['field_01','field_02','field_03'])",
     "elif kind=='field':o={'id':self.oid(),'kind':'asset','asset':r.choice(self.asset_choices('field',['field_01','field_02','field_03']))",
     "field random variants")
once("else:o={'id':self.oid(),'kind':'asset','asset':r.choice(['rock_01','rock_02','rock_03'])",
     "else:o={'id':self.oid(),'kind':'asset','asset':r.choice(self.asset_choices('nature',['rock_01','rock_02','rock_03']))",
     "nature random variants")

# Replace battle dialog with a one-action calculation and a dedicated persistent results window.
battle_pat=re.compile(r"(?ms)^    def battle\(self\):\n.*?(?=^if __name__==)")
bm=battle_pat.search(s)
if not bm:raise RuntimeError("Could not locate battle()")
battle_method="""    # MB_FEATURES_5_9_6: casualties, equipment wear, morale and training resolve in one action.
    def battle(self):
        if len(self.units)<2:
            messagebox.showinfo('Бой','Добавьте минимум два подразделения.',parent=self.root);return
        w=tk.Toplevel(self.root);w.title('Расчёт сражения');w.geometry('500x330')
        names=[f\"{u['id']} — {u['name']}\" for u in self.units]
        a=tk.StringVar();b=tk.StringVar()
        ttk.Label(w,text='Атакующий').pack(pady=(15,3))
        ttk.Combobox(w,textvariable=a,values=names,state='readonly').pack(fill='x',padx=20)
        ttk.Label(w,text='Защитник').pack(pady=(10,3))
        ttk.Combobox(w,textvariable=b,values=names,state='readonly').pack(fill='x',padx=20)
        ttk.Label(w,text='За один расчёт определяются потери, состояние снаряжения, мораль и опыт.').pack(padx=16,pady=10)
        def idx(values,value):
            try:return values.index(value)
            except ValueError:return 0
        def fight():
            A=next((u for u in self.units if f\"{u['id']} — {u['name']}\"==a.get()),None)
            B=next((u for u in self.units if f\"{u['id']} — {u['name']}\"==b.get()),None)
            if not A or not B or A is B:return
            if A['side']==B['side']:
                messagebox.showwarning('Бой','Стороны должны различаться.',parent=w);return
            self.snapshot()
            train=[.62,.78,1.0,1.22,1.43,1.68]
            morale=[.30,.62,.82,1.0,1.16,1.34,1.52]
            armor=[.86,.94,1.0,1.10,1.18,1.28,1.38]
            weapon=[1.0,1.06,1.13,1.08,1.05,1.14,1.16]
            type_bonus={'Пехота':1.0,'Стрелки':1.04,'Конница':1.13,'Осадные':1.08,'Магия':1.18,'Особое':1.12}
            def strength(u,attacking):
                ti=idx(TRAINING,u.get('training','Регулярные'))
                mi=idx(MORALE,u.get('morale','Высокая мораль'))
                ai=idx(ARMOR,u.get('armor','Кольчуга'))
                wi=idx(WEAPONS,u.get('weapon','Древковое оружие'))
                condition=max(.45,min(1.15,float(u.get('equipment_condition',100))/100))
                readiness=max(.4,min(1.1,float(u.get('readiness',100))/100))
                typef=type_bonus.get(u.get('type','Пехота'),1.0)
                return max(1,int(u.get('men',0)))*train[ti]*morale[mi]*armor[ai]*weapon[wi]*condition*readiness*typef*(1.04 if attacking else 1.0)
            sa=strength(A,True)*random.uniform(.88,1.12)
            sb=strength(B,False)*random.uniform(.88,1.12)
            ratio=sa/max(1,sb)
            if ratio>=1.0:winner,loser=A,B
            else:winner,loser=B,A
            # Losses are deliberately consequential, but a stronger force can still pay dearly.
            win_ratio=max(.55,min(1.8,max(sa,sb)/max(1,min(sa,sb))))
            loser_rate=max(.16,min(.48,.31 + .12*(win_ratio-1) + random.uniform(-.045,.045)))
            winner_rate=max(.035,min(.22,.075 + .055/(win_ratio) + random.uniform(-.025,.025)))
            casualties={}
            for u,rate in ((loser,loser_rate),(winner,winner_rate)):
                before=max(0,int(u.get('men',0)))
                loss=min(before,round(before*rate))
                u['men']=max(0,before-loss)
                casualties[u['id']]=(before,loss,u['men'])
            # Equipment damage represents lost, broken or abandoned arms and armor.
            loser_gear=min(65,max(12,round(loser_rate*100*1.35+random.uniform(0,8))))
            winner_gear=min(30,max(3,round(winner_rate*100*1.15+random.uniform(0,5))))
            gear={}
            for u,damage in ((loser,loser_gear),(winner,winner_gear)):
                before=float(u.get('equipment_condition',100))
                u['equipment_condition']=max(0,round(before-damage))
                gear[u['id']]=(before,damage,u['equipment_condition'])
            # Morale uses existing named levels; heavy losses can break a unit.
            def change_morale(u,delta):
                old=idx(MORALE,u.get('morale','Высокая мораль'))
                loss=casualties[u['id']][1]/max(1,casualties[u['id']][0])
                shift=delta
                if loss>.30:shift-=1
                elif loss<.08 and delta>0:shift+=1
                new=max(0,min(len(MORALE)-1,old+shift))
                u['morale']=MORALE[new]
                return MORALE[old],MORALE[new]
            morale_changes={loser['id']:change_morale(loser,-2),winner['id']:change_morale(winner,1)}
            # Training grows only through battle experience and remains bounded at 100%.
            training_changes={}
            for u in (A,B):
                old=idx(TRAINING,u.get('training','Регулярные'))
                before=float(u.get('combat_experience',0))
                gain=round(random.uniform(1.0,3.0)+(0.8 if u is winner else 0),1)
                u['combat_experience']=min(100.0,before+gain)
                training_changes[u['id']]=(before,gain,u['combat_experience'])
                if u['combat_experience']>=90 and old<len(TRAINING)-1:u['training']=TRAINING[min(len(TRAINING)-1,old+1)]
            result={
                'time':__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'attacker':A['name'],'defender':B['name'],'winner':winner['name'],'loser':loser['name'],
                'units':{u['id']:{'name':u['name'],'side':u['side'],'men':casualties[u['id']][0],
                    'casualties':casualties[u['id']][1],'remaining':casualties[u['id']][2],
                    'gear_damage':gear[u['id']][1],'gear_remaining':gear[u['id']][2],
                    'morale_from':morale_changes[u['id']][0],'morale_to':morale_changes[u['id']][1],
                    'experience_gain':training_changes[u['id']][1],'experience':training_changes[u['id']][2]} for u in (A,B)}
            }
            self.battle_history.append(result)
            self.render();self.refresh()
            w.destroy()
            self.show_battle_results()
        ttk.Button(w,text='⚔ Провести бой',command=fight).pack(pady=14)

    def show_battle_results(self):
        win=tk.Toplevel(self.root);win.title('Журнал итогов сражений');win.geometry('820x480')
        cols=('time','unit','result','men','gear','morale','xp')
        tree=ttk.Treeview(win,columns=cols,show='headings')
        labels={'time':'Время','unit':'Подразделение','result':'Итог','men':'Люди: потери / осталось','gear':'Снаряжение','morale':'Мораль','xp':'Опыт боя'}
        widths={'time':135,'unit':175,'result':90,'men':125,'gear':100,'morale':110,'xp':90}
        for col in cols:tree.heading(col,text=labels[col]);tree.column(col,width=widths[col],anchor='w')
        y=ttk.Scrollbar(win,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=y.set)
        tree.pack(side='left',fill='both',expand=True);y.pack(side='right',fill='y')
        for result in reversed(self.battle_history):
            for unit in result['units'].values():
                tree.insert('','end',values=(result['time'],unit['name'],
                    'Победа' if unit['name']==result['winner'] else 'Поражение',
                    f\"−{unit['casualties']} / {unit['remaining']}\",
                    f\"−{unit['gear_damage']}% → {unit['gear_remaining']}%\",
                    f\"{unit['morale_from']} → {unit['morale_to']}\",
                    f\"+{unit['experience_gain']} ({unit['experience']:.1f})\"))
        bottom=ttk.Frame(win);bottom.pack(side='bottom',fill='x')
        ttk.Button(bottom,text='Закрыть',command=win.destroy).pack(side='right',padx=8,pady=6)
"""
s = s[:bm.start()] + battle_method + s[bm.end():]

# Add equipment condition to unit property panel; defaults preserve old saves.
once("""        if u['type']=='Осадные':self.combo('Орудие',SIEGE,u.get('siege','Баллиста'),lambda v:self.val(u,'siege',v))
""",
"""        if u['type']=='Осадные':self.combo('Орудие',SIEGE,u.get('siege','Баллиста'),lambda v:self.val(u,'siege',v))
        self.field('Снаряжение %',u.get('equipment_condition',100),lambda v:self.num(u,'equipment_condition',v))
""", "equipment condition property")

# The map border is intentionally not changed here. Roads and rivers are intentionally untouched.
p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("5.9.6 sprite library, compact tabs, and battle results patch applied; syntax check passed")
