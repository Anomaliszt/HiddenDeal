#!/bin/bash

# Default values
USER_ID=${1:-1}
AMOUNT=${2:-100}

# Check if TOKEN is set
if [ -z "$TOKEN" ]; then
    echo "Error: TOKEN environment variable not set. Please run:"
    echo "export TOKEN=your_admin_jwt_token"
    exit 1
fi

echo "Adding $AMOUNT to wallet of user $USER_ID..."

# Make the API request using proper POST body instead of URL parameters
curl -X POST http://127.0.0.1:5000/api/wallet/admin/add \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $TOKEN" \
-d '{
    "user_id": '"$USER_ID"',
    "amount": '"$AMOUNT"'
}'


