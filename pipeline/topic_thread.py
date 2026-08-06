# -*- coding: utf-8 -*-
"""话题主线：检测话题切换，维护话题节点序列，提供整体话题线。
理论依据：Zacks & Tversky(2001) 事件分割——人按"事件边界"记忆连续经验。
"""

import jieba

SIM_THRESHOLD = 0.15  # Jaccard 相似度低于此值视为切换话题


def _keywords(text: str) -> set:
    words = jieba.lcut(text)
    # 去掉单字与停用词
    stops = {"我", "你", "他", "的", "了", "吗", "呢", "啊", "是", "在", "有", "也", "就", "都"}
    return {w for w in words if len(w) > 1 and w not in stops}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


class TopicThread:
    def __init__(self):
        self._nodes = []  # [{topic, brief, round}]
        self._round = 0

    def update(self, question: str) -> None:
        self._round += 1
        kws = _keywords(question)
        if not self._nodes:
            self._nodes.append({"topic": question[:20], "brief": question[:30], "round": self._round})
            return
        last = self._nodes[-1]
        last_kws = _keywords(last["topic"]) | _keywords(last["brief"])
        sim = _jaccard(kws, last_kws)
        if sim >= SIM_THRESHOLD:
            last["brief"] = question[:30]  # 同话题，更新简述
        else:
            self._nodes.append({"topic": question[:20], "brief": question[:30], "round": self._round})

    def nodes(self) -> list:
        return list(self._nodes)

    def summary(self) -> str:
        if not self._nodes:
            return ""
        if len(self._nodes) == 1:
            return f"你们在聊「{self._nodes[0]['topic']}」"
        topics = "、".join(n["topic"] for n in self._nodes)
        return f"从「{self._nodes[0]['topic']}」聊到「{self._nodes[-1]['topic']}」，中间还提到：{topics}"
