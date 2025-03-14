#!/bin/bash
TITLE=${1:-"test"}
DESCRIPTION=${2:-"This is a test auction created via the API"}
ITEM_VALUE=${4:-500}
EXPIRY_DATE="2025-03-07T16:17:30"

curl -X POST http://127.0.0.1:5000/api/auctions/ \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $TOKEN" \
-d '{
  "title": "'"$TITLE"'",
  "description": "'"$DESCRIPTION"'",
  "starting_price": '"$ITEM_VALUE"',
  "item_value": '"$ITEM_VALUE"',
  "expires_at": "'"$EXPIRY_DATE"'"
}'
