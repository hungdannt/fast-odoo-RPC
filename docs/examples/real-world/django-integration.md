# Django Integration

Integrate Odoo with Django applications using Zenoo RPC.

## Overview

This example demonstrates:
- Django model integration with Odoo
- User authentication synchronization
- Data synchronization between Django and Odoo
- Django admin integration
- REST API endpoints

## Implementation

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
import asyncio
from zenoo_rpc import ZenooClient

class OdooPartner(models.Model):
    """Django model representing Odoo partner."""
    
    odoo_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    last_sync = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'odoo_partners'
    
    async def sync_to_odoo(self):
        """Sync this partner to Odoo."""
        
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            if self.odoo_id:
                # Update existing
                await client.model("res.partner").filter(
                    id=self.odoo_id
                ).update({
                    "name": self.name,
                    "email": self.email,
                    "phone": self.phone
                })
            else:
                # Create new
                partner = await client.model("res.partner").create({
                    "name": self.name,
                    "email": self.email,
                    "phone": self.phone,
                    "customer_rank": 1
                })
                self.odoo_id = partner.id
                self.save()

# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import asyncio

@csrf_exempt
async def sync_partner(request):
    """Sync partner data with Odoo."""
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        partner = OdooPartner.objects.get(id=data['partner_id'])
        await partner.sync_to_odoo()
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

# management/commands/sync_odoo.py
from django.core.management.base import BaseCommand
from myapp.models import OdooPartner
import asyncio

class Command(BaseCommand):
    """Django management command for Odoo sync."""
    
    help = 'Synchronize data with Odoo'
    
    def handle(self, *args, **options):
        asyncio.run(self.sync_partners())
    
    async def sync_partners(self):
        """Sync all partners with Odoo."""
        
        partners = OdooPartner.objects.all()
        
        for partner in partners:
            await partner.sync_to_odoo()
            self.stdout.write(f"Synced partner: {partner.name}")
```

## Django REST Framework Integration

```python
# serializers.py
from rest_framework import serializers
from .models import OdooPartner

class OdooPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OdooPartner
        fields = '__all__'

# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class OdooPartnerViewSet(viewsets.ModelViewSet):
    queryset = OdooPartner.objects.all()
    serializer_class = OdooPartnerSerializer
    
    @action(detail=True, methods=['post'])
    async def sync_to_odoo(self, request, pk=None):
        """Sync partner to Odoo."""
        
        partner = self.get_object()
        await partner.sync_to_odoo()
        
        return Response({'status': 'synced'})
```

## Next Steps

- [Flask Integration](flask-integration.md) - Flask web services
- [FastAPI Integration](fastapi-integration.md) - Modern REST APIs
- [Webhook Handlers](webhook-handlers.md) - Real-time webhooks
