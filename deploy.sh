#!/bin/bash
# deploy.sh — ChairManMao（主席模拟器）一键部署到独立 EC2（Amazon Linux 2023）
# 用法:
#   bash deploy.sh <EC2_IP> [SSH_KEY路径]
# 示例:
#   bash deploy.sh 54.xxx.xxx.xxx
#   bash deploy.sh 54.xxx.xxx.xxx ~/.ssh/chairmanmao-key.pem
#
# 流程: 本地打包 → scp 上传 → 远程解压 → 恢复/初始化 .env → python3.11 + venv 依赖
#       → 写入 systemd 单元 → 启动服务 → /api/status 验证
set -e

HOST="${1:?用法: bash deploy.sh <EC2_IP> [SSH_KEY路径]}"
KEY="${2:-~/.ssh/chairmanmao-key.pem}"
REMOTE_USER="ec2-user"                    # Amazon Linux 2023 默认用户
REMOTE_DIR="/home/ec2-user/chairmanmao"
SERVICE="chairmanmao"
PORT="8000"

# 本地项目根（脚本所在目录）
PROJ="C:/Users/68090/Desktop/ChairManMao"
SSH_OPTS="-o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"

echo "📦 [1/6] 本地打包（代码 + 向量库 + 语料，排除敏感/冗余）..."
cd "$PROJ"
tar czf /tmp/chairmanmao-deploy.tar.gz \
  --exclude='*/__pycache__' \
  --exclude='tools/nssm' \
  --exclude='.git' \
  --exclude='data/chroma_db' \
  --exclude='data/chroma_v2' \
  --exclude='data/logs' \
  --exclude='data/chunks.jsonl' \
  --exclude='data/extracted/chunks.jsonl' \
  --exclude='.env' \
  web/ pipeline/ rag/ reasoning/ tools/ run_server.py run_pipeline.py requirements.txt .env.example \
  data/chroma_v3/ data/txt/ data/extracted/ data/baidu_hot.json
echo "   包大小: $(du -sh /tmp/chairmanmao-deploy.tar.gz | cut -f1)"

echo "📤 [2/6] 上传到 AWS ($HOST)..."
scp $SSH_OPTS -i "$KEY" /tmp/chairmanmao-deploy.tar.gz ${REMOTE_USER}@$HOST:~/

echo "🔧 [3/6] 远程部署（备份 .env → 解压 → 恢复 .env）..."
ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "
  set -e
  # 备份 .env（若已存在）
  if [ -f $REMOTE_DIR/.env ]; then
    cp $REMOTE_DIR/.env /tmp/chairmanmao-env.bak
    echo '   [deploy] 已备份现有 .env'
  fi

  # 解压到 $REMOTE_DIR
  mkdir -p $REMOTE_DIR
  cd $REMOTE_DIR && tar xzf ~/chairmanmao-deploy.tar.gz

  # 恢复 .env（首次部署时由本地通过 stdin 写入，见下方）
  if [ -f /tmp/chairmanmao-env.bak ]; then
    cp /tmp/chairmanmao-env.bak $REMOTE_DIR/.env
    echo '   [deploy] 已恢复 .env'
  fi
"

# 首次部署：若远程无 .env，从本地 .env 经 SSH 加密通道写入（key 不进 tar 包）
if ! ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "test -f $REMOTE_DIR/.env" 2>/dev/null; then
  echo "🔑 [3.5] 首次部署，初始化远程 .env（本地 → SSH 加密通道直写）..."
  ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "cat > $REMOTE_DIR/.env" < "$PROJ/.env"
  echo "   [deploy] 远程 .env 已写入（含 DeepSeek key，仅存服务器端）"
fi

echo "🐍 [4/6] 远程创建 venv + 安装依赖..."
ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "
  set -e
  # Amazon Linux 2023 默认 python3.9，需确保 python3.11
  if ! command -v python3.11 >/dev/null 2>&1; then
    echo '   [deploy] 安装 python3.11 (dnf)...'
    sudo dnf install -y python3.11
  fi
  if [ ! -d $REMOTE_DIR/venv ]; then
    python3.11 -m venv $REMOTE_DIR/venv
    echo '   [deploy] 新建 venv (python3.11)'
  fi
  $REMOTE_DIR/venv/bin/pip install --upgrade pip -q
  $REMOTE_DIR/venv/bin/pip install -r $REMOTE_DIR/requirements.txt -q
  echo '   [deploy] 依赖安装完成'
"

echo "⚙️  [5/6] 写入 systemd 单元并启动服务..."
ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "
  set -e
  cat > /tmp/chairmanmao.service <<'EOF'
[Unit]
Description=ChairManMao 主席模拟器
After=network.target

[Service]
Type=simple
User=${REMOTE_USER}
WorkingDirectory=$REMOTE_DIR
EnvironmentFile=$REMOTE_DIR/.env
ExecStart=$REMOTE_DIR/venv/bin/python3 run_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  sudo cp /tmp/chairmanmao.service /etc/systemd/system/$SERVICE.service
  sudo systemctl daemon-reload
  sudo systemctl enable $SERVICE
  sudo systemctl restart $SERVICE
  sleep 5
  echo '   [deploy] systemd 服务已启动'
"

echo "✅ [6/6] 验证服务..."
ssh $SSH_OPTS -i "$KEY" ${REMOTE_USER}@$HOST "
  for i in \$(seq 1 12); do
    resp=\$(curl -s --max-time 5 http://localhost:$PORT/api/status 2>/dev/null) && break
    sleep 5
  done
  echo \"   /api/status: \$resp\"
  if echo \"\$resp\" | grep -q '\"rag\":true'; then
    echo '   ✅ RAG 向量库加载成功'
  else
    echo '   ⚠️  rag 未加载，检查日志: journalctl -u $SERVICE -n 50'
  fi
  if echo \"\$resp\" | grep -q '\"llm\":true'; then
    echo '   ✅ LLM 配置成功'
  else
    echo '   ⚠️  llm 未配置，检查远程 .env 的 OPENAI_API_KEY'
  fi
"

echo ""
echo "🎉 部署完成！"
echo "   公网访问: http://$HOST:$PORT/"
echo "   服务:     $SERVICE (systemd)"
echo "   目录:     $REMOTE_DIR"
echo ""
echo "   📱 手机外网访问前请确认安全组已开放 TCP $PORT (0.0.0.0/0)"
