#!/bin/bash

# Setup Redis for testing
echo "🚀 Setting up Redis for OdooFlow testing..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Start Redis test container
echo "📦 Starting Redis test container..."
docker-compose -f docker-compose.test.yml up -d redis-test

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
timeout=30
counter=0

while [ $counter -lt $timeout ]; do
    if docker exec odooflow-redis-test redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is ready!"
        break
    fi
    
    echo "⏳ Waiting for Redis... ($counter/$timeout)"
    sleep 1
    counter=$((counter + 1))
done

if [ $counter -eq $timeout ]; then
    echo "❌ Redis failed to start within $timeout seconds"
    docker-compose -f docker-compose.test.yml logs redis-test
    exit 1
fi

# Show Redis info
echo "📊 Redis test instance info:"
echo "   Host: localhost"
echo "   Port: 6380"
echo "   URL: redis://localhost:6380/0"

# Test connection
echo "🔍 Testing Redis connection..."
if docker exec odooflow-redis-test redis-cli set test-key "test-value" > /dev/null 2>&1; then
    if [ "$(docker exec odooflow-redis-test redis-cli get test-key)" = "test-value" ]; then
        echo "✅ Redis connection test successful!"
        docker exec odooflow-redis-test redis-cli del test-key > /dev/null 2>&1
    else
        echo "❌ Redis connection test failed (get)"
        exit 1
    fi
else
    echo "❌ Redis connection test failed (set)"
    exit 1
fi

echo "🎉 Redis test setup complete!"
echo ""
echo "To run tests with Redis:"
echo "  python -m pytest tests/test_cache_comprehensive.py::TestRedisCache -v"
echo ""
echo "To stop Redis test container:"
echo "  docker-compose -f docker-compose.test.yml down"
