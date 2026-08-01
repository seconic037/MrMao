# tests/smoke_gui.py — 冒烟：启动主窗口并自动关闭
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import kb_editor as kb

app = kb.App()
app.after(500, app.destroy)
app.mainloop()
print("SMOKE OK")
