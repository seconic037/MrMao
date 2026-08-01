#!/usr/bin/env python
"""MrMao 知识库桌面编辑器（Tkinter，零第三方依赖）。

按文件为最小单位管理知识库：
- 框架层 knowledge/framework/*.md（重启服务生效）
- 语料库 data/txt/知识扩展/*.txt（重建向量库生效）
服务器就是本机，直接读写项目目录。
"""
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
MD_DIR = ROOT / "knowledge" / "framework"
TXT_DIR = ROOT / "data" / "txt" / "知识扩展"
TRASH_DIR = ROOT / "新知识放这里" / "_已删除"
NSSM = ROOT / "tools" / "nssm" / "nssm-2.24" / "win64" / "nssm.exe"

READONLY_SUFFIX = "_全文.txt"
READONLY_SIZE = 1024 * 1024  # 1MB
ILLEGAL_CHARS = set('/\\:*?"<>|')
SERVICE_CANDIDATES = ["MrMao", "mrmao", "ChairManMao", "chairmanmao"]


def is_readonly(name: str, size: int) -> bool:
    """_全文.txt 结尾或大于 1MB 的文件视为只读（防误删）。"""
    return name.endswith(READONLY_SUFFIX) or size > READONLY_SIZE


def validate_filename(name: str, ftype: str) -> tuple[bool, str]:
    """校验文件名。ftype: "framework" -> .md, "corpus" -> .txt。

    自动补扩展名；拒绝空名、非法字符、路径穿越、错误扩展名、重名。
    返回 (ok, err_msg)。
    """
    name = (name or "").strip()
    if not name:
        return False, "文件名不能为空"
    if any(ch in ILLEGAL_CHARS for ch in name) or ".." in name:
        return False, "文件名不能包含 / \\ : * ? \" < > | 或 .."
    ext = ".md" if ftype == "framework" else ".txt"
    if name.endswith(ext):
        pass
    elif Path(name).suffix:
        # 已有其它扩展名（如 corpus 下传 .md），拒绝而非补全成 x.md.txt
        return False, "扩展名不匹配"
    else:
        name += ext
    target_dir = MD_DIR if ftype == "framework" else TXT_DIR
    if (target_dir / name).exists():
        return False, f"已存在同名文件: {name}"
    return True, name


def list_kb_files() -> dict[str, list[dict]]:
    """扫描两组目录，返回 {"framework": [...], "corpus": [...]}。

    每项 {"name", "size", "readonly"}，按文件名排序。
    """
    result = {}
    for key, d in (("framework", MD_DIR), ("corpus", TXT_DIR)):
        items = []
        for f in sorted(d.glob("*.md" if key == "framework" else "*.txt")):
            size = f.stat().st_size
            items.append({"name": f.name, "size": size, "readonly": is_readonly(f.name, size)})
        result[key] = items
    return result


def count_hits(text: str, query: str) -> int:
    """统计 query 在 text 中按行出现的总次数（每行 count 累计）。"""
    if not query:
        return 0
    return sum(line.count(query) for line in text.splitlines())


def search_files(query: str) -> list[tuple[str, str, int]]:
    """在框架层 + 语料库全文检索，返回 [(type, filename, hits)]。

    仅返回 hits>0 的文件，按 hits 降序。读取失败的单个文件跳过。
    """
    query = (query or "").strip()
    if not query:
        return []
    results: list[tuple[str, str, int]] = []
    for key, d in (("framework", MD_DIR), ("corpus", TXT_DIR)):
        pattern = "*.md" if key == "framework" else "*.txt"
        for f in sorted(d.glob(pattern)):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            hits = count_hits(text, query)
            if hits > 0:
                results.append((key, f.name, hits))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def create_file(ftype: str, filename: str, content: str) -> tuple[bool, str]:
    """新建文件（UTF-8）。成功返回 (True, 完整文件名)；失败返回 (False, 错误信息)。"""
    ok, err = validate_filename(filename, ftype)
    if not ok:
        return False, err
    target_dir = MD_DIR if ftype == "framework" else TXT_DIR
    try:
        (target_dir / err).write_text(content, encoding="utf-8")
        return True, err
    except Exception as e:
        return False, f"写入失败: {e}"


def trash_file(ftype: str, filename: str) -> tuple[bool, str]:
    """软删除：移动到 TRASH_DIR（同名加时间戳后缀）。只读文件拒绝。"""
    target_dir = MD_DIR if ftype == "framework" else TXT_DIR
    if Path(filename).name != filename:
        return False, "非法文件名"
    src = target_dir / filename
    if not src.exists():
        return False, f"文件不存在: {filename}"
    size = src.stat().st_size
    if is_readonly(filename, size):
        return False, f"只读文件不可删除: {filename}"
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    dest = TRASH_DIR / filename
    if dest.exists():
        dest = TRASH_DIR / f"{Path(filename).stem}_{datetime.now():%Y%m%d_%H%M%S}{src.suffix}"
    try:
        shutil.move(str(src), str(dest))
        return True, f"已移动到 {TRASH_DIR.name}/{dest.name}"
    except Exception as e:
        return False, f"删除失败: {e}"


# ── GUI ───────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox

SERVICE_STATUS: dict[str, str] = {}  # {"found": 服务名} 或 {"found": ""}


def detect_service() -> str:
    """探测 nssm 服务名，返回 RUNNING 的服务名；未找到返回空串。"""
    for name in SERVICE_CANDIDATES:
        try:
            r = subprocess.run(
                ["sc", "query", name], capture_output=True, text=True,
                encoding="utf-8", errors="ignore", timeout=5)
            if "RUNNING" in r.stdout.upper():
                return name
        except Exception:
            continue
    return ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📚 MrMao 知识库编辑器")
        self.geometry("1000x600")
        self.minsize(820, 480)

        self.status_var = tk.StringVar(value="就绪")
        self.service_name = detect_service()

        # 顶栏：服务器标签 + 重启服务按钮
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        ttk.Label(top, text="服务器：本机", font=("", 10, "bold")).pack(side=tk.LEFT)
        self.restart_btn = ttk.Button(top, text="🔁 重启服务", command=self.do_restart_service)
        self.restart_btn.pack(side=tk.RIGHT)
        self.restart_btn.state(["disabled"] if not self.service_name else ["!disabled"])
        if self.service_name:
            self.set_status(f"已检测到服务 {self.service_name}")

        # 主分栏
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        # 左：文件树
        left = ttk.Frame(paned)
        paned.add(left, weight=3)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # 右：操作面板（后续任务填充）
        right = ttk.Frame(paned)
        paned.add(right, weight=5)
        self.right = right

        # 底部状态栏
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=6)

        # 右侧：检索区
        search_frame = ttk.LabelFrame(self.right, text="🔍 检索命中文件")
        search_frame.pack(fill=tk.X, padx=8, pady=(8, 6))

        search_row = ttk.Frame(search_frame)
        search_row.pack(fill=tk.X, padx=8, pady=6)
        self.search_entry = ttk.Entry(search_row)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda e: self.do_search())
        ttk.Button(search_row, text="检索", command=self.do_search).pack(side=tk.LEFT, padx=(6, 0))

        self.search_list = tk.Listbox(search_frame, height=8)
        self.search_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.search_list.bind("<Double-Button-1>", lambda e: self._on_search_pick())

        # 右侧：新建区
        create_frame = ttk.LabelFrame(self.right, text="➕ 新建文件（一次性创建，不编辑现有内容）")
        create_frame.pack(fill=tk.X, padx=8, pady=6)

        row1 = ttk.Frame(create_frame)
        row1.pack(fill=tk.X, padx=8, pady=(6, 2))
        self.type_combo = ttk.Combobox(row1, state="readonly", width=14,
                                       values=["🧠 框架 .md", "📖 语料 .txt"])
        self.type_combo.current(0)
        self.type_combo.pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row1)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        self.content_text = tk.Text(create_frame, height=8)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        row2 = ttk.Frame(create_frame)
        row2.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Button(row2, text="创建文件", command=self.do_create).pack(side=tk.LEFT)
        ttk.Button(row2, text="🗑 删除选中", command=self.do_delete).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row2, text="🔄 刷新", command=self.refresh_tree).pack(side=tk.RIGHT)

        # 右侧：重建向量库进度区
        rebuild_frame = ttk.LabelFrame(self.right, text="🔄 重建向量库（语料变更后 3-10 分钟）")
        rebuild_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.rebuild_text = tk.Text(rebuild_frame, height=10, state=tk.DISABLED)
        self.rebuild_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        ttk.Button(rebuild_frame, text="▶ 开始重建", command=self.do_rebuild).pack(anchor=tk.W, padx=8, pady=(0, 6))
        self.is_rebuilding = False
        self._rebuild_proc = None

        self.refresh_tree()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 检索 ──────────────────────────────────────────
    def do_search(self):
        query = self.search_entry.get().strip()
        self.search_list.delete(0, tk.END)
        if not query:
            self.set_status("请输入关键词")
            return
        results = search_files(query)
        if not results:
            self.set_status(f"“{query}” 无命中")
            return
        for key, fname, hits in results:
            tag = "🧠" if key == "framework" else "📖"
            self.search_list.insert(tk.END, f"{tag} {fname}（{hits}处）")
        self.set_status(f"命中 {len(results)} 个文件")

    def _on_search_pick(self):
        sel = self.search_list.curselection()
        if not sel:
            return
        line = self.search_list.get(sel[0])
        fname = line.split("（")[0].split(" ", 1)[1]
        hits = line.split("（")[1].rstrip("）")          # 形如 "25处"
        loc = "data/txt/知识扩展/" if "📖" in line else "knowledge/framework/"
        self.set_status(f"{fname} 位于 {loc}，共 {hits}")

    # ── 文件树 ────────────────────────────────────────
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        data = list_kb_files()
        labels = {"framework": "🧠 框架层（重启服务生效）", "corpus": "📖 语料库（重建向量库生效）"}
        for key in ("framework", "corpus"):
            parent = self.tree.insert("", "end", text=labels[key], open=True)
            for item in data[key]:
                flag = "🔒 " if item["readonly"] else ""
                size_kb = item["size"] / 1024
                size_txt = f"{size_kb:.0f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                self.tree.insert(parent, "end", text=f"{flag}{item['name']} ({size_txt})",
                                 values=(key, item["name"], item["readonly"]))

    def selected_file(self) -> tuple[str, str, bool] | None:
        """返回选中的 (type, filename, readonly)，未选中或选中组节点返回 None。"""
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return None
        return vals[0], vals[1], vals[2] in (True, "True")

    def set_status(self, msg: str):
        self.status_var.set(msg)

    # ── 新建 / 删除 ───────────────────────────────────
    def do_create(self):
        ftype = "framework" if "框架" in self.type_combo.get() else "corpus"
        name = self.name_entry.get()
        content = self.content_text.get("1.0", tk.END).rstrip("\n")
        if not content.strip():
            if not messagebox.askyesno("内容为空", "新文件内容为空，是否仍要创建？", parent=self):
                return
        ok, err = create_file(ftype, name, content)
        if not ok:
            messagebox.showerror("创建失败", err, parent=self)
            return
        self.set_status(f"已创建 {ftype}/{err}：" + ("重启服务后生效" if ftype == "framework" else "需重建向量库后生效"))
        self.refresh_tree()
        self.name_entry.delete(0, tk.END)
        self.content_text.delete("1.0", tk.END)

    def do_delete(self):
        sel = self.selected_file()
        if not sel:
            self.set_status("请先在左侧选中一个文件")
            return
        ftype, fname, readonly = sel
        if readonly:
            messagebox.showwarning("只读文件", f"🔒 {fname} 为卷本/大文件，不可删除", parent=self)
            return
        if not messagebox.askyesno("确认删除", f"将把 {fname} 移动到 新知识放这里/_已删除/ 备份。\n确定？", parent=self):
            return
        ok, msg = trash_file(ftype, fname)
        if not ok:
            messagebox.showerror("删除失败", msg, parent=self)
            return
        self.set_status(f"已删除 {fname}：{msg}。" + ("重启服务后生效" if ftype == "framework" else "需重建向量库后生效"))
        self.refresh_tree()

    # ── 重建向量库 ────────────────────────────────────
    def _append_rebuild(self, line: str):
        self.rebuild_text.configure(state=tk.NORMAL)
        self.rebuild_text.insert(tk.END, line)
        self.rebuild_text.see(tk.END)
        self.rebuild_text.configure(state=tk.DISABLED)

    def do_rebuild(self):
        if self.is_rebuilding:
            self.set_status("重建进行中，请等待完成")
            return
        self.is_rebuilding = True
        self._append_rebuild("\n" + "=" * 50 + "\n开始重建向量库...\n")
        import threading
        threading.Thread(target=self._rebuild_worker, daemon=True).start()

    def _rebuild_worker(self):
        try:
            proc = subprocess.Popen(
                ["python", "run_pipeline.py"],
                cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace")
            self._rebuild_proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                self.after(0, self._append_rebuild, line)
            code = proc.wait()
            self.after(0, self._append_rebuild, f"\n退出码 {code}：" + ("重建成功" if code == 0 else "重建失败，见上方日志\n"))
            self.after(0, self._finish_rebuild, code)
        except Exception as e:
            self.after(0, self._finish_rebuild, None, str(e))

    def _finish_rebuild(self, code, err=""):
        """重建收尾（在主线程执行）。"""
        self.is_rebuilding = False
        if err:
            self.set_status(f"重建异常: {err}")
        else:
            self.set_status("重建成功" if code == 0 else "重建失败")

    def _on_close(self):
        """关窗：若正在重建则终止子进程，避免 run_pipeline 残留为孤儿。"""
        if getattr(self, "_rebuild_proc", None) is not None and self.is_rebuilding:
            try:
                self._rebuild_proc.terminate()
            except Exception:
                pass
        self.destroy()

    # ── 重启服务 ──────────────────────────────────────
    def do_restart_service(self):
        if not self.service_name:
            messagebox.showinfo("提示", "未检测到 nssm 服务。\n请手动重启：python run_server.py", parent=self)
            return
        if not messagebox.askyesno("重启服务", f"将重启服务 {self.service_name}，确认？", parent=self):
            return
        try:
            r = subprocess.run([str(NSSM), "restart", self.service_name],
                               capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60)
            self.set_status(f"重启服务结果: {r.returncode} {r.stdout.strip() or r.stderr.strip()}")
        except Exception as e:
            self.set_status(f"重启服务异常: {e}")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
