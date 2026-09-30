from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

# A previous road-rendering patch could leave the first statement of
# draw_obj() at column 0. Normalize that known malformed block.
needle = "    def draw_obj(self,o):\nif o['kind']=='bridge':"
fixed = "    def draw_obj(self,o):\n        if o['kind']=='bridge':"
if needle in s:
    s = s.replace(needle, fixed, 1)

p.write_text(s, encoding="utf-8")
print("Editor syntax repair applied")

# Fail here with a precise message if the generated source is still invalid.
compile(s, str(p), "exec")
print("Python syntax check passed")
