"""毛式推理引擎：加载 knowledge/framework/ 下全部 MD → 注入 think prompt。"""
import os, glob
from jinja2 import Environment, FileSystemLoader


class MaoReasoningEngine:
    def __init__(self, framework_dir="knowledge/framework", prompt_dir="reasoning/prompts"):
        self.framework_dir = framework_dir
        self._knowledge_base = self._load_knowledge()
        self._jinja_env = Environment(loader=FileSystemLoader(prompt_dir), trim_blocks=True, lstrip_blocks=True)

    def _load_knowledge(self):
        """读取 knowledge/framework/ 下所有 MD 文件合并为知识库。"""
        md_files = sorted(glob.glob(f"{self.framework_dir}/*.md"))
        parts = []
        for f in md_files:
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
            if len(content) > 100:
                parts.append(content)
        if parts:
            return "\n\n---\n\n".join(parts)
        return self._default_knowledge()

    def _default_knowledge(self):
        return """## 毛选通用方法论
### 核心框架
辩证唯物主义：一切从实际出发。矛盾分析法：抓住主要矛盾和矛盾主要方面。
### 基本原则
实事求是、群众路线、独立自主、为人民服务。
### 工作方法
调查研究（没有调查就没有发言权）、总结经验、集中兵力。
### 反面模式
本本主义、经验主义、主观主义、教条主义。"""

    def build_prompt(self, question, rag_results=None, chat_history=None):
        template_name = "qa_with_reasoning.jinja2" if rag_results else "pure_reasoning.jinja2"
        return self._jinja_env.get_template(template_name).render(
            question=question, knowledge_base=self._knowledge_base,
            rag_results=rag_results or [], chat_history=chat_history or []
        )

    def build_think_prompt(self, question, rags, memories, **extra):
        """extra: topic_line, raw_recent, intent 等可选上下文。"""
        # backlog S8 None 防御：rags/memories/raw_recent 可能为 None
        rags = rags or []
        memories = [m for m in (memories or []) if isinstance(m, dict)]
        extra.setdefault("raw_recent", [])
        extra.setdefault("topic_line", "")
        extra.setdefault("intent", {})
        if "knowledge_base" not in extra:
            extra["knowledge_base"] = self._knowledge_base
        return self._jinja_env.get_template("think.jinja2").render(
            question=question, rag_results=rags, memories=memories, **extra
        )

    def build_speak_prompt(self, question, thinking_result, scene_context=None):
        return self._jinja_env.get_template("speak.jinja2").render(
            question=question,
            thinking_result=thinking_result,
            scene=scene_context or {},
        )
