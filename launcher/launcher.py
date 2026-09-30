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
        p=[int(x) for x in str(v).lstrip('vV').split('.')];return tuple((p+[0,0,0])[:3])
    except:return (0,0,0)
def ver():return load(INSTALL/'version.json',{}).get('version',state['installed_version'])
def api():return f"https://api.github.com/repos/{cfg['github_owner']}/{cfg['github_repo']}/releases"
def get(url):
    r=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(r,timeout=20) as x:return json.loads(x.read().decode())
def get_text(url):
    r=urllib.request.Request(url,headers={'User-Agent':'MedievalBattlefieldLauncher'})
    with urllib.request.urlopen(r,timeout=15) as x:return x.read().decode('utf-8')
def load_news():
    try:
        d=json.loads(get_text(f"https://raw.githubusercontent.com/{cfg['github_owner']}/{cfg['github_repo']}/{cfg.get('news_branch','main')}/{cfg.get('news_file','news.json')}"))
        return d.get('news',[]) if isinstance(d,dict) else []
    except:return []
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def findexe(p):
    for n in ['MedievalBattlefieldEditor.exe','Medieval_Battlefield_Editor_v4.exe']:
        if (p/n).exists():return p/n
def set_text(w,s):
    w.configure(state='normal');w.delete('1.0','end');w.insert('1.0',s);w.configure(state='disabled')
def refresh_info(rel=None):
    if rel is None:
        try:rel=next((r for r in get(api()) if not r.get('draft') and not r.get('prerelease')),None)
        except Exception:rel=None
    lines=[]
    if rel:
        lines.append(f"Версия {rel['tag_name'].lstrip('vV')} — {rel.get('name','')}")
        for line in (rel.get('body') or '').splitlines():
            line=line.strip().lstrip('-*').strip()
            if line and 'Full Changelog' not in line:lines.append(line)
    set_text(updates_box,'\n'.join('• '+x for x in lines) if lines else 'Пока нет опубликованных обновлений.')
    news=load_news();nl=[]
    for n in news[:12]:
        nl.append(f"• {n.get('date','')}  {n.get('title','')}" if isinstance(n,dict) else '• '+str(n))
    set_text(news_box,'\n'.join(nl) if nl else 'Пока нет новостей проекта.')
def update():
    try:
        status.set('Проверка GitHub…')
        rel=next((r for r in get(api()) if not r.get('draft') and not r.get('prerelease')),None)
        if not rel:status.set('Стабильных релизов нет.');return
        tag=rel['tag_name'].lstrip('vV')
        if vt(tag)<=vt(ver()):status.set(f'Версия {ver()} уже актуальна.');refresh_info(rel);return
        asset=next((a for a in rel['assets'] if a['name']==cfg['asset_name']),None)
        if not asset:raise RuntimeError('В Release отсутствует '+cfg['asset_name'])
        tmp=Path(tempfile.mkdtemp());z=tmp/'release.zip';status.set(f'Скачивание {tag}…')
        req=urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher'})
        with urllib.request.urlopen(req,timeout=120) as r,open(z,'wb') as f:f.write(r.read())
        chk=next((a for a in rel['assets'] if a['name']==cfg['asset_name']+'.sha256'),None)
        if chk:
            q=urllib.request.Request(chk['browser_download_url'],headers={'User-Agent':'MedievalBattlefieldLauncher'})
            if sha(z).lower()!=urllib.request.urlopen(q,timeout=20).read().decode().split()[0].lower():raise RuntimeError('SHA-256 проверка не пройдена')
        st=tmp/'staging';st.mkdir();zipfile.ZipFile(z).extractall(st)
        if not (st/'version.json').exists():
            ds=[d for d in st.iterdir() if d.is_dir()]
            if len(ds)==1:st=ds[0]
        if load(st/'version.json',{}).get('version')!=tag or not findexe(st):raise RuntimeError('Некорректный пакет редактора')
        BACKUPS.mkdir(exist_ok=True);old=ver()
        if INSTALL.exists():shutil.copytree(INSTALL,BACKUPS/old,dirs_exist_ok=True)
        new=ROOT/'editor_new';olddir=ROOT/'editor_old'
        if new.exists():shutil.rmtree(new)
        if olddir.exists():shutil.rmtree(olddir)
        shutil.copytree(st,new)
        if INSTALL.exists():INSTALL.rename(olddir)
        new.rename(INSTALL);shutil.rmtree(olddir,ignore_errors=True)
        state['installed_version']=tag;save(STATE,state);vervar.set('Версия: '+ver());status.set(f'Установлена версия {tag}.')
        shutil.rmtree(tmp,ignore_errors=True);refresh_info(rel)
    except Exception as e:
        status.set('Ошибка обновления');messagebox.showerror('Обновление',str(e))
def threaded():threading.Thread(target=update,daemon=True).start()
def launch():
    e=findexe(INSTALL)
    if not e:
        threaded(); root.after(700, launch); return
    try:
        rel=next((r for r in get(api()) if not r.get('draft') and not r.get('prerelease')),None)
        if rel and vt(rel['tag_name'].lstrip('vV'))>vt(ver()):
            status.set('Сначала устанавливаю последнее обновление…'); threaded(); root.after(1200, launch); return
    except Exception: pass
    e=findexe(INSTALL)
    if not e: messagebox.showerror('Редактор','Не удалось установить редактор.'); return
    subprocess.Popen([str(e)],cwd=str(INSTALL)); root.destroy()
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
