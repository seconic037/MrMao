# Handoff: MrMao 全项目状态
> 2026-08-01 · 新对话续接

## 项目环境
- 路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · ChromaDB · DeepSeek API (`deepseek-v4-flash`)
- 前端: 原生 HTML/CSS/JS · 16 个极简 SVG 图标
- 启动: `python run_server.py` → `http://localhost:8000`
- 管道: `python run_pipeline.py`

## 当前数据
- 知识扩展: 76 TXT · 482 篇 · 6339 块
- 框架层: `knowledge/framework/` 00-core.md + 经济学.md
- 日志: `聊天记录/` 实时刷盘

## 功能模块

| 模块 | 文件 | 状态 |
|------|------|------|
| 基础对话 | speak/think.jinja2, framework.py | ✅ |
| 场景系统 | pipeline/scenes.py, game_engine.py | ✅ |
| 场景UI | 4场景WebP背景+遮罩+单标签居中 | ✅ |
| 场景开关 | 底部4TAB(首页/日志/场景/阅读) | ✅ |
| 考考你 | 弹窗出题 | ✅ |
| 日志面板 | 半屏弹出+两行预览+查看+继续聊 | ✅ |
| 热点 | 百度实时+娱乐过滤+🔄刷新 | ✅ |
| 知识库体系 | 新知识放这里/+ingest_knowledge.py | ✅ |
| SVG图标 | 16个极简描边SVG | ✅ |
| Windows服务 | tools/nssm/ + install_service.bat | ⚠️ 待测 |

## 活跃问题

- ✅ 日志"继续聊"返回空 — **已修复 (2026-08-02) + Chrome 实测通过**：根因是 `style.css` 无版本号 + `app.js` 版本号未随本轮改动更新 → 浏览器缓存旧版无参 `resumeFromLog`，历史列表 onclick 调用后 catch 静默失败返回空。已统一版本号；并补上占位消息 `loading` class。**Chrome 实测**：历史记录→会话详情→继续聊 → 聊天页正常填充历史 5 条 + 主席承接（"上回咱们说到…后来你咋想的？"）完整显示。
- ✅ 承接截断残字 — **实测发现并修复**：`d.summary.substring(0,50)` 在中文边界截出残字（如"盲目标"），已改为去尾标点 + 省略号（`?v=20260802c`）
- ✅ NPC场景建议已改为5分钟+只问一次（`idleCount>=16` 或疲劳黄/红 + `idleCount>=8`，`sceneSuggested` 防重）
- ✅ 退出倒计时CSS已补 — 清理了重复定义（旧底部条式 110-112 行覆盖新浮层式），仅保留浮层式 `exit-countdown`（bottom:70px 渐变卡片），待手机实测
- ✅ `chat-links` CSS 残留已删（HTML 引用此前已删）

## 未提交改动（本轮 + 上轮场景系统）

- `web/static/style.css` — 删 chat-links 残留 + 重复 exit-countdown 定义
- `web/static/app.js` — resumeFromLog 占位消息加 loading class；承接截断去残字（v=c）
- `web/static/index.html` — style.css/app.js 版本号统一 `v=20260802c`
- 上轮场景系统 7 项改造（scenes.py / game_engine.py / speak·think.jinja2 / web/app.py / app.js / index.html / style.css）均未提交

## 约束
- 不推GitHub（除非明确说）
- 不扫 `data/` `聊天记录/` `tools/` `.env`

## 建议加载
- AGENTS.md · KNOWLEDGE.md · docs/handoffs/
- Skill: handoff-seconic（全局）
