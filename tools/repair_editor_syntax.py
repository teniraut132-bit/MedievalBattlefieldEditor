from pathlib import Path
import re

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# The road patches may leave draw_obj() with a malformed body.
# Replace the complete method using a line-anchored regex and derive the
# class indentation from the existing draw_asset() method.
pattern = re.compile(
    r"(?ms)^[ \t]*def draw_obj\(self,o\):\r?\n.*?(?=^[ \t]*def draw_asset\(self,o\):)"
)
m = pattern.search(s)
if not m:
    raise RuntimeError("Could not locate draw_obj() before draw_asset()")

asset_match = re.search(r"(?m)^([ \t]*)def draw_asset\(self,o\):", s[m.start():])
if not asset_match:
    raise RuntimeError("Could not determine class indentation")
base = asset_match.group(1)

body = [
    "def draw_obj(self,o):",
    "    if o['kind']=='bridge':",
    "        x,y=self.world_to_screen(o['x'],o['y']);L=o.get('length',160)*self.scale",
    "        self.canvas.create_rectangle(x-L/2,y-12*self.scale,x+L/2,y+12*self.scale,fill='#68462e',outline='#302117',width=3)",
    "        for xx in range(int(x-L/2+8),int(x+L/2),max(8,int(18*self.scale))):",
    "            self.canvas.create_line(xx,y-11*self.scale,xx,y+11*self.scale,fill='#b17c47',width=2)",
    "    elif o['kind']=='settlement':",
    "        x,y=self.world_to_screen(o['x'],o['y'])",
    "        self.canvas.create_oval(x-520*self.scale,y-400*self.scale,x+520*self.scale,y+400*self.scale,outline='#655039',dash=(8,5),width=2)",
    "        self.canvas.create_text(x,y-420*self.scale,text=o.get('name','Поселение'),font=('Georgia',max(9,int(18*self.scale)),'bold'),fill='#38291e')",
    "    elif o['kind']=='asset':",
    "        self.draw_asset(o)",
    "    elif o['kind']=='tree':",
    "        self.draw_asset({'asset':o['asset'],'x':o['x'],'y':o['y'],'size':o.get('size',70)})",
]
new_func = "\n".join(base + line for line in body) + "\n"
s = s[:m.start()] + new_func + s[m.end():]

# Verify the exact lines before compiling so the CI log shows what was fixed.
lines = s.splitlines()
draw_idx = next(i for i, line in enumerate(lines) if line.strip() == "def draw_obj(self,o):")
if draw_idx + 1 >= len(lines) or len(lines[draw_idx + 1]) - len(lines[draw_idx + 1].lstrip()) <= len(base):
    raise RuntimeError(
        "draw_obj() body is not indented deeper than the method definition: "
        + repr(lines[draw_idx:draw_idx+3])
    )

p.write_text(s, encoding="utf-8")
compile(s, str(p), "exec")
print("Python syntax check passed")
