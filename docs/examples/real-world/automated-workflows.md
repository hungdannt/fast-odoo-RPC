# Automated Workflows and Business Process Automation

A comprehensive example demonstrating how to build automated workflows and business process automation using Zenoo RPC with event-driven architecture, task scheduling, and integration patterns.

## Overview

This example shows how to:

- Create event-driven automated workflows
- Implement business process automation
- Schedule recurring tasks and jobs
- Handle workflow state management
- Integrate with external systems
- Monitor and track workflow execution

## Complete Implementation

### Workflow Engine Service

```python
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q
from zenoo_rpc.batch.manager import BatchManager

class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    """Individual task status."""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WorkflowTask:
    """Individual workflow task definition."""
    task_id: str
    name: str
    task_type: str  # action, condition, delay, notification
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    status: TaskStatus = TaskStatus.WAITING
    result: Optional[Any] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class WorkflowDefinition:
    """Workflow definition with tasks and configuration."""
    workflow_id: str
    name: str
    description: str
    tasks: List[WorkflowTask]
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    schedule: Optional[str] = None  # cron expression
    enabled: bool = True
    version: str = "1.0"

@dataclass
class WorkflowExecution:
    """Workflow execution instance."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    task_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

class WorkflowEngine:
    """Automated workflow engine for business process automation."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.running = False
        self._register_default_handlers()
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a new workflow definition."""
        self.workflows[workflow.workflow_id] = workflow
        print(f"Registered workflow: {workflow.name} ({workflow.workflow_id})")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a task handler function."""
        self.task_handlers[task_type] = handler
    
    async def start_workflow(
        self, 
        workflow_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a workflow execution."""
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        if not workflow.enabled:
            raise ValueError(f"Workflow {workflow_id} is disabled")
        
        # Create execution instance
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            started_at=datetime.now(),
            context=context or {}
        )
        
        self.executions[execution_id] = execution
        
        # Start execution in background
        asyncio.create_task(self._execute_workflow(execution))
        
        return execution_id
    
    async def _execute_workflow(self, execution: WorkflowExecution):
        """Execute a workflow instance."""
        
        try:
            execution.status = WorkflowStatus.RUNNING
            workflow = self.workflows[execution.workflow_id]
            
            print(f"Starting workflow execution: {execution.execution_id}")
            
            # Execute tasks based on dependencies
            completed_tasks = set()
            
            while len(completed_tasks) < len(workflow.tasks):
                # Find tasks ready to execute
                ready_tasks = []
                for task in workflow.tasks:
                    if (task.task_id not in completed_tasks and 
                        task.status in [TaskStatus.WAITING, TaskStatus.FAILED] and
                        all(dep in completed_tasks for dep in task.dependencies)):
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    # Check if we're stuck
                    remaining_tasks = [t for t in workflow.tasks if t.task_id not in completed_tasks]
                    if remaining_tasks:
                        raise Exception(f"Workflow stuck - no ready tasks. Remaining: {[t.task_id for t in remaining_tasks]}")
                    break
                
                # Execute ready tasks concurrently
                await asyncio.gather(*[
                    self._execute_task(task, execution)
                    for task in ready_tasks
                ])
                
                # Update completed tasks
                for task in ready_tasks:
                    if task.status == TaskStatus.COMPLETED:
                        completed_tasks.add(task.task_id)
                    elif task.status == TaskStatus.FAILED and task.retry_count >= task.max_retries:
                        # Task failed permanently
                        execution.status = WorkflowStatus.FAILED
                        execution.error_message = f"Task {task.task_id} failed: {task.error_message}"
                        execution.completed_at = datetime.now()
                        return
            
            # All tasks completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            print(f"Workflow execution completed: {execution.execution_id}")
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            print(f"Workflow execution failed: {execution.execution_id} - {e}")
    
    async def _execute_task(self, task: WorkflowTask, execution: WorkflowExecution):
        """Execute an individual task."""
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            print(f"Executing task: {task.name} ({task.task_id})")
            
            # Get task handler
            if task.task_type not in self.task_handlers:
                raise Exception(f"No handler registered for task type: {task.task_type}")
            
            handler = self.task_handlers[task.task_type]
            
            # Execute task with timeout
            try:
                result = await asyncio.wait_for(
                    handler(task, execution, self.client),
                    timeout=task.timeout_seconds
                )
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                
                # Store result in execution context
                execution.task_results[task.task_id] = result
                
                print(f"Task completed: {task.name}")
                
            except asyncio.TimeoutError:
                raise Exception(f"Task timed out after {task.timeout_seconds} seconds")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            
            print(f"Task failed: {task.name} - {e}")
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                print(f"Retrying task: {task.name} (attempt {task.retry_count + 1})")
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                task.status = TaskStatus.WAITING
    
    def _register_default_handlers(self):
        """Register default task handlers."""
        
        self.register_task_handler("create_record", self._handle_create_record)
        self.register_task_handler("update_record", self._handle_update_record)
        self.register_task_handler("send_email", self._handle_send_email)
        self.register_task_handler("condition", self._handle_condition)
        self.register_task_handler("delay", self._handle_delay)
        self.register_task_handler("batch_operation", self._handle_batch_operation)
        self.register_task_handler("notification", self._handle_notification)
    
    async def _handle_create_record(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle record creation task."""
        params = task.parameters
        model_name = params.get("model")
        data = params.get("data", {})
        
        # Substitute context variables
        data = self._substitute_context_variables(data, execution.context)
        
        if model_name == "res.partner":
            record = await client.model(ResPartner).create(data)
        elif model_name == "sale.order":
            record = await client.model(SaleOrder).create(data)
        else:
            # Generic model creation
            record = await client.model(model_name).create(data)
        
        return {"record_id": record.id, "model": model_name}
    
    async def _handle_update_record(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle record update task."""
        params = task.parameters
        model_name = params.get("model")
        record_id = params.get("record_id")
        data = params.get("data", {})
        
        # Substitute context variables
        data = self._substitute_context_variables(data, execution.context)
        record_id = self._substitute_context_variables(record_id, execution.context)
        
        if model_name == "res.partner":
            await client.model(ResPartner).update(record_id, data)
        elif model_name == "sale.order":
            await client.model(SaleOrder).update(record_id, data)
        else:
            # Generic model update
            await client.model(model_name).update(record_id, data)
        
        return {"updated": True, "record_id": record_id}
    
    async def _handle_send_email(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle email sending task."""
        params = task.parameters
        
        # In a real implementation, this would integrate with an email service
        email_data = {
            "to": params.get("to"),
            "subject": params.get("subject"),
            "body": params.get("body"),
            "template": params.get("template")
        }
        
        # Substitute context variables
        email_data = self._substitute_context_variables(email_data, execution.context)
        
        print(f"Sending email to {email_data['to']}: {email_data['subject']}")
        
        # Simulate email sending
        await asyncio.sleep(1)
        
        return {"email_sent": True, "recipient": email_data["to"]}
    
    async def _handle_condition(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle conditional logic task."""
        params = task.parameters
        condition_type = params.get("type")
        
        if condition_type == "record_exists":
            model_name = params.get("model")
            filters = params.get("filters", {})
            
            # Substitute context variables
            filters = self._substitute_context_variables(filters, execution.context)
            
            # Check if record exists
            if model_name == "res.partner":
                record = await client.model(ResPartner).filter(**filters).first()
            else:
                record = await client.model(model_name).filter(**filters).first()
            
            result = record is not None
            
        elif condition_type == "value_comparison":
            left_value = self._substitute_context_variables(params.get("left"), execution.context)
            right_value = self._substitute_context_variables(params.get("right"), execution.context)
            operator = params.get("operator", "eq")
            
            if operator == "eq":
                result = left_value == right_value
            elif operator == "gt":
                result = left_value > right_value
            elif operator == "lt":
                result = left_value < right_value
            else:
                result = False
        else:
            result = False
        
        return {"condition_result": result}
    
    async def _handle_delay(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle delay task."""
        delay_seconds = task.parameters.get("seconds", 1)
        await asyncio.sleep(delay_seconds)
        return {"delayed": delay_seconds}
    
    async def _handle_batch_operation(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle batch operations task."""
        params = task.parameters
        operations = params.get("operations", [])
        
        async with client.batch() as batch:
            for operation in operations:
                op_type = operation.get("type")
                model = operation.get("model")
                data = self._substitute_context_variables(operation.get("data", {}), execution.context)
                
                if op_type == "create":
                    batch.create(model, data)
                elif op_type == "update":
                    record_ids = operation.get("record_ids", [])
                    batch.update(model, data, record_ids)
        
        results = await batch.execute()
        return {"batch_results": results}
    
    async def _handle_notification(self, task: WorkflowTask, execution: WorkflowExecution, client: ZenooClient):
        """Handle notification task."""
        params = task.parameters
        message = self._substitute_context_variables(params.get("message"), execution.context)
        
        print(f"Notification: {message}")
        
        # In a real implementation, this could send to Slack, Teams, etc.
        return {"notification_sent": True, "message": message}
    
    def _substitute_context_variables(self, value: Any, context: Dict[str, Any]) -> Any:
        """Substitute context variables in values."""
        if isinstance(value, str):
            # Simple variable substitution
            for key, val in context.items():
                value = value.replace(f"{{{key}}}", str(val))
            return value
        elif isinstance(value, dict):
            return {k: self._substitute_context_variables(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._substitute_context_variables(item, context) for item in value]
        else:
            return value
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status."""
        if execution_id not in self.executions:
            return None
        
        execution = self.executions[execution_id]
        workflow = self.workflows[execution.workflow_id]
        
        return {
            "execution_id": execution_id,
            "workflow_name": workflow.name,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "task_status": [
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "retry_count": task.retry_count
                }
                for task in workflow.tasks
            ],
            "error_message": execution.error_message
        }

# Predefined Workflow Examples
def create_customer_onboarding_workflow() -> WorkflowDefinition:
    """Create a customer onboarding workflow."""
    
    tasks = [
        WorkflowTask(
            task_id="validate_customer",
            name="Validate Customer Data",
            task_type="condition",
            parameters={
                "type": "record_exists",
                "model": "res.partner",
                "filters": {"email": "{customer_email}"}
            }
        ),
        WorkflowTask(
            task_id="create_customer",
            name="Create Customer Record",
            task_type="create_record",
            dependencies=["validate_customer"],
            parameters={
                "model": "res.partner",
                "data": {
                    "name": "{customer_name}",
                    "email": "{customer_email}",
                    "customer_rank": 1
                }
            }
        ),
        WorkflowTask(
            task_id="send_welcome_email",
            name="Send Welcome Email",
            task_type="send_email",
            dependencies=["create_customer"],
            parameters={
                "to": "{customer_email}",
                "subject": "Welcome to Our Platform!",
                "body": "Dear {customer_name}, welcome to our platform!"
            }
        ),
        WorkflowTask(
            task_id="notify_sales_team",
            name="Notify Sales Team",
            task_type="notification",
            dependencies=["create_customer"],
            parameters={
                "message": "New customer onboarded: {customer_name} ({customer_email})"
            }
        )
    ]
    
    return WorkflowDefinition(
        workflow_id="customer_onboarding",
        name="Customer Onboarding Process",
        description="Automated workflow for onboarding new customers",
        tasks=tasks
    )

def create_order_processing_workflow() -> WorkflowDefinition:
    """Create an order processing workflow."""
    
    tasks = [
        WorkflowTask(
            task_id="validate_order",
            name="Validate Order Data",
            task_type="condition",
            parameters={
                "type": "value_comparison",
                "left": "{order_amount}",
                "operator": "gt",
                "right": 0
            }
        ),
        WorkflowTask(
            task_id="create_order",
            name="Create Sales Order",
            task_type="create_record",
            dependencies=["validate_order"],
            parameters={
                "model": "sale.order",
                "data": {
                    "partner_id": "{customer_id}",
                    "amount_total": "{order_amount}"
                }
            }
        ),
        WorkflowTask(
            task_id="send_confirmation",
            name="Send Order Confirmation",
            task_type="send_email",
            dependencies=["create_order"],
            parameters={
                "to": "{customer_email}",
                "subject": "Order Confirmation",
                "body": "Your order has been confirmed. Amount: ${order_amount}"
            }
        )
    ]
    
    return WorkflowDefinition(
        workflow_id="order_processing",
        name="Order Processing Workflow",
        description="Automated workflow for processing new orders",
        tasks=tasks
    )

# Usage Example
async def main():
    """Demonstrate automated workflow capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize workflow engine
        engine = WorkflowEngine(client)
        
        # Register workflows
        engine.register_workflow(create_customer_onboarding_workflow())
        engine.register_workflow(create_order_processing_workflow())
        
        print("🔄 Starting automated workflows...")
        
        # Start customer onboarding workflow
        onboarding_execution = await engine.start_workflow(
            "customer_onboarding",
            context={
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com"
            }
        )
        
        # Start order processing workflow
        order_execution = await engine.start_workflow(
            "order_processing",
            context={
                "customer_id": 1,
                "customer_email": "customer@example.com",
                "order_amount": 1500.00
            }
        )
        
        # Wait for workflows to complete
        await asyncio.sleep(10)
        
        # Check execution status
        onboarding_status = engine.get_execution_status(onboarding_execution)
        order_status = engine.get_execution_status(order_execution)
        
        print(f"\n📊 Workflow Results:")
        print(f"Customer Onboarding: {onboarding_status['status']}")
        print(f"Order Processing: {order_status['status']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Event-Driven Architecture**
- Task dependency management
- Asynchronous execution
- Event-based triggers

### 2. **Business Process Automation**
- Customer onboarding workflows
- Order processing automation
- Notification systems

### 3. **Workflow Management**
- State tracking and monitoring
- Error handling and retries
- Conditional logic support

### 4. **Integration Capabilities**
- Email automation
- External system notifications
- Batch operations

### 5. **Scalability Features**
- Concurrent task execution
- Resource management
- Performance monitoring

## Integration Examples

### Webhook Triggers

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/customer-signup")
async def customer_signup_webhook(request: Request):
    """Webhook endpoint for customer signup events."""
    data = await request.json()
    
    # Start customer onboarding workflow
    execution_id = await engine.start_workflow(
        "customer_onboarding",
        context={
            "customer_name": data["name"],
            "customer_email": data["email"]
        }
    )
    
    return {"workflow_started": execution_id}
```

### Scheduled Workflows

```python
import schedule
import time

def schedule_daily_reports():
    """Schedule daily report generation workflow."""
    asyncio.create_task(engine.start_workflow(
        "daily_reports",
        context={"date": datetime.now().strftime("%Y-%m-%d")}
    ))

schedule.every().day.at("08:00").do(schedule_daily_reports)
```

## Next Steps

- [Scheduled Tasks](scheduled-tasks.md) - Advanced task scheduling
- [Email Automation](email-automation.md) - Email workflow integration
- [Document Processing](document-processing.md) - Document workflow automation
