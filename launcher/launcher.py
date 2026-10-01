import json, shutil, subprocess, tempfile, threading, urllib.request, zipfile, hashlib
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

ROOT=Path(__file__).resolve().parent
INSTALL=ROOT/'editor'; BACKUPS=ROOT/'backups'; CFG=ROOT/'launcher_config.json'; STATE=ROOT/'state.json'
DEFAULT={'github_owner':'teniraut132-bit','github_repo':'MedievalBattlefieldEditor','asset_name':'MedievalBattlefieldEditor-Windows-x64.zip','auto_check':True,'news_file':'news.json','news_branch':'main'}

def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d.copy()

def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

cfg=load(CFG,DEFAULT)
for k,v in DEFAULT.items():cfg.setdefault(k,v)
state=load(STATE,{'installed_version':'0.0.0'})

def vt(v):
    try:
        p=[int(x) for x in str(v).lstrip('vV').split('.')]
        return tuple((p+[0,0,0])[:3])
    except:return (0,0,0)

def ver():return load(INSTALL/'version.json',{}).get('version',state['installed_version'])

def get_json(url):
    r=urllib.request.Request(url,headers={
        'User-Agent':'MedievalBattlefieldLauncher/5.2.2',
        'Accept':'application/vnd.github+json'
    })
    with urllib.request.urlopen(r,timeout=30) as x:
        return json.loads(x.read().decode('utf-8-sig'))

def get_text(url):
    r=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher/5.2.2'})
    with urllib.request.urlopen(r,timeout=20) as x:return x.read().decode('utf-8-sig')

def latest():
    # Prefer the API, but GitHub limits unauthenticated requests. If the API
    # returns HTTP 403/429, fall back to the release's direct latest.json asset.
    api=f"https://api.github.com/repos/{cfg['github_owner']}/{cfg['github_repo']}/releases/latest"
    try:
        return get_json(api)
    except Exception as api_error:
        direct=f"https://github.com/{cfg['github_owner']}/{cfg['github_repo']}/releases/latest/download/latest.json"
        try:
            meta=get_json(direct)
            version=str(meta.get('version','')).lstrip('vV')
            asset_url=meta.get('asset_url') or f"https://github.com/{cfg['github_owner']}/{cfg['github_repo']}/releases/latest/download/{cfg['asset_name']}"
            if not version or not asset_url: raise RuntimeError('latest.json does not contain version/asset_url')
            return {
                'tag_name':'v'+version,
                'name':meta.get('name','Medieval Battlefield Editor'),
                'body':meta.get('notes',''),
                'html_url':f"https://github.com/{cfg['github_owner']}/{cfg['github_repo']}/releases/latest",
                'assets':[{'name':cfg['asset_name'],'browser_download_url':asset_url,'digest':'sha256:'+str(meta.get('sha256','')) if meta.get('sha256') else None}]
            }
        except Exception as fallback_error:
            raise RuntimeError(f'Не удалось проверить обновления через GitHub API и резервный канал. API: {api_error}; резервный канал: {fallback_error}') from fallback_error

def load_news():
    try:
        d=get_json(f"https://api.github.com/repos/{cfg['github_owner']}/{cfg['github_repo']}/contents/{cfg.get('news_file','news.json')}?ref={cfg.get('news_branch','main')}")
        import base64
        return json.loads(base64.b64decode(d['content']).decode('utf-8-sig')).get('news',[])
    except:return []

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def findfile(root,name):
    direct=root/name
    if direct.exists():return direct
    hits=list(root.rglob(name))
    return hits[0] if hits else None

def findexe(p):
    # Prefer the executable at the install root. Recursive search can
    # otherwise select an old copy from a nested folder/backup.
    for n in ['MedievalBattlefieldEditor.exe','Medieval_Battlefield_Editor_v4.exe']:
        e=p/n
        if e.is_file():return e
    for n in ['MedievalBattlefieldEditor.exe','Medieval_Battlefield_Editor_v4.exe']:
        hits=[x for x in p.rglob(n) if x.is_file() and 'backups' not in [part.lower() for part in x.parts] and 'editor_old' not in [part.lower() for part in x.parts]]
        if hits:
            hits.sort(key=lambda x:(len(x.relative_to(p).parts),str(x).lower()))
            return hits[0]

def find_manifest(p):
    return findfile(p,'version.json')

def set_text(w,s):
    w.configure(state='normal');w.delete('1.0','end');w.insert('1.0',s);w.configure(state='disabled')

def refresh_info(rel=None):
    if rel is None:
        try:rel=latest()
        except Exception:rel=None
    lines=[]
    if rel:
        lines.append(f"Версия {str(rel.get('tag_name','')).lstrip('vV')} — {rel.get('name','')}")
        for line in (rel.get('body') or '').splitlines():
            line=line.strip().lstrip('-*').strip()
            if line and 'Full Changelog' not in line:lines.append(line)
    set_text(updates_box,'\n'.join('• '+x for x in lines) if lines else 'Пока нет опубликованных обновлений.')
    news=load_news();nl=[]
    for n in news[:12]:
        nl.append(f"• {n.get('date','')}  {n.get('title','')}" if isinstance(n,dict) else '• '+str(n))
    set_text(news_box,'\n'.join(nl) if nl else 'Пока нет новостей проекта.')

def update():
    tmp=None
    try:
        status.set('Проверка обновлений…')
        rel=latest()
        tag=str(rel.get('tag_name','')).lstrip('vV')
        if not tag:raise RuntimeError('GitHub не вернул номер версии релиза')
        if vt(tag)<=vt(ver()):
            status.set(f'Версия {ver()} уже актуальна.');refresh_info(rel);return True

        assets=rel.get('assets') or []
        asset=next((a for a in assets if a.get('name')==cfg['asset_name']),None)
        if not asset:
            names=', '.join(a.get('name','?') for a in assets)
            raise RuntimeError(f'В релизе {tag} нет файла {cfg["asset_name"]}. Найдены: {names or "нет файлов"}')
        url=asset.get('browser_download_url')
        if not url:raise RuntimeError('У ZIP-релиза отсутствует ссылка на скачивание')

        tmp=Path(tempfile.mkdtemp(prefix='MBE_update_'));z=tmp/'release.zip'
        status.set(f'Скачивание {tag}…')
        req=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher/5.2.2','Accept':'application/octet-stream'})
        with urllib.request.urlopen(req,timeout=300) as r,open(z,'wb') as f:shutil.copyfileobj(r,f)

        expected=asset.get('digest')
        if expected and expected.startswith('sha256:'):expected=expected.split(':',1)[1]
        if expected and sha(z).lower()!=expected.lower():raise RuntimeError('SHA-256 проверка GitHub не пройдена')

        st=tmp/'staging';st.mkdir()
        with zipfile.ZipFile(z) as zf:
            bad=zf.testzip()
            if bad:raise RuntimeError(f'Повреждённый ZIP, файл: {bad}')
            zf.extractall(st)

        manifest=find_manifest(st)
        editor=findexe(st)
        if not manifest or not editor:
            entries=', '.join(p.name for p in st.iterdir())
            raise RuntimeError(f'Некорректный пакет редактора: не найден version.json или MedievalBattlefieldEditor.exe. Содержимое ZIP: {entries or "пусто"}')
        downloaded_version=load(manifest,{}).get('version')
        if downloaded_version!=tag:
            raise RuntimeError(f'Версия пакета ({downloaded_version}) не совпадает с релизом ({tag})')

        # Normalize a possible single top-level directory so installed editor
        # remains a clean folder.
        package_root=manifest.parent
        BACKUPS.mkdir(exist_ok=True);old=ver()
        if INSTALL.exists():shutil.copytree(INSTALL,BACKUPS/old,dirs_exist_ok=True)

        new=ROOT/'editor_new';olddir=ROOT/'editor_old'
        if new.exists():shutil.rmtree(new)
        if olddir.exists():shutil.rmtree(olddir)
        shutil.copytree(package_root,new)
        if INSTALL.exists():INSTALL.rename(olddir)
        new.rename(INSTALL);shutil.rmtree(olddir,ignore_errors=True)

        state['installed_version']=tag;save(STATE,state);vervar.set('Версия: '+ver())
        status.set(f'Установлена версия {tag}.')
        shutil.rmtree(tmp,ignore_errors=True);refresh_info(rel);return True
    except Exception as e:
        if tmp:shutil.rmtree(tmp,ignore_errors=True)
        status.set('Ошибка обновления')
        messagebox.showerror('Обновление',str(e))
        return False

def threaded():threading.Thread(target=update,daemon=True).start()

def launch():
    def worker():
        ok=True
        try:
            rel=latest()
            if vt(rel.get('tag_name','0'))>vt(ver()) or not findexe(INSTALL):
                ok=update()
        except Exception:
            ok=False
        e=findexe(INSTALL)
        if ok and e:
            # Run from the actual executable directory; PyInstaller onedir
            # apps may rely on adjacent _internal/data files.
            root.after(0,lambda:(subprocess.Popen([str(e)],cwd=str(e.parent)),root.destroy()))
        elif ok:
            root.after(0,lambda:messagebox.showerror('Редактор','Редактор не установлен. Нажмите «Проверить обновления».'))
    threading.Thread(target=worker,daemon=True).start()

def settings():
    w=tk.Toplevel(root);w.title('Настройки GitHub');w.geometry('520x330');vals={}
    for k,label in [('github_owner','GitHub owner'),('github_repo','Repository'),('asset_name','ZIP asset'),('news_file','Файл новостей'),('news_branch','Ветка новостей')]:
        tk.Label(w,text=label).pack(anchor='w',padx=18,pady=(10,0))
        v=tk.StringVar(value=cfg[k]);vals[k]=v;tk.Entry(w,textvariable=v).pack(fill='x',padx=18)
    def s():cfg.update({k:v.get().strip() for k,v in vals.items()});save(CFG,cfg);w.destroy();refresh_info();status.set('Настройки сохранены')
    tk.Button(w,text='Сохранить',command=s).pack(pady=18)

root=tk.Tk();root.title('Medieval Battlefield Editor — Launcher');root.geometry('980x650');root.minsize(820,560);root.configure(bg='#0e0d0b')
header=tk.Frame(root,bg='#17130e');header.pack(fill='x')
tk.Label(header,text='MEDIEVAL BATTLEFIELD EDITOR',bg='#17130e',fg='#d6b45e',font=('Georgia',25,'bold')).pack(pady=(24,4))
vervar=tk.StringVar(value='Версия: '+ver());tk.Label(header,textvariable=vervar,bg='#17130e',fg='#dfcea0',font=('Georgia',11)).pack(pady=(0,18))
body=tk.Frame(root,bg='#0e0d0b');body.pack(fill='both',expand=True,padx=24,pady=20)
left=tk.Frame(body,bg='#1a1712',highlightbackground='#66502b',highlightthickness=2);left.pack(side='left',fill='both',expand=True,padx=(0,10))
right=tk.Frame(body,bg='#1a1712',highlightbackground='#66502b',highlightthickness=2,width=340);right.pack(side='right',fill='y');right.pack_propagate(False)
tk.Label(left,text='ОБНОВЛЕНИЯ',bg='#1a1712',fg='#d6b45e',font=('Georgia',14,'bold')).pack(anchor='w',padx=18,pady=(18,8))
updates_box=tk.Text(left,bg='#12100d',fg='#e2d5b7',relief='flat',wrap='word');updates_box.pack(fill='both',expand=True,padx=18,pady=(0,18));updates_box.configure(state='disabled')
tk.Label(right,text='НОВОСТИ ПРОЕКТА',bg='#1a1712',fg='#d6b45e',font=('Georgia',14,'bold')).pack(anchor='w',padx=18,pady=(18,8))
news_box=tk.Text(right,bg='#12100d',fg='#e2d5b7',relief='flat',wrap='word');news_box.pack(fill='both',expand=True,padx=18,pady=(0,18));news_box.configure(state='disabled')
status=tk.StringVar(value='Готово.');tk.Label(root,textvariable=status,bg='#0e0d0b',fg='#cbbd9a').pack(pady=(0,8))
buttons=tk.Frame(root,bg='#0e0d0b');buttons.pack(fill='x',padx=24,pady=(0,22))
tk.Button(buttons,text='ЗАПУСТИТЬ РЕДАКТОР',command=launch,bg='#66251d',fg='#f2d8a2',font=('Georgia',13,'bold'),relief='flat',padx=28,pady=11).pack(side='left')
tk.Button(buttons,text='ПРОВЕРИТЬ ОБНОВЛЕНИЯ',command=threaded,bg='#30271c',fg='#e2cd96',font=('Georgia',10,'bold'),relief='flat',padx=18,pady=9).pack(side='left',padx=10)
tk.Button(buttons,text='Настройки',command=settings,bg='#30271c',fg='#e2cd96',relief='flat',padx=15,pady=8).pack(side='right')
refresh_info()
if cfg.get('auto_check',True):root.after(800,threaded)
root.mainloop()
