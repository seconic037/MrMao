# -*- coding: utf-8 -*-
"""S5 长期记忆持久化测试：_meta 快照写入 + 恢复。"""
import json, os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))


def _build_meta(raw_buffer, memories, topic_thread):
    """构造 _meta 快照条目（与 web/app.py 写入格式一致）。"""
    return {
        "role": "_meta", "type": "memory_snapshot",
        "ts": "2026-08-06T00:00:00",
        "data": {
            "raw_buffer": raw_buffer,
            "memories": memories,
            "topic_thread": topic_thread,
            "session_id": "test-session",
        },
    }


def _extract_snapshot(entries):
    """从日志条目列表提取最后一条 memory_snapshot 的 data。"""
    for e in reversed(entries):
        if e.get("role") == "_meta" and e.get("type") == "memory_snapshot":
            return e["data"]
    return None


def _recover(entries):
    """模拟 web/app.py 的恢复逻辑：优先 _meta，无则退回重建。"""
    snap = _extract_snapshot(entries)
    if snap:
        return {
            "raw_buffer": snap.get("raw_buffer", []),
            "memories": snap.get("memories", []),
            "topic_thread": snap.get("topic_thread", []),
        }
    # 退回逻辑（现有 _restore_session 重建）
    memories = []
    for e in entries:
        if e.get("role") == "user":
            memories.append({"question": e.get("content", "")[:60], "summary": ""})
        elif e.get("role") == "chairman" and memories:
            memories[-1]["summary"] = e.get("content", "")[:80]
    return {"raw_buffer": [], "memories": [m for m in memories if m.get("summary")][-5:], "topic_thread": []}


class TestSessionRestore(unittest.TestCase):
    def test_meta_roundtrip(self):
        """写 _meta → 恢复 → 三层结构正确。"""
        entries = [
            {"role": "user", "content": "我最近工作压力很大"},
            {"role": "chairman", "content": "压力大，先说说具体什么事"},
            _build_meta(
                raw_buffer=[{"question": "我最近工作压力很大", "answer": "压力大，先说说具体什么事"}],
                memories=[{"question": "我最近工作压力很大", "summary": "工作压力大", "emotion": "negative"}],
                topic_thread=[{"topic": "工作压力", "brief": "我最近工作压力很大", "round": 1}],
            ),
        ]
        r = _recover(entries)
        self.assertEqual(len(r["raw_buffer"]), 1)
        self.assertEqual(r["raw_buffer"][0]["question"], "我最近工作压力很大")
        self.assertEqual(r["memories"][0]["emotion"], "negative")  # emotion 保留
        self.assertEqual(r["topic_thread"][0]["topic"], "工作压力")

    def test_no_meta_fallback(self):
        """旧日志无 _meta → 退回重建逻辑（兼容现状）。"""
        entries = [
            {"role": "user", "content": "你好"},
            {"role": "chairman", "content": "你好，坐下聊聊"},
        ]
        r = _recover(entries)
        self.assertEqual(r["raw_buffer"], [])  # 旧逻辑不恢复 raw_buffer
        self.assertEqual(len(r["memories"]), 1)
        self.assertEqual(r["topic_thread"], [])

    def test_snapshot_is_last_meta(self):
        """多轮后取最后一条 snapshot（而非第一条）。"""
        entries = [
            _build_meta([], [], []),  # 第一轮
            _build_meta(
                raw_buffer=[{"question": "q2", "answer": "a2"}],
                memories=[{"question": "q2", "summary": "s2", "emotion": "neutral"}],
                topic_thread=[{"topic": "t2", "brief": "b2", "round": 2}],
            ),  # 第二轮
        ]
        snap = _extract_snapshot(entries)
        self.assertEqual(snap["topic_thread"][0]["topic"], "t2")

    def test_meta_not_mistaken_for_dialog(self):
        """_meta 条目不应被当成对话内容（role 检查）。"""
        entries = [
            {"role": "user", "content": "你好"},
            _build_meta([], [], []),
        ]
        dialog = [e for e in entries if e.get("role") in ("user", "chairman")]
        self.assertEqual(len(dialog), 1)
        self.assertEqual(dialog[0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
