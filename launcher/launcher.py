import json, shutil, subprocess, sys, tempfile, threading, time, urllib.request, zipfile, hashlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT=Path(__file__).resolve().parent
INSTALL=ROOT/'editor'; BACKUPS=ROOT/'backups'; CFG=ROOT/'launcher_config.json'; STATE=ROOT/'state.json'
DEFAULT={'github_owner':'teniraut132-bit','github_repo':'MedievalBattlefieldEditor','asset_name':'MedievalBattlefieldEditor-Windows-x64.zip','auto_check':True}
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
def api():return f"https://api.github.com/repos/{cfg['github_owner']}/{cfg['github_repo']}/releases"
def get(url):
    r=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(r,timeout=20) as x:return json.loads(x.read().decode())
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def findexe(p):
    for n in ['MedievalBattlefieldEditor.exe','Medieval_Battlefield_Editor_v4.exe']:
        if (p/n).exists():return p/n
def update():
    try:
        status.set('Проверка GitHub…')
        rel=next((r for r in get(api()) if not r.get('draft') and not r.get('prerelease')),None)
        if not rel: status.set('Стабильных релизов нет.');return
        tag=rel['tag_name'].lstrip('vV')
        if vt(tag)<=vt(ver()): status.set(f'Версия {ver()} уже актуальна.');return
        asset=next((a for a in rel['assets'] if a['name']==cfg['asset_name']),None)
        if not asset: raise RuntimeError('В Release отсутствует '+cfg['asset_name'])
        tmp=Path(tempfile.mkdtemp()); z=tmp/'release.zip'; status.set(f'Скачивание {tag}…')
        req=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher'})
        with urllib.request.urlopen(req,timeout=120) as r,open(z,'wb') as f:f.write(r.read())
        chk=next((a for a in rel['assets'] if a['name']==cfg['asset_name']+'.sha256'),None)
        if chk:
            q=urllib.request.Request(chk['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher'})
            expected=urllib.request.urlopen(q,timeout=20).read().decode().split()[0]
            if sha(z).lower()!=expected.lower():raise RuntimeError('SHA-256 проверка не пройдена')
        st=tmp/'staging';st.mkdir();zipfile.ZipFile(z).extractall(st)
        if not (st/'version.json').exists():
            ds=[d for d in st.iterdir() if d.is_dir()]
            if len(ds)==1:st=ds[0]
        if load(st/'version.json',{}).get('version')!=tag or not findexe(st):raise RuntimeError('Некорректный пакет редактора')
        BACKUPS.mkdir(exist_ok=True); old=ver()
        if INSTALL.exists(): shutil.copytree(INSTALL,BACKUPS/old,dirs_exist_ok=True)
        new=ROOT/'editor_new'; olddir=ROOT/'editor_old'
        if new.exists():shutil.rmtree(new)
        if olddir.exists():shutil.rmtree(olddir)
        shutil.copytree(st,new)
        if INSTALL.exists():INSTALL.rename(olddir)
        new.rename(INSTALL);shutil.rmtree(olddir,ignore_errors=True)
        state['installed_version']=tag;save(STATE,state);status.set(f'Установлена версия {tag}.');vervar.set('Версия: '+ver())
        shutil.rmtree(tmp,ignore_errors=True)
    except Exception as e:
        status.set('Ошибка обновления');messagebox.showerror('Обновление',str(e))
def threaded():threading.Thread(target=update,daemon=True).start()
def launch():
    e=findexe(INSTALL)
    if not e:messagebox.showinfo('Редактор','Сначала опубликуйте первый GitHub Release и нажмите «Проверить обновления».');return
    subprocess.Popen([str(e)],cwd=str(INSTALL));root.destroy()
def settings():
    w=tk.Toplevel(root);w.title('GitHub');w.geometry('500x250');vals={}
    for k,label in [('github_owner','GitHub owner'),('github_repo','Repository'),('asset_name','ZIP asset')]:
        tk.Label(w,text=label).pack(anchor='w',padx=15,pady=(12,0));v=tk.StringVar(value=cfg[k]);vals[k]=v;tk.Entry(w,textvariable=v).pack(fill='x',padx=15)
    def s():cfg.update({k:v.get().strip() for k,v in vals.items()});save(CFG,cfg);w.destroy();status.set('Настройки сохранены')
    tk.Button(w,text='Сохранить',command=s).pack(pady=18)
root=tk.Tk();root.title('Medieval Battlefield Editor — Launcher');root.geometry('760x480');root.configure(bg='#11100d')
tk.Label(root,text='MEDIEVAL BATTLEFIELD EDITOR',bg='#11100d',fg='#d6b45e',font=('Georgia',24,'bold')).pack(pady=(30,5))
vervar=tk.StringVar(value='Версия: '+ver());tk.Label(root,textvariable=vervar,bg='#11100d',fg='#dfcea0',font=('Georgia',11)).pack()
frame=tk.Frame(root,bg='#1a1712',highlightbackground='#66502b',highlightthickness=2);frame.pack(fill='both',expand=True,padx=30,pady=25)
status=tk.StringVar(value='Готово.');tk.Label(frame,textvariable=status,bg='#1a1712',fg='#d8c89f',font=('Georgia',12)).pack(pady=30)
tk.Button(frame,text='ЗАПУСТИТЬ РЕДАКТОР',command=launch,bg='#66251d',fg='#f2d8a2',font=('Georgia',14,'bold'),relief='flat',padx=30,pady=12).pack(pady=10)
tk.Button(frame,text='ПРОВЕРИТЬ ОБНОВЛЕНИЯ',command=threaded,bg='#30271c',fg='#e2cd96',font=('Georgia',11,'bold'),relief='flat',padx=25,pady=9).pack(pady=8)
tk.Button(frame,text='Настройки GitHub',command=settings,bg='#30271c',fg='#e2cd96',relief='flat').pack(pady=8)
if cfg.get('auto_check',True):root.after(800,threaded)
root.mainloop()
