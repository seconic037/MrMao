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
    # ── 全分支评审新增（I-1/I-2/I-4）──
    def test_negated_positive_not_positive(self):
        """I-1：否定情绪——"我不开心/我不高兴"不能判成 positive。"""
        for s in ("我不开心", "我不高兴"):
            r = analyze_intent(s)
            self.assertNotEqual(r["emotion"], "positive", f"{s} 不应判为 positive")
    def test_positive_still_hits_without_negation(self):
        """I-1：无否定前缀时正向词照常命中（防过杀）。"""
        r = analyze_intent("我今天挺高兴的")
        self.assertEqual(r["emotion"], "positive")
    def test_probe_question_kind(self):
        """I-2：反问试探——"您怎么看？" 应输出 kind=test（或 info 高）。"""
        r = analyze_intent("您怎么看？")
        self.assertTrue(r["kind"] == "test" or r["needs"]["info"] > 0.5, f"got kind={r['kind']}, info={r['needs']['info']}")
        r2 = analyze_intent("你觉得呢")
        self.assertEqual(r2["kind"], "test")
    def test_approval_kind(self):
        """I-4：求认可——"我这样想对吗？" 应输出 kind=approval（或 affection 高）。"""
        r = analyze_intent("我这样想对吗？")
        self.assertTrue(r["kind"] == "approval" or r["needs"]["affection"] > 0.3, f"got kind={r['kind']}")
    def test_unknown_way_info_plus_affection(self):
        """I-4：'我不知道怎么办' 应既给 info 又给 affection（信息+情感双高）。"""
        r = analyze_intent("我不知道怎么办")
        self.assertGreater(r["needs"]["info"], 0.3)
        self.assertGreater(r["needs"]["affection"], 0.3)
    def test_comfort_kind_on_negative(self):
        """I-5 支撑：负面+高情感 → kind=comfort。"""
        r = analyze_intent("我压力大，好累")
        self.assertEqual(r["kind"], "comfort")
    # ── 二轮复评审新增（N1/N2/N5）──
    def test_pure_negative_comfort(self):
        """N1：纯负面句（无 affection 信号词）应落 comfort，而非 retreat。"""
        for s in ("我很焦虑", "我很烦", "我很痛苦"):
            r = analyze_intent(s)
            self.assertEqual(r["kind"], "comfort", f"{s} 应判 comfort，got kind={r['kind']}")
    def test_distant_negation_not_filtering_info(self):
        """N2：'我不知如何是好' 中'如何'前隔'知'，不算否定，info 应命中。"""
        r = analyze_intent("我不知如何是好")
        self.assertGreater(r["needs"]["info"], 0)
        self.assertEqual(r["kind"], "info")
    def test_approval_without_question_mark(self):
        """N5：'对不对' 自问词无问号也应判 approval。"""
        r = analyze_intent("你说我这样做对不对")
        self.assertEqual(r["kind"], "approval")
    # ── backlog S8 新增 ──
    def test_mafan_not_negative(self):
        """S8：substring 误报——'麻烦'里的'烦'不是负面情绪。"""
        r = analyze_intent("麻烦你帮我拿一下")
        self.assertNotEqual(r["emotion"], "negative")
    def test_fan_still_negative(self):
        """S8：反例——真正的'烦'仍应判负面（防过杀）。"""
        r = analyze_intent("我真烦")
        self.assertEqual(r["emotion"], "negative")
    def test_emotion_tie_goes_neutral(self):
        """S8：平局分支——正负情绪词同数时应中性（neg==pos → neutral）。"""
        r = analyze_intent("又开心又烦")
        self.assertEqual(r["emotion"], "neutral")
    def test_need_cap_at_one(self):
        """S8：封顶分支——多信号词叠加后隶属度不超 1.0。"""
        r = analyze_intent("怎么办怎么办怎么办怎么办怎么办怎么办")
        self.assertLessEqual(r["needs"]["info"], 1.0)
    def test_empty_input_returns_defaults(self):
        """S8：空输入防护——不抛异常，返回中性+无需求。"""
        for s in ("", "   "):
            r = analyze_intent(s)
            self.assertEqual(r["emotion"], "neutral")

if __name__ == "__main__":
    unittest.main()
