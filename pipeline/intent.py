# -*- coding: utf-8 -*-
"""意图判断器：规则粗判，输出双轴标签（情绪轴 + 需求轴，带隶属度）。
理论依据：Russell(1980) 情绪效价；Searle(1969) 言语行为；House(1981) 社会支持；Rosch(1975) 原型隶属度。
"""

EMOTION_WORDS_NEG = [
    "累", "压力", "焦虑", "难过", "烦", "失败", "不行", "没用", "差", "痛苦",
    "迷茫", "绝望", "难受", "委屈", "孤独", "害怕", "担心", "生气", "郁闷", "崩溃",
    "煎熬", "受挫", "失落", "糟糕", "吃力", "撑不住", "坚持不住", "好难", "太难",
]
# 子串误报例外：某情绪词前紧贴这些字时不命中（如"麻烦"里的"烦"不是负面情绪）。
# backlog S8：修复 substring 误报["麻烦"含"烦"]。
EXCEPT_PREFIX = {"烦": ("麻",)}
EMOTION_WORDS_POS = [
    "开心", "高兴", "太好了", "棒", "成功", "厉害", "满意", "幸福", "激动",
    "感谢", "感谢你", "喜欢", "进步", "突破", "顺利", "好运", "欣慰",
]
# 否定词集合：单字或双字，须紧贴被否定的词（如"不高兴"里的"不"）；
# "不知如何"中"不"与"如何"隔"知"，不构成紧贴否定，故不误杀。
NEG_PREFIXES = ("不", "没", "别", "无", "勿", "莫",
                "不是", "没有", "不会", "不能", "别是")
NEED_SIGNALS = {
    "info": ["怎么办", "如何", "为什么", "该不该", "能不能", "怎么", "什么意思", "有什么办法"],
    "affection": ["好累", "压力大", "好难", "做不到", "是不是我不行", "没用", "撑不住", "安慰", "好烦",
                  "不知道怎么办", "不知道该怎么做", "不知道怎么做"],
    "action": ["帮我", "帮我个忙", "请你", "拜托", "替我"],
    # 试探/反问信号：命中即输出 kind="test"（直接表态，别绕弯子）
    "test": ["你觉得呢", "你说呢", "您觉得", "您怎么看", "你怎么看", "你琢磨呢", "你以为呢"],
    # 求认可信号：命中即输出 kind="approval"（"对不对"等自问词不必带问号）
    "approval": ["对不对", "对吗", "行吗", "这样想", "是不是我", "你看行不行", "我这样"],
}

# ── 场景标签信号（服务手册 v4 第 7~11 层，典型信号铺开版）──
SCENE_SIGNALS = {
    "conflict": ["我不同意", "你说得不对", "你错了", "但是", "可是", "恰恰相反", "不见得",
                 "未必", "不敢苟同", "你这么说不对", "道理不是这样", "我看未必", "这不对吧",
                 "你太绝对了", "不能这么说", "你说的不对"],
    "humor_offer": ["逗您玩", "开玩笑", "调侃", "您老", "老顽固", "哈哈", "嘻嘻", "您也会错",
                    "逮着您了", "您也有不会的"],
    "refuse_request": ["帮我骂", "替我出气", "帮我教训", "帮我整", "帮我写", "替我编", "帮我查",
                       "帮我删", "帮我转账", "帮我撒谎", "帮我瞒", "帮我骗", "帮我打"],
    "silence": ["嗯嗯", "哦哦", "是哦", "好的", "知道了", "嗯", "哦", "行", "。。", "…", "哈"],
    "outburst": ["崩溃", "气死了", "大哭", "受不了", "凭什么", "太欺负人", "我不行了", "绝望了",
                 "杀了我吧", "呜呜呜", "啊啊啊", "活不下去", "想死"],
}

# ── 激活情境信号（服务性格层 10 特质）──
SITUATION_SIGNALS = {
    "空谈": ["道理我都懂", "理论上", "原则上", "说白了", "本质", "宏观", "战略上", "说起来",
            "空谈", "纸上谈兵", "大道理"],
    "纠结细节": ["但是细节", "具体到", "然而", "可问题是", "这个细节", "那一步", "那个环节",
                "具体怎么", "细节上"],
    "迷茫求方向": ["我该往哪走", "选哪个", "不知道怎么办", "方向", "出路", "接下来", "以后怎么办",
                  "怎么选择", "何去何从"],
    "越线": ["你不对", "你的路线错了", "你那套过时了", "你当年", "批评你", "你错了", "你这是",
             "你怎么能", "你太过分了"],
    "传道授业": ["您讲讲", "这道理", "怎么理解", "解释一下", "为什么这么说", "说给我听", "教教我",
                 "您给讲讲", "请教"],
    "悲观": ["没希望", "完了", "白干了", "到头来", "有什么用", "没意思", "算了吧", "认命了",
             "就这样吧", "放弃吧"],
}

# 唤醒度（S6 四象限）：负面高唤醒词（outburst 用）
HIGH_AROUSAL_NEG = ["崩溃", "气死了", "大哭", "受不了", "绝望", "活不下去", "想死", "凭什么",
                    "太欺负人", "杀了我吧"]
# 负面低唤醒词（消沉/疲惫）
LOW_AROUSAL_NEG = ["累了", "疲惫", "无奈", "没劲", "算了", "就这样", "没意思", "躺平", "好累",
                   "撑不住"]
# 正面高唤醒词（兴奋/激动）
HIGH_AROUSAL_POS = ["太棒了", "太好了", "激动", "兴奋", "厉害", "绝了", "爽", "成功啦"]


def _has_neg_prefix(text: str, idx: int) -> bool:
    """词前紧贴否定词（向前取 1~3 个字符，否定词须以紧邻字符为结尾）则返回 True。"""
    for dist in (1, 2, 3):
        if idx - dist < 0:
            break
        if text[idx - dist: idx] in NEG_PREFIXES:
            return True
    return False


def _count_hits(text: str, words: list) -> int:
    """统计命中数；某词前紧邻否定词或例外前缀时该次出现不算命中。"""
    hits = 0
    for w in words:
        start = 0
        while True:
            idx = text.find(w, start)
            if idx < 0:
                break
            if not _has_neg_prefix(text, idx) and not _has_except_prefix(text, idx, w):
                hits += 1
            start = idx + 1
    return hits


def _has_except_prefix(text: str, idx: int, word: str) -> bool:
    """词前紧贴例外字（EXCEPT_PREFIX）则返回 True，用于修复子串误报。"""
    excepts = EXCEPT_PREFIX.get(word)
    if not excepts:
        return False
    for e in excepts:
        if idx >= 1 and text[idx - 1] == e:
            return True
    return False


def _scene_membership(text: str, scene_signals: dict) -> dict:
    """计算各场景标签隶属度：命中数 → min(0.5 + 0.3*hits, 1.0)。"""
    out = {}
    for tag, words in scene_signals.items():
        hits = _count_hits(text, words)
        out[tag] = min(0.5 + 0.3 * hits, 1.0) if hits else 0.0
    return out


def _situation_membership(text: str, situation_signals: dict) -> dict:
    """计算各激活情境隶属度。闲聊/轻松为兜底（由调用方按情绪补）。"""
    out = {}
    for tag, words in situation_signals.items():
        hits = _count_hits(text, words)
        out[tag] = min(0.5 + 0.3 * hits, 1.0) if hits else 0.0
    return out


def _detect_arousal(text: str, emotion: str) -> str:
    """唤醒度判定（S6 四象限）：感叹号/强度词/重复字。"""
    exclaims = text.count("！") + text.count("!")
    repeat = any(c * 3 in text for c in "啊啊呜呜哈哈嘿嘿")
    if emotion == "negative":
        if _count_hits(text, HIGH_AROUSAL_NEG) or exclaims >= 2 or repeat:
            return "high"
        if _count_hits(text, LOW_AROUSAL_NEG):
            return "low"
    elif emotion == "positive":
        if _count_hits(text, HIGH_AROUSAL_POS) or exclaims >= 1:
            return "high"
        return "low"
    return "neutral"


def _classify_kind(text: str, emotion: str, needs: dict, test_hits: int, approval_hits: int):
    """把本轮定性成一个策略标签（test/approval/comfort/retreat/info），供 think 策略映射使用。"""
    if test_hits:
        return "test"
    if approval_hits:
        return "approval"
    if emotion == "negative":
        # 求安慰：负面且情感需求压过信息需求
        if needs["affection"] >= needs["info"] and needs["affection"] > 0.4:
            return "comfort"
        # 拒绝退缩：负面且没有强行动请求
        if needs["action"] < 0.3:
            return "retreat"
    if needs["info"] > 0.5:
        return "info"
    return None


def analyze_intent(text: str) -> dict:
    """粗判一句话的情绪与需求。"""
    neg = _count_hits(text, EMOTION_WORDS_NEG)
    pos = _count_hits(text, EMOTION_WORDS_POS)
    if neg > pos:
        emotion = "negative"
    elif pos > neg:
        emotion = "positive"
    else:
        emotion = "neutral"

    needs = {"info": 0.0, "affection": 0.0, "action": 0.0}
    test_hits = _count_hits(text, NEED_SIGNALS["test"])
    approval_hits = _count_hits(text, NEED_SIGNALS["approval"])
    # 隶属度公式（backlog S8 补注释）：基础 0.4 + 每命中一个信号词 +0.2，封顶 1.0。
    # 0.4 保证单命中即过 0.3 的"弱命中"线；0.2 为单信号词的边际增量；封顶防多词叠加溢出。
    for key in ("info", "affection", "action"):
        hits = _count_hits(text, NEED_SIGNALS[key])
        if hits:
            needs[key] = min(0.4 + 0.2 * hits, 1.0)
    # 负面情绪天然提升"要情感"隶属度：垫底 0.45 > comfort 阈值 0.4，
    # 纯负面句（无 affection 信号词）也能落入求安慰而非拒绝退缩。
    if emotion == "negative":
        needs["affection"] = max(needs["affection"], 0.45)
    # 无任何信号 → 视为闲聊（无需求）：0.1 只是占位防全零，不足以触发任何策略。
    if all(v == 0.0 for v in needs.values()):
        needs["affection"] = 0.1
    kind = _classify_kind(text, emotion, needs, test_hits, approval_hits)
    scenes = _scene_membership(text, SCENE_SIGNALS)
    situations = _situation_membership(text, SITUATION_SIGNALS)
    # 轻松情境：情绪非负面且无其他情境命中时兜底 0.6
    if emotion != "negative" and not any(v > 0 for v in situations.values()):
        situations["轻松"] = 0.6
    # 唤醒度（S6 四象限）
    arousal = _detect_arousal(text, emotion)
    # C1 情绪门控（手册 8.4 + 跨层优先级总则）：情绪负面时幽默/轻松情境归零
    if emotion == "negative":
        scenes["humor_offer"] = 0.0
        situations["轻松"] = 0.0
    return {"emotion": emotion, "needs": needs, "kind": kind,
            "arousal": arousal, "scenes": scenes, "situations": situations}
