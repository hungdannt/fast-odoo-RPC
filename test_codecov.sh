#!/bin/bash
# Test script to verify Codecov upload

echo "🧪 Testing Codecov upload..."

# Check if coverage.xml exists
if [ ! -f "coverage.xml" ]; then
    echo "❌ coverage.xml not found. Running tests first..."
    make test-coverage
fi

# Test upload
echo "📤 Testing upload to Codecov..."
codecov -f coverage.xml -t 35c1eecb-cf87-4f07-900a-56b2a0d9790d --slug tuanle96/zenoo-rpc

echo "✅ Test completed!"
