#!/bin/bash
# 啟動 ollama → 跑 pipeline → 收尾 (同一個 shell session，避免 WSL idle 把 ollama 殺掉)
set -e

export LD_LIBRARY_PATH=$HOME/.local/ollama/lib/ollama:$LD_LIBRARY_PATH

# 啟動 ollama
$HOME/.local/ollama/bin/ollama serve > $HOME/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "[wrapper] ollama PID=$OLLAMA_PID" >&2

# 等 ollama ready
for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 1
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "[wrapper] ollama ready after ${i}s" >&2
        break
    fi
done

# 預熱模型（避免第一次 call 8 秒慢）。keep_alive=30m 讓模型整輪 run 都常駐。
echo "[wrapper] warming up qwen3-vl:4b-instruct..." >&2
curl -s -X POST http://localhost:11434/api/generate \
    -d '{"model":"qwen3-vl:4b-instruct","prompt":"hi","stream":false,"keep_alive":"30m","options":{"num_predict":5}}' \
    >/dev/null 2>&1 || true

# 註：retry 模型已預設改用 4b（8b 與 4b 同時常駐時在本機 100%% HTTPError，VRAM 不足）。
# 若改用 --vlm-model-retry qwen3-vl:8b，需自行確認顯卡夠大，並在此加 8b 預熱。

# 跑 pipeline（不讓 set -e 在 pipeline 失敗時跳過下面的收尾）
echo "[wrapper] running pipeline..." >&2
PIPELINE_EXIT=0
python3 $HOME/video_pipeline/video_pipeline.py "$@" || PIPELINE_EXIT=$?
echo "[wrapper] pipeline exit=$PIPELINE_EXIT" >&2

# 收尾
kill $OLLAMA_PID 2>/dev/null || true
wait $OLLAMA_PID 2>/dev/null || true
exit $PIPELINE_EXIT
