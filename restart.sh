#!/bin/bash

set -e

echo "=================================="
echo "客服系统重启脚本"
echo "=================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "[1/6] 检查当前目录: $PROJECT_DIR"

echo ""
echo "[2/6] 停止现有服务..."
pkill -f "python.*main.py" 2>/dev/null || true
sleep 1

echo ""
echo "[3/6] 清理旧数据（可选）..."
echo "是否清理数据库和上传文件？"
echo "  y - 清理所有数据（重新开始）"
echo "  n - 保留数据"
echo ""
echo "请输入选择 (y/n)，然后按回车："
read REPLY

if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
    echo "正在清理..."
    rm -f app/chat_system.db
    rm -rf app/uploads
    echo "清理完成！"
else
    echo "跳过清理。"
fi

echo ""
echo "[4/6] 确保目录存在..."
mkdir -p app/uploads

echo ""
echo "[5/6] 同步依赖..."
uv sync

echo ""
echo "[6/6] 启动服务..."
echo ""
echo "=================================="
echo "服务启动信息:"
echo "=================================="
echo "访客端: http://localhost:4444/"
echo "客服端: http://localhost:4444/agent"
echo "=================================="
echo ""
echo "测试流程:"
echo "1. 打开客服端 http://localhost:4444/agent"
echo "2. 打开访客端 http://localhost:4444/"
echo "3. 访客发送消息，客服应该能收到"
echo "=================================="
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

exec uv run python main.py
