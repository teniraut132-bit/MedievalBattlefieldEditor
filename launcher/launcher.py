import json, shutil, subprocess, tempfile, threading, urllib.request, zipfile, hashlib, os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT=Path(__file__).resolve().parent
INSTALL=ROOT/'editor'; BACKUPS=ROOT/'backups'; CFG=ROOT/'launcher_config.json'; STATE=ROOT/'state.json'
DEFAULT={'github_owner':'teniraut132-bit','github_repo':'MedievalBattlefieldEditor','asset_name':'MedievalBattlefieldEditor-Windows-x64.zip','auto_check':True}
def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
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
def ver():return load(INSTALL/'version.json',{}).get('version',state.get('installed_version','0.0.0'))
def api():return f"https://api.github.com/repos/{cfg['github_owner']}/{cfg['github_repo']}/releases/latest"
def get(url,timeout=8):
    req=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher/6.1.3','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def findexe(p):
    for n in ('MedievalBattlefieldEditor.exe','Medieval_Battlefield_Editor_v4.exe'):
        found=next(p.rglob(n),None)
        if found and found.is_file():return found
    return None
def ui_status(msg):
    try:root.after(0,lambda: status.set(msg) if root.winfo_exists() else None)
    except (NameError,tk.TclError):pass
def ui_error(title,msg):
    try:root.after(0,lambda: messagebox.showerror(title,msg) if root.winfo_exists() else None)
    except (NameError,tk.TclError):pass
def update():
    tmp=None
    try:
        ui_status('Проверка обновлений…')
        rel=get(api())
        if rel.get('draft') or rel.get('prerelease'):raise RuntimeError('Последний релиз не является стабильным.')
        tag=rel['tag_name'].lstrip('vV')
        if vt(tag)<=vt(ver()):ui_status(f'Версия {ver()} уже актуальна.');return
        asset=next((a for a in rel.get('assets',[]) if a['name']==cfg['asset_name']),None)
        if not asset:raise RuntimeError('В релизе отсутствует '+cfg['asset_name'])
        tmp=Path(tempfile.mkdtemp(prefix='mb-update-'));z=tmp/'release.zip'
        ui_status(f'Скачивание версии {tag}…')
        req=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher/6.1.3'})
        with urllib.request.urlopen(req,timeout=120) as r,open(z,'wb') as f:shutil.copyfileobj(r,f,1024*1024)
        expected=asset.get('digest','')
        if expected.startswith('sha256:'):expected=expected.split(':',1)[1]
        else:
            chk=next((a for a in rel.get('assets',[]) if a['name']==cfg['asset_name']+'.sha256'),None)
            if chk:
                with urllib.request.urlopen(urllib.request.Request(chk['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher/6.1.3'}),timeout=15) as r:expected=r.read().decode().split()[0]
        if expected and sha(z).lower()!=expected.lower():raise RuntimeError('Проверка SHA-256 не пройдена.')
        ui_status('Проверка и распаковка…')
        with zipfile.ZipFile(z) as archive:
            bad=archive.testzip()
            if bad:raise RuntimeError('Повреждён файл в архиве: '+bad)
            st=tmp/'staging';st.mkdir();archive.extractall(st)
        manifest=next(st.rglob('version.json'),None)
        if not manifest:raise RuntimeError('В архиве не найден version.json.')
        package=manifest.parent
        if load(manifest,{}).get('version')!=tag or not findexe(package):
            raise RuntimeError('Версия пакета не совпадает с релизом или EXE отсутствует.')
        BACKUPS.mkdir(exist_ok=True);old=ver()
        if INSTALL.exists():shutil.copytree(INSTALL,BACKUPS/old,dirs_exist_ok=True)
        new=ROOT/'editor_new';old_dir=ROOT/'editor_old'
        if new.exists():shutil.rmtree(new)
        if old_dir.exists():shutil.rmtree(old_dir)
        shutil.copytree(package,new)
        # Keep user content and settings outside the app payload across upgrades.
        for name in ('user_assets','maps','projects','sprites','models'):
            src=INSTALL/name;dst=new/name
            if src.exists() and not dst.exists():
                if src.is_dir():shutil.copytree(src,dst)
                else:shutil.copy2(src,dst)
        if INSTALL.exists():INSTALL.rename(old_dir)
        try:new.rename(INSTALL)
        except Exception:
            if old_dir.exists() and not INSTALL.exists():old_dir.rename(INSTALL)
            raise
        shutil.rmtree(old_dir,ignore_errors=True)
        state['installed_version']=tag;save(STATE,state)
        ui_status(f'Установлена версия {tag}.')
        try:root.after(0,lambda:vervar.set('Версия: '+ver()) if root.winfo_exists() else None)
        except tk.TclError:pass
    except Exception as e:
        ui_status('Ошибка обновления');ui_error('Обновление',str(e))
    finally:
        if tmp:shutil.rmtree(tmp,ignore_errors=True)
def threaded():
    if getattr(threaded,'busy',False):return
    threaded.busy=True
    def worker():
        try:update()
        finally:threaded.busy=False
    threading.Thread(target=worker,daemon=True,name='UpdateCheck').start()
def launch():
    e=findexe(INSTALL)
    if not e:messagebox.showinfo('Редактор','Редактор ещё не установлен. Нажмите «Проверить обновления».');return
    try:subprocess.Popen([str(e)],cwd=str(e.parent))
    except Exception as exc:messagebox.showerror('Запуск редактора',str(exc))
    else:root.destroy()
def settings():
    w=tk.Toplevel(root);w.title('GitHub');w.geometry('500x250');vals={}
    for k,label in [('github_owner','GitHub owner'),('github_repo','Repository'),('asset_name','ZIP asset')]:
        tk.Label(w,text=label).pack(anchor='w',padx=15,pady=(12,0));v=tk.StringVar(value=cfg[k]);vals[k]=v;tk.Entry(w,textvariable=v).pack(fill='x',padx=15)
    def s():cfg.update({k:v.get().strip() for k,v in vals.items()});save(CFG,cfg);w.destroy();ui_status('Настройки сохранены')
    tk.Button(w,text='Сохранить',command=s).pack(pady=18)
root=tk.Tk();root.title('Medieval Battlefield Editor — Launcher');root.geometry('760x480');root.configure(bg='#11100d')
tk.Label(root,text='MEDIEVAL BATTLEFIELD EDITOR',bg='#11100d',fg='#d6b45e',font=('Georgia',24,'bold')).pack(pady=(30,5))
vervar=tk.StringVar(value='Версия: '+ver());tk.Label(root,textvariable=vervar,bg='#11100d',fg='#dfcea0',font=('Georgia',11)).pack()
frame=tk.Frame(root,bg='#1a1712',highlightbackground='#66502b',highlightthickness=2);frame.pack(fill='both',expand=True,padx=30,pady=25)
status=tk.StringVar(value='Готово.');tk.Label(frame,textvariable=status,bg='#1a1712',fg='#d8c89f',font=('Georgia',12)).pack(pady=30)
tk.Button(frame,text='ЗАПУСТИТЬ РЕДАКТОР',command=launch,bg='#66251d',fg='#f2d8a2',font=('Georgia',14,'bold'),relief='flat',padx=30,pady=12).pack(pady=10)
tk.Button(frame,text='ПРОВЕРИТЬ ОБНОВЛЕНИЯ',command=threaded,bg='#30271c',fg='#e2cd96',font=('Georgia',11,'bold'),relief='flat',padx=25,pady=9).pack(pady=8)
tk.Button(frame,text='Настройки GitHub',command=settings,bg='#30271c',fg='#e2cd96',relief='flat').pack(pady=8)
if cfg.get('auto_check',True):root.after(250,threaded)
root.mainloop()
