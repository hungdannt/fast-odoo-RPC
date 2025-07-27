#!/bin/bash
# Upload coverage to Codecov
# Usage: ./scripts/upload_coverage.sh

set -e

echo "🧪 Running tests with coverage..."

# Run tests with coverage
python -m pytest tests/ \
    --cov=src/zenoo_rpc \
    --cov-report=xml \
    --cov-report=term-missing \
    --cov-report=html \
    --ignore=tests/performance/test_zenoo_vs_odoorpc_benchmark.py \
    --tb=short \
    -q

echo "📊 Coverage report generated:"
echo "  - XML: coverage.xml"
echo "  - HTML: htmlcov/index.html"
echo "  - Terminal: displayed above"

# Check if codecov is installed
if ! command -v codecov &> /dev/null; then
    echo "⚠️  codecov not found. Installing..."
    pip install codecov
fi

# Upload to codecov if coverage.xml exists
if [ -f "coverage.xml" ]; then
    echo "📤 Uploading coverage to Codecov..."
    codecov -f coverage.xml -t $CODECOV_TOKEN
    echo "✅ Coverage uploaded successfully!"
else
    echo "❌ coverage.xml not found. Coverage upload skipped."
    exit 1
fi

echo "🎉 Coverage process completed!"
echo "📈 View your coverage report at: https://codecov.io/gh/tuanle96/zenoo-rpc"
