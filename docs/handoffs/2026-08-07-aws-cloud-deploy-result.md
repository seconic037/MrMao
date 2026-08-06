# Handoff Result: AWS 云端部署（ChairManMao 上云）
> 从 2026-08-07-aws-cloud-deploy.md 派生 | 2026-08-07
> 状态：⏸️ 已搁置（用户决定本地使用，2026-08-07）

## 结论
**云端部署暂停**。用户完成实例创建与 SSH 打通后，因实例内存 908Mi（t3.micro）不满足 ≥2GB 要求、升级需额外费用，决定「先不折腾了，在本地玩」。EC2 实例 43.196.86.46 仍存在（未终止）。

## 本次进展（已完成部分）
1. **摸清 AI店长 部署方案**：EC2 + scp 打包 + systemd（`ExecStart=venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`、`EnvironmentFile=/home/ubuntu/.env`）
2. **确认 ChairManMao 无需改代码**：`run_server.py` 已绑定 0.0.0.0 + 端口参数化
3. **完成打包清单验证**：代码 4007 行 + `data/chroma_v3/`（56 文件 173MB，库结构完整）+ `data/txt/` + `data/extracted/` + `data/baidu_hot.json`，包 151M；排除旧库/日志/.env/__pycache__
4. **编写 `deploy.sh`**（bash -n 通过）：打包→scp→解压→.env 经 SSH stdin 初始化→venv→systemd→`/api/status` 验证（rag+llm 双检查）
   - ⚠️ **当前为 Amazon Linux 适配版**（`REMOTE_USER=ec2-user`、`dnf install python3.11`）——因为实例最初是 Amazon Linux 2023
5. **更新 `.env.example`** 为云端模板（deepseek-v4-flash + chroma_v3 + 端口说明）
6. **README.md 新增「☁️ 云端部署（AWS EC2）」章节**
7. **SSH 打通**：经历 key 指纹不匹配（本地 pem ≠ AWS key pair）→ EC2 Instance Connect 浏览器终端注入公钥 → 最终 `ubuntu@43.196.86.46` 用本地 `chairmanmao-key.pem` 免密登录成功

## 遗留问题（未来继续时）
1. **实例规格不达标**：43.196.86.46 是 **t3.micro（908Mi）**，跑不动 bge-small-zh + ChromaDB 常驻（OOM 风险，且可能损坏向量库）。继续部署前必须升级 **t3.small（2GB）**（停止→改类型→启动，IP 会变）
2. **deploy.sh 需按系统适配**：
   - 当前实例是 **Ubuntu 26.04**（用户后改的），部署到它需改 `REMOTE_USER=ubuntu`、`REMOTE_DIR=/home/ubuntu/chairmanmao`、python3.11 改用 `apt-get install -y python3.11 python3.11-venv`
   - 建议参数化（`--user` / 自动探测 os-release）
3. **公钥已注入**实例 `/home/ubuntu/.ssh/authorized_keys`（本地 pem 的公钥），SSH 免密已通；但实例 key pair 与本地 pem 指纹不一致的历史问题无需再处理（已绕开）
4. **费用提醒**：43.196.86.46 仍在运行会产生费用，若长期不用建议用户终止（终止不可逆，需用户自行确认）
5. **隐私**：本地 `.env`（DeepSeek key）从未打包/上传，符合约束

## 已就绪可复用的资产
- `deploy.sh`（打包/上传/systemd/验证全流程，改用户变量即可用）
- `.env.example` 云端模板
- README 云端部署章节
- 公钥注入操作流程（EC2 实例连接 → 粘贴单行命令）

## 收尾
交接文档 `2026-08-07-aws-cloud-deploy.md` 状态已改为 ⏸️ 已搁置。后续若用户想继续，读本文档 + 交接文档即可无缝接手。

> 2026-08-07 补充：用户已在 AWS 控制台**删除实例（43.196.86.46）**，无持续费用。本地运行不受影响。
