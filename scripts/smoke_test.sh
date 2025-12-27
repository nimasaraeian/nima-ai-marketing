#!/bin/bash
# Smoke test for /api/analyze/url-human endpoint
# Tests that capture.artifacts are always present with url or data_uri

BASE="http://127.0.0.1:8000"
ENDPOINT="$BASE/api/analyze/url-human"

echo "Testing /api/analyze/url-human endpoint..."
echo "Endpoint: $ENDPOINT"
echo ""

PAYLOAD='{"url":"https://stripe.com/pricing","goal":"leads","locale":"en"}'

echo "Sending request..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --max-time 180)

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" != "200" ]; then
  echo "FAIL: HTTP status code is $HTTP_CODE (expected 200)"
  echo "Response: $BODY"
  exit 1
fi

echo "HTTP Status: 200 OK"
echo ""

# Check capture exists
if echo "$BODY" | jq -e '.capture == null' > /dev/null 2>&1; then
  echo "FAIL: response.capture is null"
  exit 1
fi
echo "PASS: response.capture exists"

# Check artifacts structure
if echo "$BODY" | jq -e '.capture.artifacts == null' > /dev/null 2>&1; then
  echo "FAIL: response.capture.artifacts is null"
  exit 1
fi
echo "PASS: response.capture.artifacts exists"

# Check above_the_fold
if echo "$BODY" | jq -e '.capture.artifacts.above_the_fold == null' > /dev/null 2>&1; then
  echo "FAIL: response.capture.artifacts.above_the_fold is null"
  exit 1
fi
echo "PASS: response.capture.artifacts.above_the_fold exists"

# Check desktop
DESKTOP_URL=$(echo "$BODY" | jq -r '.capture.artifacts.above_the_fold.desktop.url // empty')
DESKTOP_DATA_URI=$(echo "$BODY" | jq -r '.capture.artifacts.above_the_fold.desktop.data_uri // empty')

if [ -z "$DESKTOP_URL" ] && [ -z "$DESKTOP_DATA_URI" ]; then
  echo "FAIL: desktop has neither url nor data_uri"
  exit 1
fi

if [ -n "$DESKTOP_URL" ]; then
  echo "PASS: desktop.url = $DESKTOP_URL"
fi
if [ -n "$DESKTOP_DATA_URI" ]; then
  echo "PASS: desktop.data_uri exists (length: ${#DESKTOP_DATA_URI})"
fi

# Check mobile
MOBILE_URL=$(echo "$BODY" | jq -r '.capture.artifacts.above_the_fold.mobile.url // empty')
MOBILE_DATA_URI=$(echo "$BODY" | jq -r '.capture.artifacts.above_the_fold.mobile.data_uri // empty')

if [ -z "$MOBILE_URL" ] && [ -z "$MOBILE_DATA_URI" ]; then
  echo "FAIL: mobile has neither url nor data_uri"
  exit 1
fi

if [ -n "$MOBILE_URL" ]; then
  echo "PASS: mobile.url = $MOBILE_URL"
fi
if [ -n "$MOBILE_DATA_URI" ]; then
  echo "PASS: mobile.data_uri exists (length: ${#MOBILE_DATA_URI})"
fi

echo ""
echo "============================================================"
echo "All checks passed!"
exit 0

