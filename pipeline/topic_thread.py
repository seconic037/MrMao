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
        return 1.0  # 两集皆空视为同一话题
    if not a or not b:
        return 0.0  # 单侧为空（含 a|b 为空但 a==b 已在上分支排除）
    return len(a & b) / len(a | b)


class TopicThread:
    def __init__(self):
        self._nodes = []  # [{topic, brief, round}]
        self._round = 0

    def update(self, question: str) -> None:
        # 空输入防护（backlog S8）：空白消息不产生节点、不推进轮次
        if not question or not question.strip():
            return
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
        # 深拷贝（backlog S8）：防外部通过返回列表篡改内部节点
        return [dict(n) for n in self._nodes]

    def restore(self, nodes: list) -> None:
        """从持久化快照恢复节点（S5 长期记忆）。"""
        self._nodes = [dict(n) for n in (nodes or [])]
        self._round = max((n.get("round", 0) for n in self._nodes), default=0)

    def summary(self) -> str:
        if not self._nodes:
            return ""
        if len(self._nodes) == 1:
            return f"你们在聊「{self._nodes[0]['topic']}」"
        first, last = self._nodes[0], self._nodes[-1]
        middle = self._nodes[1:-1]
        # 中间节点去重 + 避免首尾重复（backlog S8：summary 文案"中间还提到"重复）
        seen, mids = set(), []
        for n in middle:
            tp = n["topic"]
            if tp and tp not in seen and tp not in (first["topic"], last["topic"]):
                seen.add(tp)
                mids.append(tp)
        if not mids:
            return f"从「{first['topic']}」聊到「{last['topic']}」"
        return f"从「{first['topic']}」聊到「{last['topic']}」，中间还提到：{'、'.join(mids)}"
