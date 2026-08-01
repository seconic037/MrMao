# tests/test_kb_ops.py
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import kb_editor as kb

class TestClassify(unittest.TestCase):
    def test_md_topic_hit(self):
        self.assertEqual(kb.classify_md("经济学原理_Fetter_BTS.md"), "经济学.md")
        self.assertEqual(kb.classify_md("哲学方法论.md"), "哲学.md")
    def test_md_default_keeps_name(self):
        self.assertEqual(kb.classify_md("未知主题XYZ.md"), "未知主题XYZ.md")
    def test_classify_file_by_ext(self):
        self.assertEqual(kb.classify_file(Path("a.txt")), "corpus")
        self.assertEqual(kb.classify_file(Path("b.md")), "framework")

class TestScan(unittest.TestCase):
    def test_scan_inbox_excludes_autogen_and_dirs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "01-哲学方法论.md").write_text("# x", encoding="utf-8")
            (root / "README.md").write_text("x", encoding="utf-8")
            (root / "NPC知识库情况.md").write_text("x", encoding="utf-8")
            (root / "_已处理").mkdir(); (root / "_已处理" / "old.md").write_text("x", encoding="utf-8")
            (root / "资料.txt").write_text("x", encoding="utf-8")
            items = kb.scan_inbox(root)
            names = [i["name"] for i in items]
            self.assertEqual(names, ["01-哲学方法论.md", "资料.txt"])
            self.assertEqual(items[0]["ftype"], "framework")
            self.assertEqual(items[1]["ftype"], "corpus")

class TestDedupe(unittest.TestCase):
    def test_same_stem_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / "md"; txt = root / "txt"
            md.mkdir(); txt.mkdir()
            (txt / "经济学原理_Marshall_ST.txt").write_text("内容A" * 100, encoding="utf-8")
            flag = kb.detect_duplicate("经济学原理_Marshall_BTS.md", "内容A" * 100, md, txt)
            self.assertEqual(flag, "同主干")
    def test_similar_content_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / "md"; txt = root / "txt"
            md.mkdir(); txt.mkdir()
            (txt / "别的名字.txt").write_text("同一个主题的第一段话。" * 50, encoding="utf-8")
            flag = kb.detect_duplicate("全新名字.txt", "同一个主题的第一段话。" * 50, md, txt)
            self.assertEqual(flag, "内容相似")
    def test_no_dup(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / "md"; txt = root / "txt"
            md.mkdir(); txt.mkdir()
            (txt / "完全无关.txt").write_text("A" * 300, encoding="utf-8")
            self.assertEqual(kb.detect_duplicate("新主题.txt", "B" * 300, md, txt), "")

class TestDedupeEdge(unittest.TestCase):
    def test_dup_on_empty_dirs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(kb.detect_duplicate("x.md", "内容", root, root), "")

class TestPreview(unittest.TestCase):
    def test_preview_reads_utf8(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "f.txt"; p.write_text("你好世界", encoding="utf-8")
            self.assertEqual(kb.preview_file(p), "你好世界")

class TestListAndSearch(unittest.TestCase):
    def test_is_readonly(self):
        self.assertTrue(kb.is_readonly("毛选第一卷_全文.txt", 100))
        self.assertTrue(kb.is_readonly("大.txt", 1024 * 1024 + 1))
        self.assertFalse(kb.is_readonly("小.txt", 1024))
    def test_count_hits(self):
        self.assertEqual(kb.count_hits("苹果\n香蕉苹果", "苹果"), 2)
    def test_list_kb_files_structure(self):
        data = kb.list_kb_files()
        self.assertIn("framework", data)
        self.assertIn("corpus", data)
        for item in data["framework"]:
            self.assertIn("name", item); self.assertIn("size", item); self.assertIn("readonly", item)
    def test_search_files_returns_sorted(self):
        results = kb.search_files("实事求是")
        self.assertIsInstance(results, list)
        if results:
            self.assertEqual(len(results[0]), 3)
    def test_search_empty_query(self):
        self.assertEqual(kb.search_files("  "), [])

class TestApplyChangelist(unittest.TestCase):
    def _root(self, td):
        root = Path(td)
        (root / "knowledge" / "framework").mkdir(parents=True)
        (root / "data" / "txt" / "知识扩展").mkdir(parents=True)
        (root / "新知识放这里").mkdir(parents=True)
        return root

    def test_md_new_and_merge_and_txt_copy_and_delete(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            # 已存在的框架主题文件（被合并目标）
            (root / "knowledge" / "framework" / "经济学.md").write_text("已有", encoding="utf-8")
            # 已有语料（被删除）
            (root / "data" / "txt" / "知识扩展" / "旧文件.txt").write_text("x", encoding="utf-8")
            # 收件箱新文件
            src_md = root / "新知识放这里" / "经济学原理_new.md"
            src_md.write_text("新增经济学内容", encoding="utf-8")
            src_txt = root / "新知识放这里" / "新语料.txt"
            src_txt.write_text("语料正文", encoding="utf-8")
            logs = kb.apply_changelist(
                [
                    {"src": src_md, "target": "framework", "merge_target": "经济学.md"},
                    {"src": src_txt, "target": "corpus", "merge_target": None},
                ],
                [{"ftype": "corpus", "name": "旧文件.txt"}],
                root,
            )
            merged = (root / "knowledge" / "framework" / "经济学.md").read_text(encoding="utf-8")
            self.assertIn("已有", merged); self.assertIn("新增经济学内容", merged)
            self.assertTrue((root / "data" / "txt" / "知识扩展" / "新语料.txt").exists())
            self.assertFalse((root / "data" / "txt" / "知识扩展" / "旧文件.txt").exists())
            self.assertTrue((root / "新知识放这里" / "_已删除" / "旧文件.txt").exists())
            # 原文件归档
            self.assertFalse(src_md.exists())
            self.assertTrue((root / "新知识放这里" / "_已处理" / "经济学原理_new.md").exists())

    def test_md_standalone_new(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            src = root / "新知识放这里" / "独立主题.md"
            src.write_text("内容", encoding="utf-8")
            kb.apply_changelist([{"src": src, "target": "framework", "merge_target": None}], [], root)
            self.assertTrue((root / "knowledge" / "framework" / "独立主题.md").exists())

    def test_readonly_delete_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            (root / "data" / "txt" / "知识扩展" / "大_全文.txt").write_text("x" * 2000000, encoding="utf-8")
            logs = kb.apply_changelist([], [{"ftype": "corpus", "name": "大_全文.txt"}], root)
            self.assertTrue(any("只读" in line for line in logs))
            self.assertTrue((root / "data" / "txt" / "知识扩展" / "大_全文.txt").exists())

    def test_rollback_on_second_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            src_ok = root / "新知识放这里" / "好文件.txt"
            src_ok.write_text("ok", encoding="utf-8")
            src_bad = root / "新知识放这里" / "坏文件.txt"
            src_bad.write_text("bad", encoding="utf-8")
            # merge_target 指向非法路径（含 ../）→ 应失败并触发回滚
            logs = kb.apply_changelist(
                [
                    {"src": src_ok, "target": "corpus", "merge_target": None},
                    {"src": src_bad, "target": "framework", "merge_target": "../escape.md"},
                ],
                [], root,
            )
            self.assertTrue(any("回滚" in line or "失败" in line for line in logs))
            self.assertFalse((root / "data" / "txt" / "知识扩展" / "好文件.txt").exists())

    def test_rollback_restores_merged_target(self):
        """C1 回归：merge 到已存在目标 + 后续失败 → 回滚写回原内容，而非 unlink 删掉原文件。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            (root / "knowledge" / "framework" / "经济学.md").write_text("已有", encoding="utf-8")
            src_ok = root / "新知识放这里" / "经济学原理_new.md"
            src_ok.write_text("新增经济学内容", encoding="utf-8")
            src_bad = root / "新知识放这里" / "坏文件.txt"
            src_bad.write_text("bad", encoding="utf-8")
            logs = kb.apply_changelist(
                [
                    {"src": src_ok, "target": "framework", "merge_target": "经济学.md"},
                    {"src": src_bad, "target": "framework", "merge_target": "../escape.md"},
                ],
                [], root,
            )
            self.assertTrue(any("回滚" in line or "失败" in line for line in logs))
            merged = root / "knowledge" / "framework" / "经济学.md"
            self.assertTrue(merged.exists())
            self.assertEqual(merged.read_text(encoding="utf-8"), "已有")

    def test_rollback_restores_archived_file(self):
        """C2 回归：归档第二阶段失败 → 回滚把已归档文件还原回收件箱，而非三处全失。"""
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            (root / "knowledge" / "framework" / "经济学.md").write_text("已有", encoding="utf-8")
            src1 = root / "新知识放这里" / "经济学原理_new.md"
            src1.write_text("新增经济学内容", encoding="utf-8")
            src2 = root / "新知识放这里" / "新语料.txt"
            src2.write_text("语料正文", encoding="utf-8")
            real_move = kb.shutil.move
            archived = {"count": 0}
            def _fake_move(s, d):
                if "_已处理" in str(d):
                    archived["count"] += 1
                    if archived["count"] > 1:
                        raise OSError("归档阶段第二个 move 失败")
                return real_move(str(s), str(d))
            with mock.patch.object(kb.shutil, "move", side_effect=_fake_move):
                logs = kb.apply_changelist(
                    [
                        {"src": src1, "target": "framework", "merge_target": "经济学.md"},
                        {"src": src2, "target": "corpus", "merge_target": None},
                    ],
                    [], root,
                )
            self.assertTrue(any("回滚" in line or "失败" in line for line in logs))
            # 第一个已归档文件必须还原回收件箱（而非被 unlink 三处全失）
            self.assertTrue((root / "新知识放这里" / "经济学原理_new.md").exists())
            # 顺带验证 merge 目标内容也被写回
            self.assertEqual((root / "knowledge" / "framework" / "经济学.md").read_text(encoding="utf-8"), "已有")

    def test_delete_rollback_restores(self):
        """I1 回归：delete 已执行 + 后续归档失败 → 回滚把软删除文件还原到原位置。"""
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            root = self._root(td)
            (root / "data" / "txt" / "知识扩展" / "旧文件.txt").write_text("x", encoding="utf-8")
            src = root / "新知识放这里" / "新文件.txt"
            src.write_text("y", encoding="utf-8")
            real_move = kb.shutil.move
            def _fake_move(s, d):
                if "_已处理" in str(d):
                    raise OSError("归档阶段失败")
                return real_move(str(s), str(d))
            with mock.patch.object(kb.shutil, "move", side_effect=_fake_move):
                logs = kb.apply_changelist(
                    [{"src": src, "target": "corpus", "merge_target": None}],
                    [{"ftype": "corpus", "name": "旧文件.txt"}],
                    root,
                )
            self.assertTrue(any("回滚" in line or "失败" in line for line in logs))
            self.assertTrue((root / "data" / "txt" / "知识扩展" / "旧文件.txt").exists())

class TestPidOnPort(unittest.TestCase):
    def test_pid_on_port_exact_match(self):
        from unittest import mock
        fake_out = (
            "  TCP    0.0.0.0:80001           0.0.0.0:0              LISTENING       99999\n"
            "  TCP    0.0.0.0:8000            0.0.0.0:0              LISTENING       12345\n"
        )
        proc = mock.Mock()
        proc.stdout = fake_out
        with mock.patch("kb_editor.subprocess.run", return_value=proc):
            self.assertEqual(kb._pid_on_port(8000), 12345)
            self.assertEqual(kb._pid_on_port(80001), 99999)

class TestServer(unittest.TestCase):
    def test_server_running_on_closed_port(self):
        # 挑一个几乎必然空闲的高端口
        import socket as _s
        with _s.socket() as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        self.assertFalse(kb.server_running(free_port))
    def test_server_running_true_on_open_port(self):
        import socket as _s, threading as _t
        srv = _s.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            self.assertTrue(kb.server_running(port))
        finally:
            srv.close()

class TestEntryPoint(unittest.TestCase):
    def test_main_entry_exists(self):
        """回归：双击 bat 直接运行 kb_editor.py 必须进入 mainloop（v2 曾丢失入口导致闪退）。"""
        src = Path(__file__).resolve().parent.parent / "tools" / "kb_editor.py"
        text = src.read_text(encoding="utf-8")
        self.assertIn('if __name__ == "__main__":', text)
        self.assertIn("app.mainloop()", text)

if __name__ == "__main__":
    unittest.main()
