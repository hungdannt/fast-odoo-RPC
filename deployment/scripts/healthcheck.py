#!/usr/bin/env python3
"""
Health check script for Zenoo-RPC production deployment.

This script performs comprehensive health checks for:
- Application server health
- Database connectivity
- Redis cache connectivity
- Component integration status
"""

import asyncio
import sys
import os
import time
import json
from typing import Dict, Any, List
import httpx
import asyncpg
import redis.asyncio as redis


class HealthChecker:
    """Comprehensive health checker for Zenoo-RPC."""
    
    def __init__(self):
        self.app_url = os.getenv("APP_URL", "http://localhost:8000")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.timeout = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
        
    async def check_application_health(self) -> Dict[str, Any]:
        """Check application server health."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.app_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "details": response.json() if response.content else {}
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                        "details": response.text[:200]
                    }
                    
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Application server unreachable"
            }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations."""
        if not self.database_url:
            return {
                "status": "skipped",
                "details": "Database URL not configured"
            }
        
        try:
            start_time = time.time()
            
            # Test connection
            conn = await asyncpg.connect(self.database_url)
            
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            
            # Test transaction
            async with conn.transaction():
                await conn.fetchval("SELECT NOW()")
            
            await conn.close()
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "details": {
                    "query_result": result,
                    "transaction_test": "passed"
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Database connection failed"
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and basic operations."""
        try:
            start_time = time.time()
            
            # Create Redis client
            redis_client = redis.from_url(self.redis_url)
            
            # Test ping
            ping_result = await redis_client.ping()
            
            # Test set/get operations
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            await redis_client.set(test_key, test_value, ex=60)
            retrieved_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Get Redis info
            info = await redis_client.info()
            
            await redis_client.close()
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "details": {
                    "ping": ping_result,
                    "set_get_test": retrieved_value.decode() == test_value,
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown")
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Redis connection failed"
            }
    
    async def check_component_integration(self) -> Dict[str, Any]:
        """Check component integration health."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test metrics endpoint
                metrics_response = await client.get(f"{self.app_url}/metrics")
                metrics_healthy = metrics_response.status_code == 200
                
                # Test ready endpoint
                ready_response = await client.get(f"{self.app_url}/ready")
                ready_healthy = ready_response.status_code == 200
                
                return {
                    "status": "healthy" if metrics_healthy and ready_healthy else "degraded",
                    "details": {
                        "metrics_endpoint": "healthy" if metrics_healthy else "unhealthy",
                        "ready_endpoint": "healthy" if ready_healthy else "unhealthy"
                    }
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Component integration check failed"
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        start_time = time.time()
        
        # Run all checks concurrently
        app_check, db_check, redis_check, integration_check = await asyncio.gather(
            self.check_application_health(),
            self.check_database_health(),
            self.check_redis_health(),
            self.check_component_integration(),
            return_exceptions=True
        )
        
        total_time = time.time() - start_time
        
        # Determine overall health status
        checks = {
            "application": app_check if not isinstance(app_check, Exception) else {"status": "error", "error": str(app_check)},
            "database": db_check if not isinstance(db_check, Exception) else {"status": "error", "error": str(db_check)},
            "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "error", "error": str(redis_check)},
            "integration": integration_check if not isinstance(integration_check, Exception) else {"status": "error", "error": str(integration_check)}
        }
        
        # Calculate overall status
        statuses = [check["status"] for check in checks.values()]
        
        if all(status == "healthy" for status in statuses):
            overall_status = "healthy"
        elif any(status == "healthy" for status in statuses):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "total_check_time": total_time,
            "checks": checks,
            "summary": {
                "healthy": sum(1 for s in statuses if s == "healthy"),
                "unhealthy": sum(1 for s in statuses if s == "unhealthy"),
                "degraded": sum(1 for s in statuses if s == "degraded"),
                "skipped": sum(1 for s in statuses if s == "skipped"),
                "error": sum(1 for s in statuses if s == "error")
            }
        }


async def main():
    """Main health check function."""
    checker = HealthChecker()
    
    try:
        result = await checker.run_all_checks()
        
        # Print result as JSON
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["status"] == "healthy":
            sys.exit(0)
        elif result["status"] == "degraded":
            sys.exit(1)  # Warning
        else:
            sys.exit(2)  # Critical
            
    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": time.time(),
            "error": str(e),
            "details": "Health check script failed"
        }
        
        print(json.dumps(error_result, indent=2))
        sys.exit(3)  # Unknown


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import httpx
        import asyncpg
        import redis.asyncio
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install: pip install httpx asyncpg redis")
        sys.exit(4)
    
    # Run health check
    asyncio.run(main())
