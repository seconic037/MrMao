# 项目继承快照: MrMao 主席模拟器
> 最后导出 | 2026-08-07 04:49 | 状态：🔄 活跃中

## 当前进度（一句话）
自然对话重构（手册 v3→v5 + S1~S8）**全部完成**，交付检查 7 轮全部通过，项目处于完整可发布状态，服务器运行最新引擎。

## 已完成
- **自然对话重构**（13 commits 基线 + S1~S8 扩展，git `218e589..HEAD` 共 30+ commits）：
  - 手册 v3 → **v5**（通用自然对话规则手册 0~12 层 + 三大原则 + 机制配置接口），主席配置（第一个实例，10 特质×情境 + C1~C8 裁定）
  - **意图判断器** `pipeline/intent.py`：双轴标签（情绪 negative/positive/neutral 含否定过滤 + 需求 info/affection/action 带隶属度）+ kind 细分（test/approval/comfort/retreat/info）+ 场景信号（scenes/situations/arousal 四象限）
  - **话题主线** `pipeline/topic_thread.py`：jieba Jaccard 话题切换检测
  - **think.jinja2**：意图驱动内心思考，注入对方此刻/话题线/摘要含情绪/最近原话/RAG/知识框架 + kind→策略映射 + 语体分寸（S1 师者传道）
  - **speak.jinja2**：自然对话规则（接话/长度波动/结构自由/口头禅低频/反问非必须/情感先行/禁术语）+ 场景/称呼/动作约束 + 特殊场景应对（冲突/幽默/拒绝/沉默/情绪）
  - **三层记忆**：raw_buffer(2轮原文) + memories(5条含emotion) + topic_thread(全程)
  - **S5 长期记忆持久化**：_meta 快照写入/恢复三层记忆
  - **冷场挂起**：首动后静默，场景建议独立 4min 计时
- **考考你**：改为完全主动触发（找话题→考考你），弹窗内作答+题目介绍+确认关闭
- **热搜**：口语化简述 + 🔗看原文（弹窗内读正文，必应源）
- **全部交付检查**：62 unittest 全过、前端 UI 端到端实测、API 全链路、README/AGENTS/设计文档/交接全同步、前端缓存版本递增 v20260806

## 进行中 / 未完成
- 无进行中的开发任务
- **用户自做的更长时间真实对话体验**（result.md 遗留项，非阻塞）
- S2 性格动态化（远期）、S5-B/C 多会话归档/跨会话召回（远期，session_id 已预留）

## 关键决策（含原因）
- **意图判断走规则粗判 + LLM 精修（路线 B）**：意图错了后面全错，纯 LLM 判断不稳定；规则保稳定性、LLM 保自然度
- **双轴多维标签而非唯一标签**：需求常并存（求安慰+求认可），单标签逼模型二选一失真
- **框架/语料库喂养"想"不喂养"说"**：分析是暗线不是台词（speak 禁术语，S1 改"先比喻讲透再术语收口"）
- **三层记忆而非全量保留**：人记整体靠"话题演变"不是句子数量（Zacks & Tversky 事件分割理论）
- **场景选择只在场景模式弹出**（普通模式默认不弹）；恢复对话弹三选项（总结由NPC发起/由我发起/直接聊）
- **README/AGENTS 必须同步**：每次功能改动同步文档（AGENTS.md 规则 9）

## 踩坑记录
- **bat 编码**：UTF-8 bat 在 cmd 下乱码 → 必须 GBK 编码 + 纯 ASCII 内容（`主席你好.bat` 已修）
- **`where python` 解析错误**：可能解析到 hermes venv/WindowsApps stub → 启动脚本固定 uv python 路径
- **8000 端口被占**：服务器已在跑时再 `python run_server.py` 报 Errno 10048 → `主席你好.bat` 先检测端口
- **subprocess GBK 解码**：`/api/knowledge/structure` 曾因 subprocess 文本编码崩溃 → 加 `encoding="utf-8"`
- **意图判断时序**：analyze_intent 必须在 think 调用**前**执行（曾因顺序错误导致本轮意图进不了本轮 think）
- **记忆格式**：session_memories 恢复路径曾存字符串（模板期望 dict）→ 统一 {question, summary, emotion}
- **knowledge_base 注入回归**：build_think_prompt 重构时曾丢 knowledge_base → 修复为默认注入 + **extra 可覆盖
- **百度反爬**：urllib 抓百度搜索页会触发安全验证 → 热点看原文改必应源
- **前端缓存**：改 app.js 后必须递增版本号（v=20260806），否则浏览器加载旧 JS

## 下一步行动（按优先级）
1. **用户真实体验**：在 `http://localhost:8000`（手机 `http://192.168.0.9:8000`）长时间对话，验证 v5 手册层间一致性；发现问题按"三大原则"定位（内容干瘪→查知识库 / 不像角色→查人设 / 接得不对→查规则）
2. **可选**：Windows 服务方式运行（`install_service.bat` 右键管理员执行；当前用 `主席你好.bat` 前台进程即可）
3. **远期**：S2 性格动态化、S5-B/C 多会话归档（session_id 已预留）

## 待决问题
- 无待决问题（所有设计决策均已经用户确认）

## 项目环境（技术栈/启动方式）
- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · Uvicorn · ChromaDB（collection `maozedong-works` 6339 块）· DeepSeek API（deepseek-v4-flash）
- 启动: `python run_server.py` → `http://localhost:8000`（或双击 `主席你好.bat`，端口占用时自动只开浏览器）
- 前端: 原生 HTML/CSS/JS · 四 Tab（首页/日志/场景/阅读）· 前端版本号 v20260806
- 测试: unittest（`python -m unittest discover -s tests`，62 用例）
- 向量库重建: `python run_pipeline.py`（3-10 分钟）

## 相关文件索引（指针，不复制内容）
- 手册 v5: `docs/superpowers/specs/2026-08-06-natural-conversation-rules-v5.md`
- 主席配置: `docs/superpowers/specs/2026-08-06-mao-config.md`
- 设计文档: `docs/superpowers/specs/2026-08-06-{natural-conversation-redesign,scene-signal-detector-design,long-term-memory-design,personality-layer-notes}.md`
- 交接+结果: `docs/handoffs/2026-08-06-natural-conversation-rules.md` + `-result.md`
- 进度台账: `.superpowers/sdd/progress.md`
- 实现计划: `docs/superpowers/plans/2026-08-06-natural-conversation-redesign.md`
- git: master 分支，HEAD `c22cf07`

## 建议加载的 Skill/文档
- Skill: `maozedong-wenxian`（文献知识）· `maoxuan-workbench`（毛选方法论）· `inherit-seconic`（本快照）· `handoff-seconic`（任务外派）
- 记忆: `除非用户主动说-否则不上传-github` · `kb-editor-桌面编辑器已上线`（分支已完结勿混提）
