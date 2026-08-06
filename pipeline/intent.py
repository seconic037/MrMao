# -*- coding: utf-8 -*-
"""意图判断器：规则粗判，输出双轴标签（情绪轴 + 需求轴，带隶属度）。
理论依据：Russell(1980) 情绪效价；Searle(1969) 言语行为；House(1981) 社会支持；Rosch(1975) 原型隶属度。
"""

EMOTION_WORDS_NEG = [
    "累", "压力", "焦虑", "难过", "烦", "失败", "不行", "没用", "差", "痛苦",
    "迷茫", "绝望", "难受", "委屈", "孤独", "害怕", "担心", "生气", "郁闷", "崩溃",
    "煎熬", "受挫", "失落", "糟糕", "吃力", "撑不住", "坚持不住", "好难", "太难",
]
EMOTION_WORDS_POS = [
    "开心", "高兴", "太好了", "棒", "成功", "厉害", "满意", "幸福", "激动",
    "感谢", "感谢你", "喜欢", "进步", "突破", "顺利", "好运", "欣慰",
]
NEED_SIGNALS = {
    "info": ["怎么办", "如何", "为什么", "该不该", "能不能", "怎么", "什么意思", "有什么办法"],
    "affection": ["好累", "压力大", "好难", "做不到", "是不是我不行", "没用", "撑不住", "安慰", "好烦"],
    "action": ["帮我", "帮我个忙", "请你", "拜托", "替我"],
}


def _count_hits(text: str, words: list) -> int:
    return sum(1 for w in words if w in text)


def analyze_intent(text: str, prev_emotion: str = "neutral") -> dict:
    """粗判一句话的情绪与需求。prev_emotion 供前文衰减融合（预留）。"""
    neg = _count_hits(text, EMOTION_WORDS_NEG)
    pos = _count_hits(text, EMOTION_WORDS_POS)
    if neg > pos:
        emotion = "negative"
    elif pos > neg:
        emotion = "positive"
    else:
        emotion = "neutral"

    needs = {"info": 0.0, "affection": 0.0, "action": 0.0}
    for key, signals in NEED_SIGNALS.items():
        hits = _count_hits(text, signals)
        if hits:
            needs[key] = min(0.4 + 0.2 * hits, 1.0)
    # 负面情绪天然提升"要情感"隶属度
    if emotion == "negative":
        needs["affection"] = max(needs["affection"], 0.4)
    # 无任何信号 → 视为闲聊（无需求）
    if all(v == 0.0 for v in needs.values()):
        needs["affection"] = 0.1
    return {"emotion": emotion, "needs": needs}
