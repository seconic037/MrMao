# Handoff: 场景系统 + 游戏化互动
> 从 ChairManMao 项目分叉 | 2026-07-31

## 任务目标

为主席模拟器增加：4 个互动场景 + 游戏化问答（考考你）——全部 5 个 Phase 已完成编码，编译通过，待启动测试。

## 项目环境

- 项目路径: `C:\Users\68090\Desktop\ChairManMao`
- Python 3.11 · FastAPI · ChromaDB · DeepSeek API
- 前端: 原生 HTML/CSS/JS，移动端响应式
- 启动: `python run_server.py` → `http://localhost:8000`
- 管道: `python run_pipeline.py`（新增语料后重跑）

## 已完成功能

### Phase 1：核心场景系统
4 个场景，带氛围文本、专属动作库、事物清单：

| 场景ID | 名称 | 类型 |
|--------|------|------|
| `shuwu` | 菊香书屋 | 室内·办公 |
| `keting` | 丰泽园客厅 | 室内·居家 |
| `xiaolu` | 菊香书屋外的小路上 | 室外·办公周围 |
| `shuxia` | 丰泽园外的树下 | 室外·家周围 |

- 场景标签栏（聊天页 stats-bar 下方），点击切换
- speak.jinja2 注入场景氛围 + 动作约束（室内禁室外动作，室外禁桌面动作）
- 背景图动态切换（9 张 9:16 竖屏图片已放入 `web/static/img/scenes/`）

### Phase 2：场景互动
- `build_speak_prompt(scene_context)` 传入场景信息
- idle-actions 按场景返回专属动作（70% 场景动作 + 30% 通用动作）
- 连续 2 次冷场后，主席主动提议切换场景（弹窗确认）

### Phase 3：场景切换动画
- 幻灯片背景过渡：旧场景 fadeOut → 过渡背景图 + 文字逐字显示 → 新场景 fadeIn
- 6 种跨类型切换（门廊/走廊/庭院入口/傍晚/小径），同类型直接切换
- 用户说话中表达"出去走走"/"进屋"→ 自动检测并触发切换

### Phase 4：主席主动结束
- 30s 冷场动作 → 8min 疲倦预警 → 10min 离开语 → 1min 倒计时自动保存退出
- 离开语按场景分层（室内"我让警卫员送你出去"、室外"太阳快落山了"）
- 倒计时条底部弹出，可"再聊会儿"取消或"立即退出"

### Phase 5：游戏化·考考你
- 30 题题库（哲学/党史/历史/诗词/军事各 6 题），嵌入对话流（非独立面板）
- 加权选题按场景偏好（书房偏党史、树下偏诗词）
- 主席主动出题（每 15 轮最多 1 次）+ 用户点击 🔔 快捷求考
- 答对赞美 + 答错纠正 + 连对 3/5/7 题特殊表扬

## 涉及文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `pipeline/scenes.py` | **新增** | 场景定义、动作库（通用+场景+疲劳+离开）、事物清单、过渡配置、切换检测 |
| `pipeline/game_engine.py` | **新增** | 30 题题库、加权选题、答题判定、赞美语库、出题频次控制 |
| `web/app.py` | 修改 | +5 个场景 API（set/get/transition/exit/suggest）、quiz 答题检测+出题、TIMEOUT 10min |
| `reasoning/framework.py` | 修改 | `build_speak_prompt(question, thinking, scene_context)` |
| `reasoning/prompts/speak.jinja2` | 修改 | +当前场景块（名称+氛围+事物+动作约束） |
| `web/static/index.html` | 修改 | +场景标签栏（4 个 scene-tag）、+🔔 按钮、+过渡层 div、+倒计时 UI |
| `web/static/app.js` | 修改 | +currentScene/setScene/playTransition、+idle 增强（离开倒计时/提议切换）、+quiz UI（showQuiz/answerQuiz） |
| `web/static/style.css` | 修改 | +场景标签/过渡层/问答选项/退出倒计时样式、+背景图切换 |
| `web/static/img/scenes/` | **新增** | 9 张 9:16 竖屏背景图（4 主场景 + 5 过渡场景，PNG，待转 WebP） |
| `docs/scene-system-design.md` | **新增** | 完整设计文档 v2.0 |
| `docs/scene-bg-prompts.txt` | **新增** | 9 张背景图 GPTIMAGE2 提示词 |
| `docs/branch-scenes-game.md` | **新增** | 分支规划文档 |

## API 路由（新增 7 个）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/scene/set` | POST | 切换场景，返回过渡信息 |
| `/api/scene/get` | GET | 获取当前场景 |
| `/api/scene/transition` | POST | 获取两场景过渡信息 |
| `/api/scene/exit` | GET | 生成主席离开语 |
| `/api/scene/suggest` | GET | 主席提议切换场景 |
| ChatResp 新增字段 | — | `scene_switch`（切换检测）、`quiz`（出题）、`quiz_result`（答题结果） |

## 如何测试

```bash
cd C:\Users\68090\Desktop\ChairManMao
python run_server.py
# 打开 http://localhost:8000
# 进入聊天 → 点击场景标签切换 → 说话触发场景感知
# 等待 30s 看冷场动作 → 等待 2 次冷场看主席提议切换
# 点击 🔔 按钮看考考你出题
```

## 约束

- 不推 GitHub（除非用户明确说）
- 不改变 RAG/think/日志系统（正交设计）
- 背景图目前是 PNG，建议后续转 WebP 减小体积
- `web/static/img/scenes/` 文件名已约定，CSS/JS 硬编码引用
- 主席离开的 10min/8min 阈值在 `web/app.py` 常量 `TIMEOUT_SECONDS`/`TIMEOUT_WARN`

## 建议后续

1. **启动测试**：实际跑一遍聊天流程，验证场景切换、冷场、离开全链路
2. **背景图优化**：PNG → WebP（预计从 2-3MB 缩到 200-400KB）
3. **过渡动画调参**：`playTransition()` 中逐字速度 60ms/字可调
4. **题库扩充**：如果需要，在 `pipeline/game_engine.py` 追加题目
