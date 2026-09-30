from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# Road patches can accidentally corrupt indentation around draw_obj().
# Rebuild that small function from a known-valid definition instead of
# trying to repair indentation line by line.
start = s.find("    def draw_obj(self,o):")
end = s.find("    def draw_asset(self,o):", start)
if start < 0 or end < 0:
    raise RuntimeError("Could not locate draw_obj()/draw_asset()")

new_func = """    def draw_obj(self,o):
        if o['kind']=='bridge':
            x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale
            self.canvas.create_rectangle(x-L/2,y-12*self.scale,x+L/2,y+12*self.scale,fill='#68462e',outline='#302117',width=3)
            for xx in range(int(x-L/2+8),int(x+L/2),max(8,int(18*self.scale))):
                self.canvas.create_line(xx,y-11*self.scale,xx,y+11*self.scale,fill='#b17c47',width=2)
        elif o['kind']=='settlement':
            x,y=self.world_to_screen(o['x'],o['y'])
            self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,outline='#655039',dash=(8,5),width=2)
            self.canvas.create_text(x,y-420*self.scale,text=o.get('name','Поселение'),font=('Georgia',max(9,int(18*self.scale)),'bold'),fill='#38291e')
        elif o['kind']=='asset':
            self.draw_asset(o)
        elif o['kind']=='tree':
            self.draw_asset({'asset':o['asset'],'x':o['x'],'y':o['y'],'size':o.get('size',70)})

"""
s = s[:start] + new_func + s[end:]
p.write_text(s, encoding="utf-8")

compile(s, str(p), "exec")
print("Python syntax check passed")
