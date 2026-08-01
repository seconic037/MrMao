# 设计规格：MrMao 主席模拟器 — Windows 便携版打包（exe）

> 日期：2026-08-01 · 状态：已获用户认可 · 方案：Embedded Python 绿色版

## 1. 背景与目标

用户希望在**任何其他 Windows 电脑**上运行 MrMao 主席模拟器（"游戏"），目标电脑使用者为**完全小白**（无 Python、无命令行经验），要求**双击即用**。

### 约束（探索阶段确认）

| 项 | 值 | 影响 |
|----|----|------|
| 运行时依赖 | torch CPU **523M** + chromadb 1.5.9 + sentence-transformers 5.6.1 + onnxruntime + tokenizers | Python 依赖层约 1.2GB |
| 数据 | data/ 262M（chroma_v3 **173M**）、嵌入模型 bge-small-zh-v1.5 **93M**、static 24M | 数据层约 500MB |
| LLM | DeepSeek API（**必须联网** + API key） | 非纯离线游戏 |
| 后端 | FastAPI + uvicorn，`run_server.py` 入口，端口 8000 | launcher 需拉起服务 |
| 前端 | 原生 HTML/CSS/JS，`web/static/` | 随数据目录携带 |
| 向量库 | chromadb 内置 HNSW（无外部 hnswlib） | 打包兼容性好 |

**用户已确认的决策：**
1. ✅ 接受联网依赖 + 用户提供 DeepSeek API key
2. ✅ 目标电脑为完全小白 → 双击即用
3. ✅ 交付形态：**单文件夹便携版**
4. ✅ API key **首次启动时填写**，不打包进分发包
5. ✅ 方案：**Embedded Python 绿色版**（非 PyInstaller 全打包）

## 2. 目录结构

```
ChairMao游戏/                      ← 整个文件夹拷贝到任何 Windows 电脑
├── 主席模拟器.exe                ← launcher（双击启动，~10MB，PyInstaller 打）
├── python/                       ← 嵌入式 Python 3.11 + 全部依赖（~1.2GB）
│   └── python.exe + site-packages/
├── app/                          ← 项目代码（web/ pipeline/ rag/ reasoning/ run_server.py）
├── data/                         ← 向量库 chroma_v3 + 嵌入模型 + static + 语料（~500MB）
├── .env                          ← 首次启动自动生成，无 API key 则由用户填写
├── 聊天记录/                     ← 运行时生成（会话日志）
└── 使用说明.txt                  ← 给小白的一句话说明
```

## 3. 启动流程（launcher 职责）

1. 定位自身所在目录 `Path(sys.executable).parent`
2. 校验 `python/python.exe` 与 `data/` 关键文件存在 → 缺失弹窗提示
3. 校验 `.env` 中 API key：
   - `.env` 不存在 → 自动生成模板
   - key 为空 → 打开浏览器引导页（`http://localhost:8000/setup` 或独立提示页）让用户填写并保存
4. 探测端口：8000 被占用 → 自动选空闲端口
5. 子进程启动 `python/python.exe app/run_server.py --port=<空闲端口>`
6. 轮询 `http://localhost:<port>` 就绪（≤10s）→ `webbrowser.open`
7. launcher 进程保持运行（控制台窗口或托盘图标），提供退出入口
8. 多开保护：检测本程序已运行 → 直接打开浏览器不重复启动

## 4. Embedded Python 构建流程

1. 从 python.org 下载 `python-3.11.x-embed-amd64.zip`（官方嵌入式发行版）
2. 启用 site：编辑 `python311._pth` 放开 `import site`
3. 注入 pip（`get-pip.py`）
4. `pip install -r requirements-lock.txt`（锁定版本，保证行为一致）
5. 拷贝 `app/`、`data/`、前端资源到便携目录
6. 用 PyInstaller 构建 launcher exe（**仅 subprocess/webbrowser/os/socket 等标准库**，不含 torch/chromadb）
7. 产出 `ChairMao游戏/` 文件夹
8. 用 `build_package.py` 一键完成上述全部步骤（可重复构建）

### 版本锁定

- 用 `pip freeze` 生成 `requirements-lock.txt`
- 关键包当前版本：chromadb 1.5.9、sentence-transformers 5.6.1、torch 2.13.0+cpu、fastapi 0.133.1、openai 2.24.0

## 5. API Key 处理

- **不打包** key 进分发包
- 首次启动引导用户填写，保存到便携目录 `.env`
- `.env` 位于便携目录内（可随包移动，换电脑不丢配置）

## 6. 错误处理与边界情况

| 场景 | 处理 |
|------|------|
| 无 API key | 首次启动弹引导页填 key，保存到 `.env` |
| 端口 8000 占用 | launcher 自动探测空闲端口并传 `--port=` |
| 向量库/模型缺失 | 启动前校验，弹窗提示具体缺失项 |
| 断网 | 页面正常打开；对话时报"网络异常"（现有前端逻辑已覆盖） |
| 杀毒误报 | Embedded Python + 小 launcher 误报率低；如遇误报需用户加白名单 |
| 多开 | 端口检测，已运行则直接开浏览器 |
| 目标电脑无中文字体/系统 | 使用系统默认字体，不依赖特殊环境 |

## 7. 测试计划

1. **本机构建**：`build_package.py` 产出完整 `ChairMao游戏/` 文件夹
2. **双击启动**：launcher → 页面打开 → 对话正常（含 RAG、场景、日志、热点）
3. **无 key 首次运行**：删除 `.env` → 验证引导填 key → 保存后续用正常
4. **端口占用**：先占 8000 → 验证自动换端口
5. **体积与耗时**：总体积、双击到页面打开耗时（目标 < 10 秒）
6. **外置数据升级**：替换 `data/` 或 `app/` 后仍正常运行（验证外置目录设计）

## 8. 范围说明

**包含：**
- 便携文件夹构建脚本（`build_package.py`）
- launcher exe（`launcher/` 独立小项目）
- 首次启动 API key 引导
- 端口自适应
- 使用说明.txt

**不包含（YAGNI）：**
- 安装程序（NSIS/Inno）——用户已选便携版
- 完全离线 LLM——用户已接受联网
- 自动更新机制——后续可按需增加
- Docker/服务器中转——已排除
