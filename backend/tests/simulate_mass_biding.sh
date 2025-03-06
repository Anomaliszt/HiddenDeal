#!/bin/bash

# Configuration
AUCTION_ID=${1:-1}  # Use the first argument as auction ID or default to 1
NUM_USERS=${2:-10}  # Default to 10 users for testing
API_URL="http://127.0.0.1:5000/api"
MIN_BID=1
MAX_BID=100
START_INDEX=${3:-1}  # Start user index, useful for continuing a previous run
TIMESTAMP=$(date +%s)  # Add timestamp to ensure unique usernames/emails

echo "Starting mass bidding simulation on auction $AUCTION_ID"
echo "Will create $(($NUM_USERS)) users starting from index $START_INDEX"
echo "Using timestamp $TIMESTAMP for unique usernames"

# Create a file to log successful bids
LOG_FILE="mass_bidding_$(date +%Y%m%d_%H%M%S).log"
echo "Logging results to $LOG_FILE"
echo "timestamp,user_id,username,email,bid_amount,response_code,status" > $LOG_FILE

# Initialize counters
success_count=0
failure_count=0

# Function for generating random float between min and max with 1 decimal place
random_bid() {
    local min=$1
    local max=$2
    local range=$(($max-$min+1))
    local rand=$((RANDOM % range + min))
    echo $rand  # Using whole numbers instead of floats for simplicity
}

# Debugging: Print API URL
echo "Using API URL: $API_URL"

# Create users and place bids
for i in $(seq $START_INDEX $(($START_INDEX + $NUM_USERS - 1))); do
    # Generate user details with timestamp to ensure uniqueness
    username="testuser${i}_${TIMESTAMP}"
    email="test${i}_${TIMESTAMP}@example.com"
    password="Password123!"  # More complex password to meet requirements
    
    echo -n "[$i/$((START_INDEX + NUM_USERS - 1))] Creating user $username... "
    
    # Register user - Create JSON payload as a variable first
    REGISTER_DATA="{\"username\":\"$username\",\"email\":\"$email\",\"password\":\"$password\"}"
    echo "Sending registration data: $REGISTER_DATA"
    
    register_response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d "$REGISTER_DATA")
    
    # Extract status code and save full response for debugging
    status_code=$(echo "$register_response" | tail -n1)
    register_body=$(echo "$register_response" | sed '$d')
    
    echo "Registration response: $register_body (HTTP $status_code)"
    
    if [[ "$status_code" != "201" && "$status_code" != "200" ]]; then
        echo "Failed (HTTP $status_code)"
        echo "Response: $register_body"
        echo "$(date +"%Y-%m-%d %H:%M:%S"),$i,$username,$email,0,$status_code,registration_failed" >> $LOG_FILE
        ((failure_count++))
        continue
    fi
    
    echo "Success! Logging in... "
    
    # Login to get token - Create JSON payload as a variable first
    LOGIN_DATA="{\"email\":\"$email\",\"password\":\"$password\"}"
    echo "Sending login data: $LOGIN_DATA"
    
    login_response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d "$LOGIN_DATA")
    
    # Extract status code and token
    status_code=$(echo "$login_response" | tail -n1)
    login_body=$(echo "$login_response" | sed '$d')
    
    echo "Login response: $login_body"
    
    if [[ "$status_code" != "200" ]]; then
        echo "Login Failed (HTTP $status_code)"
        echo "$(date +"%Y-%m-%d %H:%M:%S"),$i,$username,$email,0,$status_code,login_failed" >> $LOG_FILE
        ((failure_count++))
        continue
    fi
    
    # Extract token using Python for reliable parsing
    token=$(echo "$login_body" | python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    print(data.get('token', ''))
except Exception as e:
    print(f'Error parsing JSON: {e}', file=sys.stderr)
    print('')
" 2>/dev/null)
    
    # Fallback to grep if Python fails
    if [[ -z "$token" ]]; then
        echo "Python token extraction failed, trying grep..."
        token=$(echo "$login_body" | grep -o '"token"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d':' -f2 | tr -d ' "')
    fi
    
    if [[ -z "$token" ]]; then
        echo "Failed to extract token from: $login_body"
        echo "$(date +"%Y-%m-%d %H:%M:%S"),$i,$username,$email,0,$status_code,token_extraction_failed" >> $LOG_FILE
        ((failure_count++))
        continue
    fi
    
    echo "Token extracted successfully: ${token:0:15}..."
    
    # Generate random bid amount
    bid_amount=$(random_bid $MIN_BID $MAX_BID)
    
    echo -n "Placing bid of $bid_amount... "
    
    # Place bid - Create JSON payload as a variable first
    BID_DATA="{\"auctionId\":$AUCTION_ID,\"amount\":$bid_amount}"
    echo "Sending bid data: $BID_DATA"
    
    bid_response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/bids/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d "$BID_DATA")
    
    # Extract status code
    status_code=$(echo "$bid_response" | tail -n1)
    bid_body=$(echo "$bid_response" | sed '$d')
    
    if [[ "$status_code" != "201" && "$status_code" != "200" ]]; then
        echo "Failed to place bid (HTTP $status_code)"
        echo "Response: $bid_body"
        echo "$(date +"%Y-%m-%d %H:%M:%S"),$i,$username,$email,$bid_amount,$status_code,bid_failed" >> $LOG_FILE
        ((failure_count++))
    else
        echo "Success!"
        echo "$(date +"%Y-%m-%d %H:%M:%S"),$i,$username,$email,$bid_amount,$status_code,success" >> $LOG_FILE
        ((success_count++))
    fi
    
    # Add a small delay to avoid overwhelming the server
    sleep 0.1
done

echo "Simulation complete!"
echo "Successfully created and placed bids for $success_count users"
echo "Failed for $failure_count users"
echo "Results logged to $LOG_FILE"