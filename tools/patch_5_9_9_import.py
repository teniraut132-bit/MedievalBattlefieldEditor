from pathlib import Path
import re

p=Path("editor/Medieval_Battlefield_Editor_v4.py")
s=p.read_text(encoding="utf-8")
MARK="# MB_IMPORT_FIX_5_9_9"
if MARK in s:
    print("5.9.9 sprite import fix already applied")
    raise SystemExit(0)

# The previous library patch used re.sub() at runtime but only imported re in
# the build script. That makes PNG import fail with NameError: re is not defined.
# Add the runtime import to the generated editor itself.
head="import json, random, math, os, copy, zipfile, tempfile, shutil, sys, io"
if head not in s:
    raise RuntimeError("Expected base import line not found")
s=s.replace(head,head+", re",1)

# Make the importer validate actual pixels and normalize copies to a portable RGBA PNG.
start=s.index("    def import_sprites(self):")
end=s.index("    def export_sprite_pack(self):",start)
method='''    def import_sprites(self):
        files=filedialog.askopenfilenames(
            title='Добавить пользовательские спрайты',
            filetypes=[('PNG / WebP / JPG / BMP / GIF','*.png *.webp *.jpg *.jpeg *.bmp *.gif'),
                       ('PNG','*.png'),
                       ('Все файлы','*.*')])
        if not files:return
        category=simpledialog.askstring(
            'Категория спрайтов',
            'Категория: buildings (здания), nature (природа), decor (декор), forest (лес), field (поля), other (прочее).',
            initialvalue='other',parent=self.root)
        if category is None:return
        category=category.strip().lower()
        if category not in ('buildings','nature','decor','forest','field','other'):category='other'
        added=0;errors=[]
        for raw_path in files:
            src=Path(raw_path)
            try:
                with Image.open(src) as source:
                    source.load()
                    # Preserve alpha/transparency where present and normalize
                    # unusual PNG modes (P, LA, RGB, CMYK, etc.) to RGBA.
                    im=source.convert('RGBA')
                    if im.width<2 or im.height<2:
                        raise ValueError(f'слишком маленькое изображение {im.size}')
                    stem=re.sub(r'[^A-Za-z0-9_-]+','_',src.stem).strip('_')[:48] or 'sprite'
                    dest_stem=stem;idx=2
                    while any(q.stem.lower()==dest_stem.lower() for q in self.custom_sprite_dir.iterdir() if q.is_file()):
                        dest_stem=f'{stem}_{idx}';idx+=1
                    # Store a stable PNG copy. This avoids depending on codec support
                    # after an application update and makes sharing deterministic.
                    dest=self.custom_sprite_dir/(dest_stem+'.png')
                    im.save(dest,'PNG',optimize=True)
                self.custom_sprite_meta[dest_stem]={'category':category,'source_name':src.name}
                added+=1
            except Exception as exc:
                errors.append(f'{src.name}: {type(exc).__name__}: {exc}')
        self.save_sprite_meta()
        self.asset_pil_cache.clear();self.sprite_cache.clear()
        self.build_palette()
        self.status.set(f'В библиотеку добавлено спрайтов: {added}.')
        if errors:
            messagebox.showwarning(
                'Некоторые спрайты пропущены',
                'Импортировано: '+str(added)+'\\n\\n'+'\\n'.join(errors[:8]),
                parent=self.root)
'''
s=s[:start]+method+s[end:]

# Palette refresh is already performed by build_palette(); no extra source rewrite here.

s=MARK+"\n"+s
p.write_text(s,encoding="utf-8")
compile(s,str(p),"exec")
print("PASS: 5.9.9 sprite importer fix compiles")
