import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from intent import analyze_intent

class TestIntent(unittest.TestCase):
    def test_negative_emotion(self):
        r = analyze_intent("我压力大，好累")
        self.assertEqual(r["emotion"], "negative")
    def test_positive_emotion(self):
        r = analyze_intent("太好了，我做到了")
        self.assertEqual(r["emotion"], "positive")
    def test_neutral_default(self):
        r = analyze_intent("今天天气不错")
        self.assertEqual(r["emotion"], "neutral")
    def test_info_need(self):
        r = analyze_intent("我该怎么办？")
        self.assertGreater(r["needs"]["info"], 0.5)
    def test_affection_need(self):
        r = analyze_intent("我压力大，你说我该怎么办")
        self.assertGreater(r["needs"]["affection"], 0.3)
        self.assertGreater(r["needs"]["info"], 0.3)
    def test_action_need(self):
        r = analyze_intent("帮我个忙")
        self.assertGreater(r["needs"]["action"], 0.3)

if __name__ == "__main__":
    unittest.main()
