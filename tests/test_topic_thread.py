import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from topic_thread import TopicThread

class TestTopicThread(unittest.TestCase):
    def test_same_topic_updates_not_appends(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("工作压力还是很大，怎么办")
        self.assertEqual(len(t.nodes()), 1)
    def test_new_topic_appends(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("咱们聊聊历史吧")
        self.assertGreaterEqual(len(t.nodes()), 2)
    def test_summary_nonempty(self):
        t = TopicThread()
        t.update("我最近工作压力很大")
        t.update("咱们聊聊历史吧")
        self.assertTrue(len(t.summary()) > 5)
    # ── backlog S8 新增 ──
    def test_empty_input_no_node(self):
        """S8：空输入不产生节点、不推进轮次。"""
        t = TopicThread()
        t.update("")
        t.update("   ")
        self.assertEqual(len(t.nodes()), 0)
        self.assertEqual(t.summary(), "")
    def test_nodes_deep_copy(self):
        """S8：nodes() 返回深拷贝，外部修改不污染内部。"""
        t = TopicThread()
        t.update("工作压力很大")
        nodes = t.nodes()
        nodes[0]["topic"] = "被篡改"
        self.assertEqual(t.nodes()[0]["topic"], "工作压力很大")
    def test_summary_no_middle_duplicate(self):
        """S8：summary 的'中间还提到'不含首尾重复。"""
        t = TopicThread()
        t.update("工作压力")
        t.update("聊聊历史")
        t.update("说说诗词")
        s = t.summary()
        self.assertTrue(s.startswith("从「工作压力」聊到「说说诗词」"))
        middle_part = s.split("中间还提到：", 1)[1]
        self.assertNotIn("工作压力", middle_part)  # 首节点不应在"中间"里
        self.assertNotIn("说说诗词", middle_part)  # 尾节点不应在"中间"里
        self.assertIn("历史", middle_part)
    def test_jaccard_single_empty_side(self):
        """S8：_jaccard 单侧为空分支——空集 vs 非空应 0（不为 1 误判同话题）。"""
        from topic_thread import _jaccard
        self.assertEqual(_jaccard(set(), {"a"}), 0.0)
        self.assertEqual(_jaccard({"a"}, set()), 0.0)
        self.assertEqual(_jaccard(set(), set()), 1.0)

if __name__ == "__main__":
    unittest.main()
