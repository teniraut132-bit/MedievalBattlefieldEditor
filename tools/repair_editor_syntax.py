from pathlib import Path

p = Path("editor/Medieval_Battlefield_Editor_v4.py")
s = p.read_text(encoding="utf-8")

lines = s.splitlines(True)
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("    def draw_obj(self,o):"):
        out.append(line)
        i += 1
        block = []
        while i < len(lines) and not (lines[i].startswith("    def ") or lines[i].startswith("    class ")):
            block.append(lines[i])
            i += 1

        # The road patches accidentally de-indented the entire draw_obj body.
        # If its first real statement is at method indentation, shift the
        # whole body one level right; this preserves all relative nesting.
        first = next((x for x in block if x.strip()), None)
        if first is not None and len(first) - len(first.lstrip(" ")) <= 4:
            block = [
                ("    " + x if x.strip() else x)
                for x in block
            ]
        out.extend(block)
        continue
    out.append(line)
    i += 1

s = "".join(out)
p.write_text(s, encoding="utf-8")

compile(s, str(p), "exec")
print("Python syntax check passed")
