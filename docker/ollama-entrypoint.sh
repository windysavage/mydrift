#!/bin/sh

echo "🚀 啟動 Ollama Server..."
ollama serve &

# 等待 API server 就緒（你可以調整 sleep 時間或改成 loop 探測）
sleep 3

echo "📦 檢查模型是否存在：gemma:4b"

MODEL_EXISTS=$(curl -s http://localhost:11434/api/show \
  -H "Content-Type: application/json" \
  -d '{"name": "gemma:4b"}' | grep -c '"modelfile"')

if [ "$MODEL_EXISTS" -gt 0 ]; then
  echo "✅ gemma:4b 已存在，跳過下載"
else
  echo "⬇️ gemma:4b 不存在，開始拉取..."
  curl -X POST http://localhost:11434/api/pull \
    -H "Content-Type: application/json" \
    -d '{"name": "gemma:4b"}'
fi

echo "🟢 Ollama 初始化完成，等待主程序結束..."
wait
