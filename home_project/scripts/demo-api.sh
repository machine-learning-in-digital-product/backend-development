#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1:8003}"
COOKIE_JAR="${COOKIE_JAR:-$(dirname "$0")/../.demo-api-cookies.txt}"

echo "=== GET / ==="
curl -sS "$BASE/" | jq .
echo

echo "=== POST /login (demo / demo123) ==="
curl -sS -c "$COOKIE_JAR" -X POST "$BASE/login" \
  -H "Content-Type: application/json" \
  -d '{"login":"demo","password":"demo123"}' | jq .
echo

echo "=== POST /predict ==="
curl -sS -b "$COOKIE_JAR" -X POST "$BASE/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": 100,
    "is_verified_seller": true,
    "item_id": 9001,
    "name": "Демо товар",
    "description": "Описание для проверки модерации и simple_predict",
    "category": 2,
    "images_qty": 3
  }' | jq .
echo

echo "=== POST /simple_predict?item_id=9001 ==="
curl -sS -b "$COOKIE_JAR" -X POST "$BASE/simple_predict?item_id=9001" | jq .
echo

echo "=== POST /async_predict?item_id=9001 ==="
ASYNC_JSON=$(curl -sS -b "$COOKIE_JAR" -X POST "$BASE/async_predict?item_id=9001")
echo "$ASYNC_JSON" | jq .
TASK_ID=$(echo "$ASYNC_JSON" | jq -r '.task_id')
echo

if [[ -n "$TASK_ID" && "$TASK_ID" != "null" ]]; then
  echo "=== GET /moderation_result/$TASK_ID ==="
  curl -sS -b "$COOKIE_JAR" "$BASE/moderation_result/$TASK_ID" | jq .
  echo
fi

echo "(Пропуск POST /close — удалит item 9001. При необходимости:)"
echo "curl -sS -X POST \"$BASE/close?item_id=9001\" | jq ."
