#!/usr/bin/env python
"""MrMao 知识库工作流编辑器 v2（Tkinter，零第三方依赖）。

四步工作流：①新知识(刷新/去重/分类) → ②待上传清单 → ③本次更改 → ④同步与生效。
知识库页：树形浏览 + 只读预览 + 检索 + 标记删除。
规格：docs/superpowers/specs/2026-08-01-kb-editor-v2-design.md
"""
import os, re, shutil, socket, subprocess, sys, threading
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "新知识放这里"
MD_DIR = ROOT / "knowledge" / "framework"
TXT_DIR = ROOT / "data" / "txt" / "知识扩展"
ARCHIVE = INBOX / "_已处理"
TRASH_DIR = INBOX / "_已删除"
NSSM = ROOT / "tools" / "nssm" / "nssm-2.24" / "win64" / "nssm.exe"
SERVICE_CANDIDATES = ["MrMao", "mrmao", "ChairManMao", "chairmanmao"]
PORT = 8000
READONLY_SUFFIX = "_全文.txt"
READONLY_SIZE = 1024 * 1024
ILLEGAL_CHARS = set('/\\:*?"<>|')

# 从 tools/ingest_knowledge.py 复制（保持命令行工具不动）
TOPIC_RULES = {
    "经济学": ["经济", "资本", "市场", "贸易", "货币", "金融", "马歇尔", "斯密", "费特"],
    "哲学": ["哲学", "思维", "逻辑", "辩证", "形而上学"],
    "历史": ["历史", "史", "朝代", "战争", "革命", "党史"],
    "兵法战略": ["兵法", "战略", "三十六计", "孙子"],
    "文学": ["文学", "诗", "词", "小说", "名著"],
    "科学": ["科学", "数学", "物理", "化学", "生物", "统计"],
}
AUTO_GENERATED = {"NPC知识库情况.md", "README.md"}


def classify_md(filename: str) -> str:
    """按文件名关键词推断主题文件，沿用 ingest_knowledge 规则。"""
    basename = Path(filename).stem
    for topic, keywords in TOPIC_RULES.items():
        for kw in keywords:
            if kw in basename:
                return f"{topic}.md"
    return basename + ".md"


def classify_file(path: Path) -> str:
    """按扩展名分类：.md -> framework，.txt -> corpus。"""
    return "framework" if path.suffix.lower() == ".md" else "corpus"


def stem_key(name: str) -> str:
    """归一化文件名主干：去扩展名、去 _BTS/_ST/_plus/PLUS/数字后缀。"""
    base = Path(name).stem
    base = re.sub(r"[_\-]?(BTS|ST|PLUS|plus|_plus|精选|精要)", "", base)
    return re.sub(r"[\s_\-]+", "", base).lower()


def scan_inbox(inbox: Path) -> list[dict]:
    """扫描收件箱顶层 .md/.txt，排除自动生成文件；返回按文件名排序的清单。"""
    items = []
    for f in sorted(inbox.glob("*.md")) + sorted(inbox.glob("*.txt")):
        if f.name in AUTO_GENERATED:
            continue
        items.append({"name": f.name, "path": f, "ftype": classify_file(f), "size": f.stat().st_size})
    items.sort(key=lambda x: x["name"])
    return items


def detect_duplicate(name: str, text: str, md_dir: Path, txt_dir: Path) -> str:
    """去重检测：同名 -> 同主干 -> 内容相似（首 500 字）。返回标记或空串。"""
    key = stem_key(name)
    for d in (md_dir, txt_dir):
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if f.name == name:
                return "同名"
            if stem_key(f.name) == key:
                return "同主干"
    head = text[:500]
    if head.strip():
        for d in (md_dir, txt_dir):
            if not d.exists():
                continue
            for f in d.iterdir():
                if not f.is_file():
                    continue
                try:
                    other = f.read_text(encoding="utf-8")[:500]
                except Exception:
                    continue
                if other and head == other:
                    return "内容相似"
    return ""


def preview_file(path: Path) -> str:
    """只读预览：读取 UTF-8 全文；失败抛出异常由 GUI 捕获提示。"""
    return path.read_text(encoding="utf-8")


def is_readonly(name: str, size: int) -> bool:
    """_全文.txt 结尾或大于 1MB 视为只读（防误删）。"""
    return name.endswith(READONLY_SUFFIX) or size > READONLY_SIZE


def list_kb_files() -> dict[str, list[dict]]:
    """扫描框架层与语料库，返回 {"framework": [...], "corpus": [...]}，按文件名排序。"""
    result = {}
    for key, d in (("framework", MD_DIR), ("corpus", TXT_DIR)):
        items = []
        pattern = "*.md" if key == "framework" else "*.txt"
        for f in sorted(d.glob(pattern)):
            size = f.stat().st_size
            items.append({"name": f.name, "size": size, "readonly": is_readonly(f.name, size)})
        result[key] = items
    return result


def count_hits(text: str, query: str) -> int:
    if not query:
        return 0
    return sum(line.count(query) for line in text.splitlines())


def search_files(query: str) -> list[tuple[str, str, int]]:
    """在框架层 + 语料库全文检索，返回 [(type, filename, hits)]，按 hits 降序。"""
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


def _safe_child(base: Path, name: str) -> Path:
    """校验 name 是 base 的直接子文件名，防路径穿越；非法抛 ValueError。"""
    if Path(name).name != name or name in ("", ".") or ".." in name or any(c in ILLEGAL_CHARS for c in name):
        raise ValueError(f"非法文件名: {name}")
    return base / name


def apply_changelist(new_items: list[dict], delete_items: list[dict], root: Path) -> list[str]:
    """执行本次更改：md 合并/新建、txt 复制、软删除、归档。返回日志行。

    原子性：先完成全部目标写入与删除移动，全部成功后才归档收件箱原文件；
    任一步失败 → 撤销已执行操作并返回含"失败/回滚"的日志。
    """
    logs: list[str] = []
    md_dir = root / "knowledge" / "framework"
    txt_dir = root / "data" / "txt" / "知识扩展"
    inbox = root / "新知识放这里"
    trash = inbox / "_已删除"
    archive = inbox / "_已处理"
    # 记录已执行操作用于回滚：(kind, path, extra)
    #   create:  ("create", dest, None)             → 回滚 unlink
    #   merge:   ("merge", dest, 原内容或None)       → 回滚写回原内容 / unlink
    #   delete:  ("delete", src原路径, 软删除目标名)  → 回滚 move 还原到原路径
    #   archive: ("archive", 已归档dest, 收件箱源路径) → 回滚 move 还原回收件箱
    done: list[tuple[str, Path, str | None]] = []

    try:
        # 1) 新增
        for item in new_items:
            src = Path(item["src"])
            target = item["target"]
            merge_target = item.get("merge_target")
            if target == "framework":
                md_dir.mkdir(parents=True, exist_ok=True)
                if merge_target:
                    dest = _safe_child(md_dir, merge_target)
                    if not dest.name.endswith(".md"):
                        dest = md_dir / (Path(merge_target).stem + ".md")
                    original = dest.read_text(encoding="utf-8") if dest.exists() else None
                    text = src.read_text(encoding="utf-8")
                    with dest.open("a", encoding="utf-8") as df:
                        df.write("\n\n---\n" + text)
                    done.append(("merge", dest, original))
                    logs.append(f"🧠 MD → 合并到 knowledge/framework/{dest.name}")
                else:
                    dest = _safe_child(md_dir, src.name)
                    if dest.exists():
                        raise ValueError(f"目标已存在: {dest.name}")
                    shutil.copy2(src, dest)
                    done.append(("create", dest, None))
                    logs.append(f"🧠 MD → 新建 knowledge/framework/{dest.name}")
            else:  # corpus
                txt_dir.mkdir(parents=True, exist_ok=True)
                dest = _safe_child(txt_dir, src.name)
                if dest.exists():
                    raise ValueError(f"目标已存在: {dest.name}")
                shutil.copy2(src, dest)
                done.append(("create", dest, None))
                logs.append(f"📖 TXT → data/txt/知识扩展/{dest.name}")
        # 2) 删除（软删除）
        for item in delete_items:
            ftype, name = item["ftype"], item["name"]
            base = md_dir if ftype == "framework" else txt_dir
            src = _safe_child(base, name)
            if not src.exists():
                raise ValueError(f"待删除文件不存在: {name}")
            size = src.stat().st_size
            if is_readonly(name, size):
                raise ValueError(f"只读文件不可删除: {name}")
            trash.mkdir(parents=True, exist_ok=True)
            dest = trash / name
            if dest.exists():
                dest = trash / f"{Path(name).stem}_{datetime.now():%Y%m%d_%H%M%S}{src.suffix}"
            shutil.move(str(src), str(dest))
            done.append(("delete", src, dest.name))
            logs.append(f"🗑 软删除 → 新知识放这里/_已删除/{dest.name}")
        # 3) 全部成功 → 归档收件箱原文件
        archive.mkdir(parents=True, exist_ok=True)
        for item in new_items:
            src = Path(item["src"])
            if src.exists():
                dest = archive / src.name
                if dest.exists():
                    dest = archive / f"{Path(src.name).stem}_{datetime.now():%Y%m%d_%H%M%S}{src.suffix}"
                shutil.move(str(src), str(dest))
                done.append(("archive", dest, str(src)))
        logs.append("✅ 本次更改已全部落盘")
        return logs
    except Exception as e:
        logs.append(f"❌ 落盘失败: {e}")
        # 回滚：撤销已执行操作，逐项捕获失败并如实报告
        failures: list[str] = []
        for kind, path, extra in reversed(done):
            try:
                if kind == "create":
                    if path.exists():
                        path.unlink()
                elif kind == "merge":
                    if extra is None:
                        # merge 前目标不存在 → 删除本次创建的副本
                        if path.exists():
                            path.unlink()
                    else:
                        # 写回 merge 前原内容，恢复原状而非连旧内容一起删除
                        path.write_text(extra, encoding="utf-8")
                elif kind == "delete":
                    # 从 _已删除 还原到原路径
                    backup = trash / extra
                    if not backup.exists():
                        raise FileNotFoundError(f"软删除副本不存在: {extra}")
                    if path.exists():
                        logs.append(f"⚠️ 还原跳过：原路径已存在 {path}")
                    else:
                        shutil.move(str(backup), str(path))
                elif kind == "archive":
                    # 还原回收件箱源路径（而非 unlink，避免三处全失）
                    src_back = Path(extra)
                    if path.exists():
                        if src_back.exists():
                            src_back = src_back.with_name(
                                f"{src_back.stem}_{datetime.now():%Y%m%d_%H%M%S}{src_back.suffix}"
                            )
                        shutil.move(str(path), str(src_back))
                else:
                    raise ValueError(f"未知回滚操作: {kind}")
            except Exception as ex:
                failures.append(f"{path.name}({ex})")
        if failures:
            logs.append(f"⚠️ 部分回滚失败：{', '.join(failures)}，请手动检查")
        else:
            logs.append("✅ 已回滚本次更改（磁盘恢复原状）")
        return logs


def server_running(port: int = PORT) -> bool:
    """探测 127.0.0.1:port 是否有服务在监听。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _nssm_service_running() -> str:
    """返回 RUNNING 的 nssm 服务名，无则空串。"""
    for name in SERVICE_CANDIDATES:
        try:
            r = subprocess.run(["sc", "query", name], capture_output=True, text=True,
                               encoding="utf-8", errors="ignore", timeout=5)
            if "RUNNING" in r.stdout.upper():
                return name
        except Exception:
            continue
    return ""


def _pid_on_port(port: int) -> int:
    """通过 netstat 找 8000 端口 PID；找不到返回 0。"""
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=10)
        for line in r.stdout.splitlines():
            parts = line.split()
            # 本地地址精确匹配端口，避免 :8000 误命中 :80001 等
            if (len(parts) > 1 and parts[1].endswith(f":{port}")
                    and "LISTENING" in line.upper()):
                if parts and parts[-1].isdigit():
                    return int(parts[-1])
    except Exception:
        pass
    return 0


def restart_server() -> str:
    """重启服务器：优先 nssm 服务；否则杀 8000 端口进程后后台启动 run_server.py。"""
    logs = []
    svc = _nssm_service_running()
    if svc:
        r = subprocess.run([str(NSSM), "restart", svc], capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=60)
        logs.append(f"🔄 nssm restart {svc} → 退出码 {r.returncode}")
    else:
        pid = _pid_on_port(PORT)
        if pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, text=True, timeout=10)
            logs.append(f"🛑 已终止旧进程 PID {pid}")
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["python", "run_server.py"], cwd=str(ROOT),
                         creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logs.append("🚀 已后台启动 python run_server.py")
    # 等待端口恢复（最多 30s）
    import time
    for _ in range(30):
        if server_running(PORT):
            logs.append("✅ 服务器已就绪（8000 端口可访问）")
            return "\n".join(logs)
        time.sleep(1)
    logs.append("⏳ 等待超时：服务器未在 30s 内就绪，请手动检查 python run_server.py")
    return "\n".join(logs)


# ══════════════════════════════════════════════════════════════════
#  GUI 部分（Task 6：双标签 + 步骤条 + 服务器状态灯）
# ══════════════════════════════════════════════════════════════════
import tkinter as tk
from tkinter import ttk, messagebox


class App(tk.Tk):
    """主窗口：工作流（四步向导）+ 知识库（浏览/检索/标记删除）双标签页。"""

    STEP_TITLES = ["① 新知识", "② 待上传清单", "③ 本次更改", "④ 同步与生效"]

    def __init__(self):
        super().__init__()
        self.title("📚 MrMao 知识库工作流编辑器")
        self.geometry("1100x680")
        self.minsize(900, 560)

        self.status_var = tk.StringVar(value="就绪")
        self.server_var = tk.StringVar(value="检测中…")

        # ── 顶栏：标题 + 服务器状态灯 + 手动重启 ──
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=(6, 0))
        ttk.Label(top, text="📚 MrMao 知识库编辑器", font=("", 11, "bold")).pack(side=tk.LEFT)
        self.server_light = ttk.Label(top, textvariable=self.server_var)
        self.server_light.pack(side=tk.RIGHT)
        ttk.Button(top, text="🔁 重启服务器", command=self.do_restart_server).pack(side=tk.RIGHT, padx=(0, 8))

        # ── 主笔记本：工作流 / 知识库 ──
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.wf_tab = ttk.Frame(self.notebook)
        self.kb_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.wf_tab, text="🔧 工作流")
        self.notebook.add(self.kb_tab, text="📚 知识库")

        # ── 工作流：步骤条 ──
        self.step_bar = ttk.Frame(self.wf_tab)
        self.step_bar.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.step_btns: dict[int, ttk.Button] = {}
        for i, title in enumerate(self.STEP_TITLES, start=1):
            btn = ttk.Button(self.step_bar, text=title, command=lambda n=i: self.show_step(n))
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self.step_btns[i] = btn
        self.step_container = ttk.Frame(self.wf_tab)
        self.step_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.step_panels: dict[int, ttk.Frame] = {}
        self.current_step = 0

        # ── 状态栏 ──
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=6)

        self._build_step_panels()
        self._build_kb_tab()
        self.show_step(1)
        self.refresh_server_light()
        self.after(30000, self._poll_server)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 通用 ──
    def set_status(self, msg: str):
        self.status_var.set(msg)

    def show_step(self, n: int):
        """切换工作流步骤面板（1-4），并同步步骤条高亮。"""
        if self.current_step:
            self.step_panels[self.current_step].pack_forget()
        self.current_step = n
        self.step_panels[n].pack(fill=tk.BOTH, expand=True)
        for i, btn in self.step_btns.items():
            btn.state(["!disabled"])
            if i == n:
                btn.state(["pressed"])

    def refresh_server_light(self):
        self.server_var.set("🟢 服务器运行中" if server_running() else "🔴 服务器未运行")

    def _poll_server(self):
        self.refresh_server_light()
        self.after(30000, self._poll_server)

    def do_restart_server(self):
        if not messagebox.askyesno("重启服务器", "将重启服务器使框架层改动生效，确认？", parent=self):
            return
        self.set_status("正在重启服务器…")
        import threading as _t
        _t.Thread(target=self._restart_worker, daemon=True).start()

    def _restart_worker(self):
        log = restart_server()
        self.after(0, self._show_restart_result, log)

    def _show_restart_result(self, log: str):
        self.set_status("服务器重启完成" if "已就绪" in log else "服务器重启异常")
        self.refresh_server_light()
        if hasattr(self, "log_text"):
            self._append_log(log)

    def _append_log(self, text: str):
        if hasattr(self, "log_text"):
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)

    def _on_close(self):
        if getattr(self, "_rebuild_proc", None) is not None and getattr(self, "is_rebuilding", False):
            try:
                self._rebuild_proc.terminate()
            except Exception:
                pass
        self.destroy()

    def _build_step_panels(self):
        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_step4()

    # ── 步骤① 新知识 ──
    def _build_step1(self):
        p = ttk.Frame(self.step_container)
        self.step_panels[1] = p
        hint = ("📥 把 TXT/MD 文件丢进「新知识放这里」文件夹，然后点「刷新资料库」\n"
                "系统会自动：分类（.md→🧠框架 / .txt→📖语料）+ 去重检测（⚠️疑似重复）")
        ttk.Label(p, text=hint, foreground="#555").pack(anchor=tk.W, padx=8, pady=6)

        row = ttk.Frame(p)
        row.pack(fill=tk.X, padx=8)
        self.refresh_btn = ttk.Button(row, text="🔄 刷新资料库", command=self.do_refresh)
        self.refresh_btn.pack(side=tk.LEFT)
        self.next1_btn = ttk.Button(row, text="下一步 →", command=self.next_from_step1)
        self.next1_btn.pack(side=tk.RIGHT)
        self.next1_btn.state(["disabled"])

        cols = ("name", "ftype", "dup", "size")
        self.inbox_tree = ttk.Treeview(p, columns=cols, show="headings", height=10)
        for c, w, t in (("name", 320, "文件"), ("ftype", 90, "分类"),
                        ("dup", 120, "去重检测"), ("size", 80, "大小")):
            self.inbox_tree.heading(c, text=t)
            self.inbox_tree.column(c, width=w, anchor="w")
        self.inbox_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.inbox_tree.bind("<Double-Button-1>", lambda e: self._preview_selected(self.inbox_tree))
        self.inbox_tree.bind("<<TreeviewSelect>>", lambda e: self._update_inbox_remove())

        btn_row = ttk.Frame(p)
        btn_row.pack(fill=tk.X, padx=8)
        self.remove1_btn = ttk.Button(btn_row, text="移除选中（本次不处理）", command=self.on_inbox_remove)
        self.remove1_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="🔍 预览", command=lambda: self._preview_selected(self.inbox_tree)).pack(side=tk.LEFT, padx=(8, 0))
        self.inbox_items: list[dict] = []
        self._preview_pane: tk.Text | None = None

    def do_refresh(self):
        items = scan_inbox(INBOX)
        for it in items:
            try:
                text = it["path"].read_text(encoding="utf-8")
                it["dup"] = detect_duplicate(it["name"], text, MD_DIR, TXT_DIR)
            except Exception:
                it["dup"] = ""
        self.inbox_items = items
        self.inbox_tree.delete(*self.inbox_tree.get_children())
        for it in items:
            flag = {"": "", "同名": "⚠️同名", "同主干": "⚠️同主干", "内容相似": "⚠️内容相似"}[it["dup"]]
            tag = "🧠" if it["ftype"] == "framework" else "📖"
            size_kb = it["size"] / 1024
            self.inbox_tree.insert("", "end", values=(
                it["name"], f"{tag} {it['ftype']}", flag,
                f"{size_kb:.0f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"))
        self.next1_btn.state(["!disabled"] if items else ["disabled"])
        self.set_status(f"发现 {len(items)} 个新文件" + ("，含疑似重复请留意" if any(i["dup"] for i in items) else ""))

    def on_inbox_remove(self):
        sel = self.inbox_tree.selection()
        if not sel:
            return
        iid = sel[0]
        name = self.inbox_tree.item(iid, "values")[0]
        self.inbox_items = [i for i in self.inbox_items if i["name"] != name]
        self.inbox_tree.delete(iid)
        self.set_status(f"已移除 {name}（本次不处理）")

    def _update_inbox_remove(self):
        pass  # 占位：保持按钮可用性

    def _preview_selected(self, tree):
        sel = tree.selection()
        if not sel:
            return
        name = tree.item(sel[0], "values")[0]
        path = self._path_by_name(tree, name)
        if path:
            self.show_preview(path)

    def _path_by_name(self, tree, name: str):
        # inbox_tree: 从 self.inbox_items 找；kb 树：从 tree 的 values 里取
        for it in self.inbox_items:
            if it["name"] == name:
                return it["path"]
        return None

    def show_preview(self, path):
        """打开只读预览弹窗（模态 Toplevel）。"""
        win = tk.Toplevel(self)
        win.title(f"预览：{Path(path).name}")
        win.geometry("640x480")
        txt = tk.Text(win, wrap="word")
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        try:
            txt.insert("1.0", preview_file(path))
        except Exception as e:
            txt.insert("1.0", f"无法读取文件：{e}")
        txt.configure(state=tk.DISABLED)

    # ── 步骤② 待上传清单 ──
    def _build_step2(self):
        p = ttk.Frame(self.step_container)
        self.step_panels[2] = p
        ttk.Label(p, text="📋 待上传清单：确认分类目标，可移除或预览", foreground="#555").pack(anchor=tk.W, padx=8, pady=6)
        back = ttk.Frame(p)
        back.pack(fill=tk.X, padx=8)
        ttk.Button(back, text="← 上一步", command=self.back_to_step1).pack(side=tk.LEFT)
        ttk.Button(back, text="🗑 移除选中", command=self.on_stage_remove).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(back, text="分类目标:").pack(side=tk.LEFT, padx=(10, 2))
        self.stage_target_combo = ttk.Combobox(back, state="readonly", width=28)
        self.stage_target_combo["values"] = self._merge_targets()
        self.stage_target_combo.state(["disabled"])
        self.stage_target_combo.pack(side=tk.LEFT)
        self.next2_btn = ttk.Button(back, text="下一步 →", command=self.next_from_step2)
        self.next2_btn.pack(side=tk.RIGHT)

        cols = ("name", "target", "size")
        self.stage_tree = ttk.Treeview(p, columns=cols, show="headings", height=10)
        for c, w, t in (("name", 300, "文件"), ("target", 260, "分类目标"), ("size", 80, "大小")):
            self.stage_tree.heading(c, text=t)
            self.stage_tree.column(c, width=w, anchor="w")
        self.stage_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.stage_tree.bind("<Double-Button-1>", lambda e: self._preview_stage())
        self.stage_tree.bind("<<TreeviewSelect>>", self._on_stage_select)
        self.stage_target_combo.bind("<<ComboboxSelected>>", self._on_stage_target_change)
        self.stage_items: list[dict] = []

    def _on_stage_select(self, _event=None):
        """选中待上传行时：framework 行联动分类目标下拉，corpus 行禁用下拉。"""
        sel = self.stage_tree.selection()
        if not sel:
            self.stage_target_combo.set("")
            self.stage_target_combo.state(["disabled"])
            return
        it = self.stage_items[int(sel[0])]
        if it["ftype"] == "framework":
            self.stage_target_combo["values"] = self._merge_targets()
            self.stage_target_combo.set(f"合并到 {it['merge_target']}" if it["merge_target"] else "新建独立文件")
            self.stage_target_combo.state(["!disabled"])
        else:
            self.stage_target_combo.set("")
            self.stage_target_combo.state(["disabled"])

    def _on_stage_target_change(self, _event=None):
        """下拉变更时更新该 framework 行的 merge_target，并重渲该行。"""
        sel = self.stage_tree.selection()
        if not sel:
            return
        i = int(sel[0])
        value = self.stage_target_combo.get()
        if value.startswith("合并到 "):
            self.stage_items[i]["merge_target"] = value[len("合并到 "):]
        elif value == "新建独立文件":
            self.stage_items[i]["merge_target"] = None
        else:
            return
        self._render_stage()
        self.stage_tree.selection_set(str(i))
        self._on_stage_select()
        self.set_status(f"已更新 {self.stage_items[i]['name']} 的分类目标")

    def _merge_targets(self) -> list[str]:
        return sorted(f"合并到 {f}" for f in sorted(p.name for p in MD_DIR.glob("*.md"))) + ["新建独立文件"]

    def next_from_step1(self):
        self.stage_items = []
        for it in self.inbox_items:
            if it["ftype"] == "framework":
                merge = classify_md(it["name"])
                self.stage_items.append({"name": it["name"], "path": it["path"], "ftype": "framework",
                                         "merge_target": merge if (MD_DIR / merge).exists() else None,
                                         "size": it["size"]})
            else:
                self.stage_items.append({"name": it["name"], "path": it["path"], "ftype": "corpus",
                                         "merge_target": None, "size": it["size"]})
        self._render_stage()
        self.stage_target_combo["values"] = self._merge_targets()
        self.show_step(2)

    def _render_stage(self):
        self.stage_tree.delete(*self.stage_tree.get_children())
        for i, it in enumerate(self.stage_items):
            if it["ftype"] == "framework":
                target = f"合并到 {it['merge_target']}" if it["merge_target"] else "新建独立文件"
            else:
                target = "语料库 data/txt/知识扩展/"
            self.stage_tree.insert("", "end", iid=str(i), values=(it["name"], target, it["size"]))
        self.next2_btn.state(["!disabled"] if self.stage_items else ["disabled"])

    def _preview_stage(self):
        sel = self.stage_tree.selection()
        if not sel:
            return
        it = self.stage_items[int(sel[0])]
        self.show_preview(it["path"])

    def on_stage_remove(self):
        sel = self.stage_tree.selection()
        if not sel:
            self.set_status("请先选中一个待上传文件")
            return
        idx = int(sel[0])
        it = self.stage_items.pop(idx)
        self._render_stage()
        self.stage_target_combo.set("")
        self.stage_target_combo.state(["disabled"])
        self.set_status(f"已从待上传清单移除 {it['name']}")

    def back_to_step1(self):
        self.show_step(1)

    def next_from_step2(self):
        self._render_change_tree()
        self.show_step(3)

    # ── 步骤③ 本次更改清单 ──
    def _build_step3(self):
        p = ttk.Frame(self.step_container)
        self.step_panels[3] = p
        ttk.Label(p, text="📦 本次更改清单（草稿，磁盘暂不动）：", foreground="#555").pack(anchor=tk.W, padx=8, pady=6)

        nav = ttk.Frame(p); nav.pack(fill=tk.X, padx=8)
        ttk.Button(nav, text="← 上一步", command=lambda: self.show_step(2)).pack(side=tk.LEFT)
        self.next3_btn = ttk.Button(nav, text="下一步 →", command=self.next_from_step3)
        self.next3_btn.pack(side=tk.RIGHT)

        cols = ("kind", "name", "detail")
        self.change_tree = ttk.Treeview(p, columns=cols, show="headings", height=12)
        for c, w, t in (("kind", 70, "类型"), ("name", 280, "文件"), ("detail", 300, "去向")):
            self.change_tree.heading(c, text=t); self.change_tree.column(c, width=w, anchor="w")
        self.change_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.summary_var = tk.StringVar(value="本次共新增 0 / 删除 0")
        ttk.Label(p, textvariable=self.summary_var, font=("", 10, "bold")).pack(anchor=tk.W, padx=8)
        self.kb_delete_items: list[dict] = []

    def next_from_step3(self):
        self._render_change_tree()
        self.show_step(4)

    def _render_change_tree(self):
        self.change_tree.delete(*self.change_tree.get_children())
        for it in self.stage_items:
            detail = f"合并到 knowledge/framework/{it['merge_target']}" if it["merge_target"] else (
                "新建 knowledge/framework/" if it["ftype"] == "framework" else "复制到 data/txt/知识扩展/")
            self.change_tree.insert("", "end", values=("➕新增", it["name"], detail))
        for it in self.kb_delete_items:
            self.change_tree.insert("", "end", values=("🗑删除", it["name"], "移动到 新知识放这里/_已删除/"))
        self.summary_var.set(f"本次共新增 {len(self.stage_items)} / 删除 {len(self.kb_delete_items)}")

    # ── 步骤④ 同步与生效 ──
    def _build_step4(self):
        p = ttk.Frame(self.step_container)
        self.step_panels[4] = p
        ttk.Label(p, text="🚀 同步与生效：确认后开始上传（原子落盘，失败自动回滚）", foreground="#555").pack(anchor=tk.W, padx=8, pady=6)
        nav = ttk.Frame(p); nav.pack(fill=tk.X, padx=8)
        ttk.Button(nav, text="← 上一步", command=lambda: self.show_step(3)).pack(side=tk.LEFT)
        self.upload_btn = ttk.Button(nav, text="▶ 开始上传（落盘）", command=self.do_upload)
        self.upload_btn.pack(side=tk.RIGHT)

        self.log_text = tk.Text(p, height=12, state=tk.DISABLED, wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.is_uploading = False
        self._rebuild_proc = None
        self.is_rebuilding = False

    def do_upload(self):
        if self.is_uploading or self.is_rebuilding:
            self.set_status("上传/重建进行中，请等待")
            return
        if not messagebox.askyesno("开始上传", "将执行本次更改并落盘（新增/合并/软删除），确认？", parent=self):
            return
        self.is_uploading = True
        self.upload_btn.state(["disabled"])
        self._append_log("\n" + "=" * 50 + "\n▶ 开始上传…\n")
        threading.Thread(target=self._upload_worker, daemon=True).start()

    def _upload_worker(self):
        new_items = [{"src": it["path"], "target": it["ftype"], "merge_target": it["merge_target"]}
                     for it in self.stage_items]
        logs = apply_changelist(new_items, self.kb_delete_items, ROOT)
        self.after(0, self._upload_finished, logs)

    def _upload_finished(self, logs):
        for line in logs:
            self._append_log(line)
        self.is_uploading = False
        ok = not any("失败" in line or "回滚" in line for line in logs)
        if not ok:
            self.upload_btn.state(["!disabled"])
            self.set_status("上传失败已回滚，请检查日志")
            return
        # 自动判断生效方式
        has_corpus = (any(it["ftype"] == "corpus" for it in self.stage_items)
                      or any(it["ftype"] == "corpus" for it in self.kb_delete_items))
        if has_corpus:
            self.set_status("含语料库改动，开始重建向量库（3-10 分钟）…")
            self._append_log("\n📖 检测到语料库改动，开始重建向量库…\n")
            self._start_rebuild()
        else:
            self.set_status("仅框架改动，重启服务器生效…")
            self._append_log("\n🧠 仅框架改动，重启服务器…\n")
            threading.Thread(target=self._restart_after_upload, daemon=True).start()

    def _restart_after_upload(self):
        log = restart_server()
        self.after(0, self._done_all, log)

    def _done_all(self, log: str):
        self._append_log(log)
        self._append_log("\n✅ NPC 已拥有新思想！")
        self.set_status("完成：NPC 已拥有新思想")
        # 一轮完成后恢复上传按钮，允许进行第二批上传（is_uploading/is_rebuilding 防抖已保证安全）
        self.upload_btn.state(["!disabled"])
        self.refresh_server_light()

    def _start_rebuild(self):
        self.is_rebuilding = True
        threading.Thread(target=self._rebuild_worker, daemon=True).start()

    def _rebuild_worker(self):
        try:
            proc = subprocess.Popen(["python", "run_pipeline.py"], cwd=str(ROOT),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            self._rebuild_proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                self.after(0, self._append_log, line)
            code = proc.wait()
            self.after(0, self._rebuild_done, code)
        except Exception as e:
            self.after(0, self._rebuild_done, -1, str(e))

    def _rebuild_done(self, code, err=""):
        self.is_rebuilding = False
        if err:
            self._append_log(f"❌ 重建异常: {err}")
            return
        self._append_log(f"\n重建退出码 {code}：" + ("成功" if code == 0 else "失败，见上方日志"))
        if code == 0:
            self.set_status("向量库重建成功，重启服务器…")
            threading.Thread(target=self._restart_after_upload, daemon=True).start()
        else:
            # 失败分支不恢复上传按钮：收件箱源文件已归档到 _已处理/，重传会 FileNotFoundError
            self.upload_btn.state(["disabled"])
            self._append_log("⚠️ 语料已落盘，但向量库未更新。请手动运行：python run_pipeline.py 重建，或调整清单后重启编辑器重新上传")
            self.set_status("重建失败，请手动运行 run_pipeline.py")

    def _build_kb_tab(self):
        top = ttk.Frame(self.kb_tab)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.kb_search_entry = ttk.Entry(top)
        self.kb_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.kb_search_entry.bind("<Return>", lambda e: self.do_kb_search())
        ttk.Button(top, text="检索", command=self.do_kb_search).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="🗑 标记删除", command=self.on_kb_delete).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(top, text="🔄 刷新", command=self.refresh_kb_tree).pack(side=tk.LEFT, padx=(6, 0))

        paned = ttk.Panedwindow(self.kb_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(paned); paned.add(left, weight=2)
        self.kb_tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.kb_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.kb_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.kb_tree.configure(yscrollcommand=sb.set)
        self.kb_tree.bind("<<TreeviewSelect>>", lambda e: self._kb_preview())

        right = ttk.Frame(paned); paned.add(right, weight=3)
        self.kb_preview_text = tk.Text(right, wrap="word", state=tk.DISABLED)
        self.kb_preview_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.refresh_kb_tree()

    def refresh_kb_tree(self):
        self.kb_tree.delete(*self.kb_tree.get_children())
        data = list_kb_files()
        deleted_names = {it["name"] for it in self.kb_delete_items}
        for key, label in (("framework", "🧠 框架层 knowledge/framework/（重启服务生效）"),
                           ("corpus", "📖 语料库 data/txt/知识扩展/（重建向量库生效）")):
            parent = self.kb_tree.insert("", "end", text=label, open=True)
            for item in data[key]:
                flag = "🔒 " if item["readonly"] else ""
                mark = "🚫 " if item["name"] in deleted_names else ""
                size_kb = item["size"] / 1024
                size_txt = f"{size_kb:.0f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                self.kb_tree.insert(parent, "end", text=f"{flag}{mark}{item['name']} ({size_txt})",
                                    values=(key, item["name"], item["readonly"]))

    def _kb_selected(self):
        sel = self.kb_tree.selection()
        if not sel:
            return None
        vals = self.kb_tree.item(sel[0], "values")
        if not vals:
            return None
        return {"ftype": vals[0], "name": vals[1], "readonly": vals[2] in (True, "True")}

    def _kb_path(self, ftype: str, name: str) -> Path:
        return (MD_DIR if ftype == "framework" else TXT_DIR) / name

    def _kb_preview(self):
        sel = self._kb_selected()
        self.kb_preview_text.configure(state=tk.NORMAL)
        self.kb_preview_text.delete("1.0", tk.END)
        if not sel:
            self.kb_preview_text.configure(state=tk.DISABLED)
            return
        try:
            text = preview_file(self._kb_path(sel["ftype"], sel["name"]))
            self.kb_preview_text.insert("1.0", text)
        except Exception as e:
            self.kb_preview_text.insert("1.0", f"无法读取：{e}")
        self.kb_preview_text.configure(state=tk.DISABLED)

    def do_kb_search(self):
        query = self.kb_search_entry.get().strip()
        results = search_files(query)
        if not results:
            self.set_status(f"“{query}” 无命中")
            return
        lines = [f"{'🧠' if k=='framework' else '📖'} {n}（{h}处）" for k, n, h in results]
        self.set_status(f"命中 {len(results)} 个文件（双击条目在下方预览）")
        # 定位第一个命中并预览
        k, n, _ = results[0]
        self._show_kb_file(k, n)
        self.kb_search_entry.delete(0, tk.END)

    def _show_kb_file(self, ftype: str, name: str):
        # 在树中展开并选中对应节点
        for parent in self.kb_tree.get_children():
            for child in self.kb_tree.get_children(parent):
                if self.kb_tree.item(child, "values")[1] == name and \
                   self.kb_tree.item(child, "values")[0] == ftype:
                    self.kb_tree.selection_set(child)
                    self.kb_tree.see(child)
                    self._kb_preview()
                    return

    def on_kb_delete(self):
        sel = self._kb_selected()
        if not sel:
            self.set_status("请先在知识库树中选中一个文件")
            return
        if sel["readonly"]:
            messagebox.showwarning("只读文件", f"🔒 {sel['name']} 为卷本/大文件，不可删除", parent=self)
            return
        existing = [it for it in self.kb_delete_items if it["name"] == sel["name"] and it["ftype"] == sel["ftype"]]
        if existing:
            self.kb_delete_items.remove(existing[0])
            self.set_status(f"已取消标记删除：{sel['name']}")
        else:
            self.kb_delete_items.append(sel)
            self.set_status(f"已标记删除：{sel['name']}（进入步骤③本次更改清单）")
        self.refresh_kb_tree()


if __name__ == "__main__":
    app = App()
    app.mainloop()
