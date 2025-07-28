# Flask Integration

Create web services with Flask and Zenoo RPC integration.

## Overview

This example demonstrates:
- Flask web application with Odoo integration
- REST API endpoints
- User authentication
- Data synchronization
- Background task processing

## Installation

```bash
pip install flask flask-sqlalchemy
pip install zenoo-rpc
```

## Basic Flask Application

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import asyncio
from zenoo_rpc import ZenooClient

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

class Partner(db.Model):
    """Flask model for partners."""
    
    id = db.Column(db.Integer, primary_key=True)
    odoo_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))

@app.route('/api/partners', methods=['GET'])
def get_partners():
    """Get all partners."""
    
    partners = Partner.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'email': p.email,
        'phone': p.phone
    } for p in partners])

@app.route('/api/partners', methods=['POST'])
def create_partner():
    """Create new partner and sync to Odoo."""
    
    data = request.json
    
    # Create in Flask
    partner = Partner(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone')
    )
    db.session.add(partner)
    db.session.commit()
    
    # Sync to Odoo
    asyncio.run(sync_partner_to_odoo(partner))
    
    return jsonify({'id': partner.id, 'status': 'created'})

async def sync_partner_to_odoo(partner):
    """Sync partner to Odoo."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        odoo_partner = await client.model("res.partner").create({
            "name": partner.name,
            "email": partner.email,
            "phone": partner.phone,
            "customer_rank": 1
        })
        
        # Update Flask record with Odoo ID
        partner.odoo_id = odoo_partner.id
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

## Advanced Features

### Background Tasks with Celery

```python
from celery import Celery
import asyncio

celery = Celery('flask_app')

@celery.task
def sync_partner_task(partner_id):
    """Background task to sync partner."""
    
    partner = Partner.query.get(partner_id)
    asyncio.run(sync_partner_to_odoo(partner))
    
    return f"Synced partner {partner.name}"

@app.route('/api/partners/<int:partner_id>/sync', methods=['POST'])
def sync_partner_background(partner_id):
    """Sync partner in background."""
    
    task = sync_partner_task.delay(partner_id)
    return jsonify({'task_id': task.id, 'status': 'queued'})
```

### Error Handling

```python
from flask import abort
from zenoo_rpc.exceptions import ZenooError

@app.errorhandler(ZenooError)
def handle_zenoo_error(error):
    """Handle Zenoo RPC errors."""
    return jsonify({
        'error': 'Odoo integration error',
        'message': str(error)
    }), 500

@app.route('/api/partners/<int:partner_id>', methods=['PUT'])
def update_partner(partner_id):
    """Update partner with error handling."""
    
    partner = Partner.query.get_or_404(partner_id)
    data = request.json
    
    try:
        # Update Flask record
        partner.name = data.get('name', partner.name)
        partner.email = data.get('email', partner.email)
        partner.phone = data.get('phone', partner.phone)
        db.session.commit()
        
        # Sync to Odoo if exists
        if partner.odoo_id:
            asyncio.run(update_odoo_partner(partner))
        
        return jsonify({'status': 'updated'})
        
    except ZenooError as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to sync with Odoo',
            'message': str(e)
        }), 500

async def update_odoo_partner(partner):
    """Update partner in Odoo."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        await client.model("res.partner").filter(
            id=partner.odoo_id
        ).update({
            "name": partner.name,
            "email": partner.email,
            "phone": partner.phone
        })
```

## Best Practices

1. **Async Context**: Always use async context managers for Zenoo clients
2. **Error Handling**: Implement proper error handling for Odoo operations
3. **Background Tasks**: Use Celery for long-running Odoo operations
4. **Database Transactions**: Use database transactions for data consistency
5. **Validation**: Validate data before syncing to Odoo

## Next Steps

- [Django Integration](django-integration.md) - Django applications
- [Celery Integration](celery-integration.md) - Background processing
- [Database Integration](database-integration.md) - Database patterns
