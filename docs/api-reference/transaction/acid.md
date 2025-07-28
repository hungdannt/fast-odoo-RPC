# ACID Properties

Understanding ACID properties in Zenoo RPC transactions.

## Overview

ACID properties ensure reliable transaction processing:
- **Atomicity**: All operations succeed or all fail
- **Consistency**: Database remains in valid state
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed changes persist

## Atomicity

### All-or-Nothing Operations

```python
async def atomic_operations_example():
    """Demonstrate atomic operations."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # All these operations will succeed or all will fail
                partner = await client.model("res.partner").create({
                    "name": "ACME Corp",
                    "email": "contact@acme.com"
                })
                
                product = await client.model("product.product").create({
                    "name": "ACME Widget",
                    "list_price": 100.0
                })
                
                order = await client.model("sale.order").create({
                    "partner_id": partner.id,
                    "order_line": [(0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": 5
                    })]
                })
                
                # If any operation fails, all are rolled back
                if order.amount_total < 0:  # Business rule violation
                    raise ValueError("Invalid order total")
                
                print(f"Order created successfully: {order.id}")
                
        except Exception as e:
            print(f"Transaction failed, all operations rolled back: {e}")
```

### Partial Failure Handling

```python
async def handle_partial_failures():
    """Handle partial failures in batch operations."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        partners_data = [
            {"name": "Valid Partner 1", "email": "valid1@example.com"},
            {"name": "", "email": "invalid@example.com"},  # Invalid - empty name
            {"name": "Valid Partner 2", "email": "valid2@example.com"}
        ]
        
        # Atomic approach - all or nothing
        try:
            async with client.transaction() as tx:
                created_partners = []
                
                for partner_data in partners_data:
                    # Validate before creating
                    if not partner_data.get("name"):
                        raise ValueError(f"Invalid partner data: {partner_data}")
                    
                    partner = await client.model("res.partner").create(partner_data)
                    created_partners.append(partner)
                
                print(f"All {len(created_partners)} partners created successfully")
                
        except Exception as e:
            print(f"Batch creation failed, no partners created: {e}")
```

## Consistency

### Data Integrity Constraints

```python
async def maintain_data_consistency():
    """Demonstrate data consistency maintenance."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        async with client.transaction() as tx:
            # Create customer
            customer = await client.model("res.partner").create({
                "name": "Consistent Customer",
                "customer_rank": 1
            })
            
            # Create product
            product = await client.model("product.product").create({
                "name": "Consistent Product",
                "list_price": 50.0,
                "type": "product"
            })
            
            # Create order with consistent data
            order = await client.model("sale.order").create({
                "partner_id": customer.id,
                "state": "draft"
            })
            
            # Add order line
            order_line = await client.model("sale.order.line").create({
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": 2,
                "price_unit": product.list_price
            })
            
            # Verify consistency
            await order.action_confirm()  # This will validate business rules
            
            print(f"Consistent order created: {order.name}")

async def handle_consistency_violations():
    """Handle consistency constraint violations."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # Attempt to create order with non-existent customer
                order = await client.model("sale.order").create({
                    "partner_id": 99999,  # Non-existent customer
                    "state": "draft"
                })
                
        except Exception as e:
            print(f"Consistency violation prevented: {e}")
```

## Isolation

### Transaction Isolation Levels

```python
import asyncio

async def demonstrate_isolation():
    """Demonstrate transaction isolation."""
    
    async def transaction_1():
        """First concurrent transaction."""
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            async with client.transaction() as tx:
                print("Transaction 1: Starting")
                
                # Read partner
                partner = await client.model("res.partner").filter(id=1).first()
                original_name = partner.name
                print(f"Transaction 1: Read partner name: {original_name}")
                
                # Simulate processing time
                await asyncio.sleep(2)
                
                # Update partner
                await partner.update({"name": f"{original_name} - Updated by TX1"})
                print("Transaction 1: Updated partner")
                
                # Simulate more processing
                await asyncio.sleep(1)
                
                print("Transaction 1: Committing")
    
    async def transaction_2():
        """Second concurrent transaction."""
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            # Start slightly after transaction 1
            await asyncio.sleep(1)
            
            async with client.transaction() as tx:
                print("Transaction 2: Starting")
                
                # Read same partner
                partner = await client.model("res.partner").filter(id=1).first()
                print(f"Transaction 2: Read partner name: {partner.name}")
                
                # Update partner
                await partner.update({"name": f"{partner.name} - Updated by TX2"})
                print("Transaction 2: Updated partner")
                
                print("Transaction 2: Committing")
    
    # Run transactions concurrently
    await asyncio.gather(transaction_1(), transaction_2())
```

### Avoiding Race Conditions

```python
async def avoid_race_conditions():
    """Demonstrate race condition avoidance."""
    
    async def increment_counter_safely(counter_id: int):
        """Safely increment a counter value."""
        
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            async with client.transaction() as tx:
                # Use SELECT FOR UPDATE equivalent
                counter = await client.model("res.partner").filter(
                    id=counter_id
                ).first()
                
                if counter:
                    # Read current value
                    current_value = getattr(counter, 'ref', '0')
                    try:
                        numeric_value = int(current_value) if current_value else 0
                    except ValueError:
                        numeric_value = 0
                    
                    # Increment
                    new_value = numeric_value + 1
                    
                    # Update atomically
                    await counter.update({"ref": str(new_value)})
                    
                    print(f"Counter incremented to: {new_value}")
                    return new_value
    
    # Run multiple concurrent increments
    tasks = [increment_counter_safely(1) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print(f"Final counter values: {results}")
```

## Durability

### Ensuring Persistent Changes

```python
async def ensure_durability():
    """Demonstrate durability of committed transactions."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Create important data that must persist
        async with client.transaction() as tx:
            critical_partner = await client.model("res.partner").create({
                "name": "Critical Business Partner",
                "email": "critical@business.com",
                "customer_rank": 1,
                "supplier_rank": 1
            })
            
            # Create related records
            contract = await client.model("res.partner").create({
                "name": "Service Contract",
                "parent_id": critical_partner.id,
                "is_company": False
            })
            
            print(f"Critical data created: Partner {critical_partner.id}, Contract {contract.id}")
            
            # Transaction commits here - data is now durable
        
        # Verify data persists after transaction
        await asyncio.sleep(1)  # Simulate system activity
        
        # Read back the data
        persisted_partner = await client.model("res.partner").filter(
            id=critical_partner.id
        ).first()
        
        if persisted_partner:
            print(f"Data persisted successfully: {persisted_partner.name}")
        else:
            print("ERROR: Data was not persisted!")

async def handle_system_failures():
    """Demonstrate handling of system failures."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        try:
            async with client.transaction() as tx:
                # Create data
                partner = await client.model("res.partner").create({
                    "name": "Pre-failure Partner"
                })
                
                # Simulate system failure before commit
                # In real scenarios, this could be network failure, server crash, etc.
                raise SystemError("Simulated system failure")
                
        except SystemError as e:
            print(f"System failure occurred: {e}")
            print("Transaction was not committed - no data persisted")
        
        # Verify no partial data exists
        failed_partners = await client.model("res.partner").filter(
            name="Pre-failure Partner"
        ).all()
        
        print(f"Partners found after failure: {len(failed_partners)}")
```

## ACID Compliance Best Practices

### Transaction Design Patterns

```python
class ACIDCompliantService:
    """Service class demonstrating ACID-compliant operations."""
    
    def __init__(self, client: ZenooClient):
        self.client = client
    
    async def create_customer_with_order(self, customer_data: dict, order_data: dict) -> dict:
        """Create customer and initial order atomically."""
        
        async with self.client.transaction() as tx:
            # Validate input data (Consistency)
            self._validate_customer_data(customer_data)
            self._validate_order_data(order_data)
            
            # Create customer (Atomicity)
            customer = await self.client.model("res.partner").create({
                **customer_data,
                "customer_rank": 1
            })
            
            # Create order (Atomicity)
            order = await self.client.model("sale.order").create({
                **order_data,
                "partner_id": customer.id,
                "state": "draft"
            })
            
            # Verify business rules (Consistency)
            if order.amount_total < 0:
                raise ValueError("Order total cannot be negative")
            
            # All operations succeed together (Atomicity)
            # Changes are isolated from other transactions (Isolation)
            # Changes will persist after commit (Durability)
            
            return {
                "customer_id": customer.id,
                "order_id": order.id,
                "status": "success"
            }
    
    def _validate_customer_data(self, data: dict):
        """Validate customer data for consistency."""
        if not data.get("name"):
            raise ValueError("Customer name is required")
        if data.get("email") and "@" not in data["email"]:
            raise ValueError("Invalid email format")
    
    def _validate_order_data(self, data: dict):
        """Validate order data for consistency."""
        if not data.get("order_line"):
            raise ValueError("Order must have at least one line")
    
    async def transfer_customer_data(self, from_customer_id: int, to_customer_id: int) -> dict:
        """Transfer data between customers atomically."""
        
        async with self.client.transaction() as tx:
            # Read source customer (Isolation)
            source = await self.client.model("res.partner").filter(
                id=from_customer_id
            ).first()
            
            if not source:
                raise ValueError(f"Source customer {from_customer_id} not found")
            
            # Read target customer (Isolation)
            target = await self.client.model("res.partner").filter(
                id=to_customer_id
            ).first()
            
            if not target:
                raise ValueError(f"Target customer {to_customer_id} not found")
            
            # Transfer orders atomically
            orders = await self.client.model("sale.order").filter(
                partner_id=from_customer_id,
                state__in=["draft", "sent"]
            ).all()
            
            transferred_count = 0
            for order in orders:
                await order.update({"partner_id": to_customer_id})
                transferred_count += 1
            
            # Update customer status (Consistency)
            await source.update({"active": False})
            
            # All changes are atomic and will be durable
            return {
                "transferred_orders": transferred_count,
                "source_deactivated": True,
                "status": "success"
            }

# Usage
async def use_acid_service():
    """Demonstrate ACID-compliant service usage."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        service = ACIDCompliantService(client)
        
        try:
            # Create customer with order (ACID compliant)
            result = await service.create_customer_with_order(
                customer_data={
                    "name": "ACID Test Customer",
                    "email": "acid@test.com"
                },
                order_data={
                    "order_line": [(0, 0, {
                        "product_id": 1,
                        "product_uom_qty": 1
                    })]
                }
            )
            
            print(f"ACID operation completed: {result}")
            
        except Exception as e:
            print(f"ACID operation failed (all changes rolled back): {e}")
```

## Best Practices

1. **Keep Transactions Short**: Minimize transaction duration to reduce lock contention
2. **Validate Early**: Perform validation before starting expensive operations
3. **Handle Conflicts**: Implement proper handling for isolation conflicts
4. **Monitor Performance**: Track transaction performance and deadlock rates
5. **Test Concurrency**: Test your application under concurrent load

## Related

- [Transaction Manager](manager.md) - Transaction management
- [Transaction Context](context.md) - Context usage
- [Transaction Exceptions](exceptions.md) - Error handling
