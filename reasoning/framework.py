"""毛式推理引擎：加载 book-to-skill 知识库 + RAG 结果 → 生成分析 Prompt。"""
import os
from jinja2 import Environment, FileSystemLoader


class MaoReasoningEngine:
    def __init__(self, knowledge_path="knowledge/maozedong-knowledge-base.md", prompt_dir="reasoning/prompts"):
        self.knowledge_path = knowledge_path
        self._knowledge_base = self._load_knowledge()
        self._jinja_env = Environment(loader=FileSystemLoader(prompt_dir), trim_blocks=True, lstrip_blocks=True)

    def _load_knowledge(self):
        if os.path.exists(self.knowledge_path):
            with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > 200:
                return content
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
