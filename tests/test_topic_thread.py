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

if __name__ == "__main__":
    unittest.main()
