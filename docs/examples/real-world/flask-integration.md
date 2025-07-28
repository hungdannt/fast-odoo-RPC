# Flask Integration

Create web services with Flask and Zenoo RPC integration.

## Overview

This example demonstrates:
- Flask web application with Odoo integration
- REST API endpoints
- User authentication
- Data synchronization
- Background task processing

## Implementation

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

@app.route('/api/sync', methods=['POST'])
def sync_all_partners():
    """Sync all partners with Odoo."""
    
    partners = Partner.query.filter_by(odoo_id=None).all()
    
    for partner in partners:
        asyncio.run(sync_partner_to_odoo(partner))
    
    return jsonify({'synced': len(partners)})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

## Background Tasks with Celery

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
```

## Next Steps

- [Django Integration](django-integration.md) - Django applications
- [FastAPI Integration](fastapi-integration.md) - Modern APIs
- [Webhook Handlers](webhook-handlers.md) - Event handling
