# Scheduled Tasks and Job Management

A comprehensive example demonstrating how to implement scheduled tasks, job management, and background processing using Zenoo RPC with various scheduling patterns and monitoring capabilities.

## Overview

This example shows how to:

- Implement cron-like scheduled tasks
- Create recurring background jobs
- Manage task queues and priorities
- Monitor job execution and performance
- Handle task failures and retries
- Integrate with external schedulers

## Complete Implementation

### Task Scheduler Service

```python
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from enum import Enum
import uuid
import croniter
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q
from zenoo_rpc.batch.manager import BatchManager

class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    """Task execution status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    task_id: str
    name: str
    description: str
    handler_name: str
    schedule: str  # cron expression or interval
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    timeout_seconds: int = 300
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0

@dataclass
class TaskExecution:
    """Task execution instance."""
    execution_id: str
    task_id: str
    status: TaskStatus = TaskStatus.SCHEDULED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class TaskScheduler:
    """Advanced task scheduler with cron support and job management."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.tasks: Dict[str, ScheduledTask] = {}
        self.executions: Dict[str, TaskExecution] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._register_default_handlers()
    
    def register_task(self, task: ScheduledTask):
        """Register a new scheduled task."""
        # Calculate next run time
        task.next_run = self._calculate_next_run(task.schedule)
        self.tasks[task.task_id] = task
        print(f"Registered task: {task.name} (next run: {task.next_run})")
    
    def register_handler(self, handler_name: str, handler: Callable):
        """Register a task handler function."""
        self.task_handlers[handler_name] = handler
    
    async def start_scheduler(self):
        """Start the task scheduler."""
        if self.running:
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        print("Task scheduler started")
    
    async def stop_scheduler(self):
        """Stop the task scheduler."""
        self.running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        print("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Find tasks ready to run
                ready_tasks = []
                for task in self.tasks.values():
                    if (task.enabled and 
                        task.next_run and 
                        task.next_run <= current_time):
                        ready_tasks.append(task)
                
                # Execute ready tasks
                if ready_tasks:
                    # Sort by priority
                    ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
                    
                    # Execute tasks concurrently (with limit)
                    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent tasks
                    await asyncio.gather(*[
                        self._execute_task_with_semaphore(task, semaphore)
                        for task in ready_tasks
                    ])
                
                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _execute_task_with_semaphore(self, task: ScheduledTask, semaphore: asyncio.Semaphore):
        """Execute task with concurrency control."""
        async with semaphore:
            await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        execution_id = str(uuid.uuid4())
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            started_at=datetime.now()
        )
        
        self.executions[execution_id] = execution
        
        try:
            execution.status = TaskStatus.RUNNING
            print(f"Executing task: {task.name}")
            
            # Get handler
            if task.handler_name not in self.task_handlers:
                raise Exception(f"Handler not found: {task.handler_name}")
            
            handler = self.task_handlers[task.handler_name]
            
            # Execute with timeout
            start_time = datetime.now()
            result = await asyncio.wait_for(
                handler(task, self.client),
                timeout=task.timeout_seconds
            )
            end_time = datetime.now()
            
            # Update execution
            execution.status = TaskStatus.COMPLETED
            execution.completed_at = end_time
            execution.duration = (end_time - start_time).total_seconds()
            execution.result = result
            
            # Update task
            task.last_run = start_time
            task.next_run = self._calculate_next_run(task.schedule, start_time)
            task.run_count += 1
            
            print(f"Task completed: {task.name} (duration: {execution.duration:.2f}s)")
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.retry_count += 1
            
            task.failure_count += 1
            
            print(f"Task failed: {task.name} - {e}")
            
            # Schedule retry if possible
            if execution.retry_count < task.max_retries:
                execution.status = TaskStatus.RETRYING
                # Schedule retry with exponential backoff
                retry_delay = 2 ** execution.retry_count * 60  # 1, 2, 4 minutes
                task.next_run = datetime.now() + timedelta(seconds=retry_delay)
                print(f"Task will retry in {retry_delay} seconds")
            else:
                # Calculate next regular run
                task.next_run = self._calculate_next_run(task.schedule)
    
    def _calculate_next_run(self, schedule: str, base_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time based on schedule."""
        if base_time is None:
            base_time = datetime.now()
        
        if schedule.startswith("interval:"):
            # Interval-based schedule (e.g., "interval:300" for 5 minutes)
            interval_seconds = int(schedule.split(":")[1])
            return base_time + timedelta(seconds=interval_seconds)
        
        elif schedule.startswith("daily:"):
            # Daily at specific time (e.g., "daily:08:30")
            time_str = schedule.split(":")[1] + ":" + schedule.split(":")[2]
            target_time = datetime.strptime(time_str, "%H:%M").time()
            
            next_run = datetime.combine(base_time.date(), target_time)
            if next_run <= base_time:
                next_run += timedelta(days=1)
            
            return next_run
        
        else:
            # Cron expression
            try:
                cron = croniter.croniter(schedule, base_time)
                return cron.get_next(datetime)
            except:
                # Fallback to hourly
                return base_time + timedelta(hours=1)
    
    def _register_default_handlers(self):
        """Register default task handlers."""
        
        self.register_handler("data_cleanup", self._handle_data_cleanup)
        self.register_handler("backup_data", self._handle_backup_data)
        self.register_handler("generate_reports", self._handle_generate_reports)
        self.register_handler("sync_customers", self._handle_sync_customers)
        self.register_handler("send_notifications", self._handle_send_notifications)
        self.register_handler("health_check", self._handle_health_check)
        self.register_handler("cache_warmup", self._handle_cache_warmup)
    
    async def _handle_data_cleanup(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle data cleanup task."""
        params = task.parameters
        days_old = params.get("days_old", 30)
        
        # Delete old records
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Example: Clean up old log entries (if you have a log model)
        deleted_count = 0
        
        # In a real implementation, you would delete old records
        print(f"Cleaning up data older than {days_old} days")
        
        return {
            "deleted_records": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    async def _handle_backup_data(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle data backup task."""
        params = task.parameters
        backup_type = params.get("type", "incremental")
        
        # Example backup logic
        print(f"Starting {backup_type} backup")
        
        # Get data to backup
        customers = await client.model(ResPartner).filter(
            customer_rank__gt=0
        ).limit(1000).all()
        
        orders = await client.model(SaleOrder).filter(
            state__in=["sale", "done"]
        ).limit(1000).all()
        
        # Simulate backup process
        await asyncio.sleep(2)
        
        return {
            "backup_type": backup_type,
            "customers_backed_up": len(customers),
            "orders_backed_up": len(orders),
            "backup_size_mb": len(customers) * 0.1 + len(orders) * 0.2
        }
    
    async def _handle_generate_reports(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle report generation task."""
        params = task.parameters
        report_type = params.get("type", "daily_sales")
        
        if report_type == "daily_sales":
            # Generate daily sales report
            today = datetime.now().date()
            orders = await client.model(SaleOrder).filter(
                Q(date_order__gte=today) &
                Q(state__in=["sale", "done"])
            ).all()
            
            total_revenue = sum(order.amount_total for order in orders)
            
            report_data = {
                "date": today.isoformat(),
                "total_orders": len(orders),
                "total_revenue": float(total_revenue),
                "average_order_value": float(total_revenue / len(orders)) if orders else 0
            }
            
        elif report_type == "customer_summary":
            # Generate customer summary report
            customers = await client.model(ResPartner).filter(
                customer_rank__gt=0
            ).all()
            
            companies = sum(1 for c in customers if c.is_company)
            individuals = len(customers) - companies
            
            report_data = {
                "total_customers": len(customers),
                "companies": companies,
                "individuals": individuals
            }
        
        else:
            report_data = {"error": f"Unknown report type: {report_type}"}
        
        print(f"Generated {report_type} report")
        return report_data
    
    async def _handle_sync_customers(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle customer synchronization task."""
        params = task.parameters
        source_system = params.get("source", "external_crm")
        
        # Simulate external system sync
        print(f"Syncing customers from {source_system}")
        
        # In a real implementation, this would:
        # 1. Fetch data from external system
        # 2. Compare with existing data
        # 3. Update/create records as needed
        
        # Simulate processing
        await asyncio.sleep(3)
        
        return {
            "source_system": source_system,
            "customers_synced": 25,
            "new_customers": 5,
            "updated_customers": 20
        }
    
    async def _handle_send_notifications(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle notification sending task."""
        params = task.parameters
        notification_type = params.get("type", "daily_summary")
        
        if notification_type == "daily_summary":
            # Send daily summary to managers
            today = datetime.now().date()
            
            # Get today's metrics
            orders = await client.model(SaleOrder).filter(
                Q(date_order__gte=today) &
                Q(state__in=["sale", "done"])
            ).all()
            
            new_customers = await client.model(ResPartner).filter(
                Q(create_date__gte=today) &
                Q(customer_rank__gt=0)
            ).count()
            
            summary = {
                "date": today.isoformat(),
                "orders": len(orders),
                "revenue": sum(order.amount_total for order in orders),
                "new_customers": new_customers
            }
            
            # Simulate sending notification
            print(f"Sending daily summary: {summary}")
            
            return {"notification_sent": True, "summary": summary}
        
        return {"notification_sent": False, "reason": "Unknown notification type"}
    
    async def _handle_health_check(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle system health check task."""
        
        health_status = {"overall": "healthy", "checks": {}}
        
        try:
            # Test database connection
            start_time = datetime.now()
            test_query = await client.model(ResPartner).limit(1).all()
            db_response_time = (datetime.now() - start_time).total_seconds()
            
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time": db_response_time
            }
            
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["overall"] = "unhealthy"
        
        # Check cache if available
        if hasattr(client, 'cache'):
            try:
                # Test cache operation
                cache_key = "health_check_test"
                await client.cache.set(cache_key, "test_value")
                cached_value = await client.cache.get(cache_key)
                
                health_status["checks"]["cache"] = {
                    "status": "healthy" if cached_value == "test_value" else "degraded"
                }
                
            except Exception as e:
                health_status["checks"]["cache"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_status
    
    async def _handle_cache_warmup(self, task: ScheduledTask, client: ZenooClient) -> Dict[str, Any]:
        """Handle cache warmup task."""
        
        warmed_items = 0
        
        # Warm up frequently accessed data
        try:
            # Cache top customers
            top_customers = await (
                client.model(ResPartner)
                .filter(customer_rank__gt=0)
                .only("name", "email")
                .limit(100)
                .cache(ttl=3600)
                .all()
            )
            warmed_items += len(top_customers)
            
            # Cache recent orders
            recent_orders = await (
                client.model(SaleOrder)
                .filter(state__in=["sale", "done"])
                .only("name", "partner_id", "amount_total")
                .limit(100)
                .cache(ttl=1800)
                .all()
            )
            warmed_items += len(recent_orders)
            
        except Exception as e:
            return {"error": str(e), "warmed_items": warmed_items}
        
        return {"warmed_items": warmed_items}
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and statistics."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        # Get recent executions
        recent_executions = [
            {
                "execution_id": exec.execution_id,
                "status": exec.status.value,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "duration": exec.duration,
                "error_message": exec.error_message
            }
            for exec in self.executions.values()
            if exec.task_id == task_id
        ][-10:]  # Last 10 executions
        
        return {
            "task_id": task_id,
            "name": task.name,
            "enabled": task.enabled,
            "schedule": task.schedule,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "run_count": task.run_count,
            "failure_count": task.failure_count,
            "success_rate": (task.run_count - task.failure_count) / task.run_count * 100 if task.run_count > 0 else 0,
            "recent_executions": recent_executions
        }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get overall scheduler status."""
        total_tasks = len(self.tasks)
        enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
        
        # Calculate next run times
        next_runs = [task.next_run for task in self.tasks.values() if task.next_run and task.enabled]
        next_run = min(next_runs) if next_runs else None
        
        return {
            "running": self.running,
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "next_run": next_run.isoformat() if next_run else None,
            "total_executions": len(self.executions)
        }

# Predefined Task Definitions
def create_default_tasks() -> List[ScheduledTask]:
    """Create default scheduled tasks."""
    
    tasks = [
        ScheduledTask(
            task_id="daily_backup",
            name="Daily Data Backup",
            description="Backup critical data daily at 2 AM",
            handler_name="backup_data",
            schedule="0 2 * * *",  # Daily at 2 AM
            parameters={"type": "incremental"},
            priority=TaskPriority.HIGH
        ),
        ScheduledTask(
            task_id="weekly_cleanup",
            name="Weekly Data Cleanup",
            description="Clean up old data weekly",
            handler_name="data_cleanup",
            schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
            parameters={"days_old": 90},
            priority=TaskPriority.NORMAL
        ),
        ScheduledTask(
            task_id="daily_reports",
            name="Daily Sales Reports",
            description="Generate daily sales reports",
            handler_name="generate_reports",
            schedule="daily:08:00",  # Daily at 8 AM
            parameters={"type": "daily_sales"},
            priority=TaskPriority.NORMAL
        ),
        ScheduledTask(
            task_id="hourly_sync",
            name="Customer Sync",
            description="Sync customers from external CRM",
            handler_name="sync_customers",
            schedule="0 * * * *",  # Every hour
            parameters={"source": "external_crm"},
            priority=TaskPriority.NORMAL
        ),
        ScheduledTask(
            task_id="health_check",
            name="System Health Check",
            description="Check system health every 15 minutes",
            handler_name="health_check",
            schedule="interval:900",  # Every 15 minutes
            priority=TaskPriority.HIGH
        ),
        ScheduledTask(
            task_id="cache_warmup",
            name="Cache Warmup",
            description="Warm up cache with frequently accessed data",
            handler_name="cache_warmup",
            schedule="0 */6 * * *",  # Every 6 hours
            priority=TaskPriority.LOW
        )
    ]
    
    return tasks

# Usage Example
async def main():
    """Demonstrate scheduled task capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize task scheduler
        scheduler = TaskScheduler(client)
        
        # Register default tasks
        for task in create_default_tasks():
            scheduler.register_task(task)
        
        print("📅 Starting task scheduler...")
        
        # Start scheduler
        await scheduler.start_scheduler()
        
        # Let it run for a while
        await asyncio.sleep(30)
        
        # Check scheduler status
        status = scheduler.get_scheduler_status()
        print(f"\n📊 Scheduler Status:")
        print(f"  Running: {status['running']}")
        print(f"  Total Tasks: {status['total_tasks']}")
        print(f"  Enabled Tasks: {status['enabled_tasks']}")
        print(f"  Next Run: {status['next_run']}")
        
        # Check individual task status
        for task_id in ["health_check", "daily_reports"]:
            task_status = scheduler.get_task_status(task_id)
            if task_status:
                print(f"\n📋 Task: {task_status['name']}")
                print(f"  Success Rate: {task_status['success_rate']:.1f}%")
                print(f"  Run Count: {task_status['run_count']}")
                print(f"  Next Run: {task_status['next_run']}")
        
        # Stop scheduler
        await scheduler.stop_scheduler()

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Flexible Scheduling**
- Cron expressions support
- Interval-based scheduling
- Daily time-based scheduling
- Custom schedule patterns

### 2. **Task Management**
- Priority-based execution
- Retry mechanisms with backoff
- Timeout handling
- Concurrency control

### 3. **Monitoring & Analytics**
- Execution tracking
- Success/failure rates
- Performance metrics
- Health monitoring

### 4. **Business Operations**
- Data backup automation
- Report generation
- System maintenance
- External system sync

### 5. **Scalability Features**
- Concurrent task execution
- Resource management
- Error recovery
- Performance optimization

## Integration Examples

### Web API for Task Management

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/api/tasks")
async def list_tasks():
    """List all scheduled tasks."""
    return {
        task_id: scheduler.get_task_status(task_id)
        for task_id in scheduler.tasks.keys()
    }

@app.post("/api/tasks/{task_id}/enable")
async def enable_task(task_id: str):
    """Enable a scheduled task."""
    if task_id in scheduler.tasks:
        scheduler.tasks[task_id].enabled = True
        return {"enabled": True}
    raise HTTPException(404, "Task not found")

@app.post("/api/tasks/{task_id}/disable")
async def disable_task(task_id: str):
    """Disable a scheduled task."""
    if task_id in scheduler.tasks:
        scheduler.tasks[task_id].enabled = False
        return {"enabled": False}
    raise HTTPException(404, "Task not found")
```

### Celery Integration

```python
from celery import Celery

celery_app = Celery('tasks')

@celery_app.task
def run_scheduled_task(task_id: str):
    """Run a scheduled task via Celery."""
    asyncio.run(scheduler._execute_task(scheduler.tasks[task_id]))

# Schedule tasks with Celery Beat
celery_app.conf.beat_schedule = {
    'daily-backup': {
        'task': 'run_scheduled_task',
        'schedule': crontab(hour=2, minute=0),
        'args': ('daily_backup',)
    }
}
```

## Next Steps

- [Email Automation](email-automation.md) - Email scheduling and automation
- [Document Processing](document-processing.md) - Automated document workflows
- [Performance Metrics](performance-metrics.md) - Monitor task performance
