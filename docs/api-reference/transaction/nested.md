# Nested Transactions

Support for nested transactions and savepoints in Zenoo RPC.

## Overview

Nested transactions provide:
- Savepoint management
- Partial rollback capabilities
- Hierarchical transaction structure
- Fine-grained error recovery

## Savepoints

### Creating Savepoints

```python
async def create_savepoints():
    """Demonstrate savepoint creation and usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Create initial data
            partner = await client.model("res.partner").create({
                "name": "Savepoint Test Partner"
            })
            
            # Create savepoint before risky operations
            savepoint1 = await tx.create_savepoint("before_product_creation")
            
            try:
                # Risky operation that might fail
                product = await client.model("product.product").create({
                    "name": "Test Product",
                    "list_price": 100.0
                })
                
                # Create another savepoint
                savepoint2 = await tx.create_savepoint("before_order_creation")
                
                try:
                    # Another risky operation
                    order = await client.model("sale.order").create({
                        "partner_id": partner.id,
                        "order_line": [(0, 0, {
                            "product_id": product.id,
                            "product_uom_qty": 1
                        })]
                    })
                    
                    print(f"All operations successful: Partner {partner.id}, Product {product.id}, Order {order.id}")
                    
                except Exception as e:
                    print(f"Order creation failed, rolling back to savepoint2: {e}")
                    await tx.rollback_to_savepoint(savepoint2)
                    # Partner and product still exist, only order creation is rolled back
                
            except Exception as e:
                print(f"Product creation failed, rolling back to savepoint1: {e}")
                await tx.rollback_to_savepoint(savepoint1)
                # Only partner exists, product creation is rolled back
```

### Savepoint Management

```python
class SavepointManager:
    """Manager for handling savepoints in transactions."""
    
    def __init__(self, transaction):
        self.transaction = transaction
        self.savepoints = {}
        self.savepoint_counter = 0
    
    async def create_named_savepoint(self, name: str) -> str:
        """Create a named savepoint."""
        
        if name in self.savepoints:
            raise ValueError(f"Savepoint '{name}' already exists")
        
        savepoint_id = await self.transaction.create_savepoint(name)
        self.savepoints[name] = savepoint_id
        
        return savepoint_id
    
    async def create_auto_savepoint(self) -> str:
        """Create an automatically named savepoint."""
        
        self.savepoint_counter += 1
        name = f"auto_savepoint_{self.savepoint_counter}"
        
        return await self.create_named_savepoint(name)
    
    async def rollback_to_named_savepoint(self, name: str):
        """Rollback to a named savepoint."""
        
        if name not in self.savepoints:
            raise ValueError(f"Savepoint '{name}' not found")
        
        savepoint_id = self.savepoints[name]
        await self.transaction.rollback_to_savepoint(savepoint_id)
        
        # Remove this savepoint and all later ones
        self._cleanup_savepoints_after(name)
    
    def _cleanup_savepoints_after(self, name: str):
        """Clean up savepoints created after the specified one."""
        
        # In a real implementation, you'd track savepoint order
        # and remove all savepoints created after the specified one
        pass
    
    async def release_savepoint(self, name: str):
        """Release a named savepoint."""
        
        if name not in self.savepoints:
            raise ValueError(f"Savepoint '{name}' not found")
        
        savepoint_id = self.savepoints[name]
        await self.transaction.release_savepoint(savepoint_id)
        
        del self.savepoints[name]
    
    def list_savepoints(self) -> List[str]:
        """List all active savepoints."""
        return list(self.savepoints.keys())

# Usage
async def use_savepoint_manager():
    """Demonstrate savepoint manager usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            manager = SavepointManager(tx)
            
            # Create base data
            partner = await client.model("res.partner").create({
                "name": "Managed Savepoint Partner"
            })
            
            # Create savepoint before batch operations
            await manager.create_named_savepoint("before_batch")
            
            try:
                # Batch operations
                for i in range(5):
                    await manager.create_auto_savepoint()
                    
                    try:
                        product = await client.model("product.product").create({
                            "name": f"Batch Product {i}",
                            "list_price": 10.0 * (i + 1)
                        })
                        
                        print(f"Created product {i}: {product.id}")
                        
                    except Exception as e:
                        print(f"Failed to create product {i}: {e}")
                        # Rollback to the auto savepoint for this iteration
                        await manager.rollback_to_named_savepoint(f"auto_savepoint_{i + 1}")
                
                print(f"Active savepoints: {manager.list_savepoints()}")
                
            except Exception as e:
                print(f"Batch operation failed, rolling back to before_batch: {e}")
                await manager.rollback_to_named_savepoint("before_batch")
```

## Nested Transaction Patterns

### Try-Catch with Savepoints

```python
async def try_catch_with_savepoints():
    """Implement try-catch pattern using savepoints."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            results = []
            
            # Process multiple items with individual error handling
            items_to_process = [
                {"name": "Valid Item 1", "price": 10.0},
                {"name": "", "price": 20.0},  # Invalid - empty name
                {"name": "Valid Item 2", "price": 30.0},
                {"name": "Valid Item 3", "price": -5.0},  # Invalid - negative price
            ]
            
            for i, item_data in enumerate(items_to_process):
                savepoint_name = f"item_{i}"
                savepoint = await tx.create_savepoint(savepoint_name)
                
                try:
                    # Validate item
                    if not item_data.get("name"):
                        raise ValueError("Item name is required")
                    if item_data.get("price", 0) < 0:
                        raise ValueError("Item price cannot be negative")
                    
                    # Create item
                    product = await client.model("product.product").create({
                        "name": item_data["name"],
                        "list_price": item_data["price"]
                    })
                    
                    results.append({
                        "index": i,
                        "status": "success",
                        "product_id": product.id
                    })
                    
                    # Release savepoint on success
                    await tx.release_savepoint(savepoint)
                    
                except Exception as e:
                    # Rollback to savepoint on error
                    await tx.rollback_to_savepoint(savepoint)
                    
                    results.append({
                        "index": i,
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Print results
            for result in results:
                if result["status"] == "success":
                    print(f"Item {result['index']}: Created product {result['product_id']}")
                else:
                    print(f"Item {result['index']}: Failed - {result['error']}")
            
            successful_count = sum(1 for r in results if r["status"] == "success")
            print(f"Successfully processed {successful_count}/{len(items_to_process)} items")
```

### Hierarchical Operations

```python
async def hierarchical_operations():
    """Demonstrate hierarchical operations with nested savepoints."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Level 1: Create company
            company_savepoint = await tx.create_savepoint("company_creation")
            
            try:
                company = await client.model("res.partner").create({
                    "name": "Hierarchical Test Company",
                    "is_company": True
                })
                
                print(f"Created company: {company.id}")
                
                # Level 2: Create departments
                departments_savepoint = await tx.create_savepoint("departments_creation")
                
                try:
                    departments = []
                    for dept_name in ["Sales", "Marketing", "Engineering"]:
                        dept_savepoint = await tx.create_savepoint(f"dept_{dept_name.lower()}")
                        
                        try:
                            dept = await client.model("res.partner").create({
                                "name": f"{company.name} - {dept_name}",
                                "parent_id": company.id,
                                "is_company": False
                            })
                            
                            departments.append(dept)
                            print(f"Created department: {dept.name}")
                            
                            # Level 3: Create employees for each department
                            employees_savepoint = await tx.create_savepoint(f"employees_{dept_name.lower()}")
                            
                            try:
                                for i in range(2):  # 2 employees per department
                                    employee = await client.model("res.partner").create({
                                        "name": f"{dept_name} Employee {i + 1}",
                                        "parent_id": dept.id,
                                        "is_company": False
                                    })
                                    
                                    print(f"Created employee: {employee.name}")
                                
                                # Simulate potential failure for Engineering department
                                if dept_name == "Engineering":
                                    # Uncomment to test rollback
                                    # raise ValueError("Engineering department setup failed")
                                    pass
                                
                            except Exception as e:
                                print(f"Failed to create employees for {dept_name}: {e}")
                                await tx.rollback_to_savepoint(employees_savepoint)
                                # Department exists but no employees
                            
                        except Exception as e:
                            print(f"Failed to create department {dept_name}: {e}")
                            await tx.rollback_to_savepoint(dept_savepoint)
                            # Continue with other departments
                    
                    print(f"Created {len(departments)} departments")
                    
                except Exception as e:
                    print(f"Failed to create departments: {e}")
                    await tx.rollback_to_savepoint(departments_savepoint)
                    # Company exists but no departments
                
            except Exception as e:
                print(f"Failed to create company: {e}")
                await tx.rollback_to_savepoint(company_savepoint)
                # Nothing created
```

## Advanced Nested Transaction Patterns

### Conditional Rollback

```python
class ConditionalTransaction:
    """Transaction with conditional rollback logic."""
    
    def __init__(self, transaction):
        self.transaction = transaction
        self.conditions = []
        self.savepoints = []
    
    async def add_condition(self, condition_func, rollback_message: str = None):
        """Add a condition that must be met for transaction to commit."""
        
        savepoint = await self.transaction.create_savepoint(f"condition_{len(self.conditions)}")
        
        self.conditions.append({
            "function": condition_func,
            "message": rollback_message or "Condition not met",
            "savepoint": savepoint
        })
        
        self.savepoints.append(savepoint)
    
    async def evaluate_conditions(self) -> bool:
        """Evaluate all conditions and rollback if any fail."""
        
        for i, condition in enumerate(self.conditions):
            try:
                if not await condition["function"]():
                    print(f"Condition {i} failed: {condition['message']}")
                    await self.transaction.rollback_to_savepoint(condition["savepoint"])
                    return False
            except Exception as e:
                print(f"Condition {i} evaluation failed: {e}")
                await self.transaction.rollback_to_savepoint(condition["savepoint"])
                return False
        
        return True
    
    async def commit_if_conditions_met(self):
        """Commit transaction only if all conditions are met."""
        
        if await self.evaluate_conditions():
            print("All conditions met, transaction will commit")
            return True
        else:
            print("Some conditions failed, transaction rolled back")
            return False

# Usage
async def conditional_transaction_example():
    """Demonstrate conditional transaction usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            conditional_tx = ConditionalTransaction(tx)
            
            # Create some data
            partner = await client.model("res.partner").create({
                "name": "Conditional Partner"
            })
            
            product = await client.model("product.product").create({
                "name": "Conditional Product",
                "list_price": 50.0
            })
            
            # Add conditions
            async def partner_has_email():
                updated_partner = await client.model("res.partner").filter(id=partner.id).first()
                return bool(updated_partner.email)
            
            async def product_price_valid():
                updated_product = await client.model("product.product").filter(id=product.id).first()
                return updated_product.list_price > 0
            
            await conditional_tx.add_condition(
                partner_has_email,
                "Partner must have email address"
            )
            
            await conditional_tx.add_condition(
                product_price_valid,
                "Product must have positive price"
            )
            
            # Update data to meet conditions
            await partner.update({"email": "conditional@example.com"})
            # Product already has valid price
            
            # Evaluate conditions before commit
            success = await conditional_tx.commit_if_conditions_met()
            
            if success:
                print("Transaction committed successfully")
            else:
                print("Transaction was rolled back due to failed conditions")
```

## Best Practices

1. **Use Descriptive Names**: Give savepoints meaningful names
2. **Clean Up Savepoints**: Release savepoints when no longer needed
3. **Handle Nested Errors**: Implement proper error handling at each level
4. **Limit Nesting Depth**: Avoid excessive nesting for performance
5. **Document Logic**: Document complex nested transaction logic

## Performance Considerations

```python
async def performance_optimized_nested():
    """Demonstrate performance-optimized nested transactions."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Batch operations to minimize savepoint overhead
            batch_size = 50
            items = list(range(200))  # 200 items to process
            
            for batch_start in range(0, len(items), batch_size):
                batch_end = min(batch_start + batch_size, len(items))
                batch_items = items[batch_start:batch_end]
                
                # Create savepoint for entire batch
                batch_savepoint = await tx.create_savepoint(f"batch_{batch_start}")
                
                try:
                    # Process batch without individual savepoints
                    for i in batch_items:
                        await client.model("res.partner").create({
                            "name": f"Batch Partner {i}"
                        })
                    
                    print(f"Processed batch {batch_start}-{batch_end}")
                    
                    # Release savepoint on successful batch
                    await tx.release_savepoint(batch_savepoint)
                    
                except Exception as e:
                    print(f"Batch {batch_start}-{batch_end} failed: {e}")
                    await tx.rollback_to_savepoint(batch_savepoint)
                    
                    # Optionally retry individual items in failed batch
                    for i in batch_items:
                        item_savepoint = await tx.create_savepoint(f"item_{i}")
                        
                        try:
                            await client.model("res.partner").create({
                                "name": f"Retry Partner {i}"
                            })
                            await tx.release_savepoint(item_savepoint)
                            
                        except Exception as item_error:
                            await tx.rollback_to_savepoint(item_savepoint)
                            print(f"Item {i} failed: {item_error}")
```

## Related

- [Transaction Manager](manager.md) - Transaction management
- [Transaction Context](context.md) - Context usage
- [ACID Properties](acid.md) - ACID compliance
