# Django Integration

Comprehensive guide for integrating Zenoo RPC with Django applications.

## Overview

This example demonstrates:
- Django model synchronization with Odoo
- User authentication integration
- Django admin interface for Odoo data
- REST API endpoints with Django REST Framework
- Background task processing with Celery

## Installation

```bash
pip install django djangorestframework celery
pip install zenoo-rpc
```

## Django Settings

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'odoo_integration',  # Your app
]

# Odoo Configuration
ODOO_CONFIG = {
    'host': 'localhost',
    'port': 8069,
    'database': 'demo',
    'username': 'admin',
    'password': 'admin'
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

## Models

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
import asyncio
from zenoo_rpc import ZenooClient
from django.conf import settings

class OdooSyncMixin:
    """Mixin for Odoo synchronization."""
    
    async def sync_to_odoo(self):
        """Sync this model to Odoo."""
        async with ZenooClient(
            settings.ODOO_CONFIG['host'],
            port=settings.ODOO_CONFIG['port']
        ) as client:
            await client.login(
                settings.ODOO_CONFIG['database'],
                settings.ODOO_CONFIG['username'],
                settings.ODOO_CONFIG['password']
            )
            
            return await self._perform_odoo_sync(client)
    
    async def _perform_odoo_sync(self, client):
        """Override in subclasses."""
        raise NotImplementedError

class Partner(models.Model, OdooSyncMixin):
    """Django model representing Odoo partner."""
    
    odoo_id = models.IntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    is_company = models.BooleanField(default=False)
    last_sync = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partners'
    
    def __str__(self):
        return self.name
    
    async def _perform_odoo_sync(self, client):
        """Sync partner to Odoo."""
        
        partner_data = {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "is_company": self.is_company,
            "customer_rank": 1
        }
        
        if self.odoo_id:
            # Update existing
            await client.model("res.partner").filter(
                id=self.odoo_id
            ).update(partner_data)
        else:
            # Create new
            partner = await client.model("res.partner").create(partner_data)
            self.odoo_id = partner.id
            self.save()
        
        return self.odoo_id

class Product(models.Model, OdooSyncMixin):
    """Django model representing Odoo product."""
    
    odoo_id = models.IntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    default_code = models.CharField(max_length=100, unique=True)
    list_price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
    
    def __str__(self):
        return self.name
    
    async def _perform_odoo_sync(self, client):
        """Sync product to Odoo."""
        
        product_data = {
            "name": self.name,
            "default_code": self.default_code,
            "list_price": float(self.list_price),
            "active": self.active,
            "sale_ok": True
        }
        
        if self.odoo_id:
            await client.model("product.product").filter(
                id=self.odoo_id
            ).update(product_data)
        else:
            product = await client.model("product.product").create(product_data)
            self.odoo_id = product.id
            self.save()
        
        return self.odoo_id
```

## Django Admin Integration

```python
# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Partner, Product
from .tasks import sync_to_odoo_task

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'odoo_id', 'last_sync', 'sync_status']
    list_filter = ['is_company', 'last_sync']
    search_fields = ['name', 'email']
    actions = ['sync_to_odoo']
    
    def sync_status(self, obj):
        """Display sync status."""
        if obj.odoo_id:
            return format_html(
                '<span style="color: green;">✓ Synced (ID: {})</span>',
                obj.odoo_id
            )
        else:
            return format_html('<span style="color: red;">✗ Not synced</span>')
    
    sync_status.short_description = 'Sync Status'
    
    def sync_to_odoo(self, request, queryset):
        """Admin action to sync selected partners to Odoo."""
        for partner in queryset:
            sync_to_odoo_task.delay('partner', partner.id)
        
        self.message_user(
            request,
            f"Sync initiated for {queryset.count()} partners."
        )
    
    sync_to_odoo.short_description = "Sync selected partners to Odoo"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_code', 'list_price', 'odoo_id', 'last_sync']
    list_filter = ['active', 'last_sync']
    search_fields = ['name', 'default_code']
    actions = ['sync_to_odoo']
    
    def sync_to_odoo(self, request, queryset):
        """Admin action to sync selected products to Odoo."""
        for product in queryset:
            sync_to_odoo_task.delay('product', product.id)
        
        self.message_user(
            request,
            f"Sync initiated for {queryset.count()} products."
        )
    
    sync_to_odoo.short_description = "Sync selected products to Odoo"
```

## REST API with Django REST Framework

```python
# serializers.py
from rest_framework import serializers
from .models import Partner, Product

class PartnerSerializer(serializers.ModelSerializer):
    sync_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = '__all__'
    
    def get_sync_status(self, obj):
        return "synced" if obj.odoo_id else "not_synced"

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Partner, Product
from .serializers import PartnerSerializer, ProductSerializer
from .tasks import sync_to_odoo_task

class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    
    @action(detail=True, methods=['post'])
    def sync_to_odoo(self, request, pk=None):
        """Sync partner to Odoo."""
        partner = self.get_object()
        
        # Start background sync task
        task = sync_to_odoo_task.delay('partner', partner.id)
        
        return Response({
            'status': 'sync_initiated',
            'task_id': task.id
        })
    
    @action(detail=False, methods=['post'])
    def bulk_sync(self, request):
        """Bulk sync partners to Odoo."""
        partner_ids = request.data.get('partner_ids', [])
        
        for partner_id in partner_ids:
            sync_to_odoo_task.delay('partner', partner_id)
        
        return Response({
            'status': 'bulk_sync_initiated',
            'count': len(partner_ids)
        })

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    @action(detail=True, methods=['post'])
    def sync_to_odoo(self, request, pk=None):
        """Sync product to Odoo."""
        product = self.get_object()
        
        task = sync_to_odoo_task.delay('product', product.id)
        
        return Response({
            'status': 'sync_initiated',
            'task_id': task.id
        })
```

## Celery Tasks

```python
# tasks.py
from celery import Celery
import asyncio
from .models import Partner, Product

app = Celery('django_odoo_integration')

@app.task
def sync_to_odoo_task(model_type, object_id):
    """Background task to sync object to Odoo."""
    
    try:
        if model_type == 'partner':
            partner = Partner.objects.get(id=object_id)
            result = asyncio.run(partner.sync_to_odoo())
            return f"Partner {partner.name} synced with Odoo ID: {result}"
        
        elif model_type == 'product':
            product = Product.objects.get(id=object_id)
            result = asyncio.run(product.sync_to_odoo())
            return f"Product {product.name} synced with Odoo ID: {result}"
        
        else:
            return f"Unknown model type: {model_type}"
    
    except Exception as e:
        return f"Sync failed: {str(e)}"

@app.task
def sync_from_odoo_task():
    """Background task to sync data from Odoo to Django."""
    
    async def sync_partners():
        async with ZenooClient("localhost", port=8069) as client:
            await client.login("demo", "admin", "admin")
            
            # Get partners from Odoo
            odoo_partners = await client.model("res.partner").filter(
                customer_rank__gt=0
            ).only("name", "email", "phone", "is_company").all()
            
            synced_count = 0
            
            for odoo_partner in odoo_partners:
                # Update or create Django partner
                partner, created = Partner.objects.update_or_create(
                    odoo_id=odoo_partner.id,
                    defaults={
                        "name": odoo_partner.name,
                        "email": odoo_partner.email or "",
                        "phone": odoo_partner.phone or "",
                        "is_company": odoo_partner.is_company
                    }
                )
                synced_count += 1
            
            return synced_count
    
    try:
        count = asyncio.run(sync_partners())
        return f"Synced {count} partners from Odoo"
    except Exception as e:
        return f"Sync from Odoo failed: {str(e)}"
```

## Management Commands

```python
# management/commands/sync_odoo.py
from django.core.management.base import BaseCommand
from django.apps import apps
import asyncio

class Command(BaseCommand):
    help = 'Synchronize data with Odoo'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Model to sync (partner, product, all)',
            default='all'
        )
        parser.add_argument(
            '--direction',
            type=str,
            choices=['to_odoo', 'from_odoo', 'both'],
            help='Sync direction',
            default='both'
        )
    
    def handle(self, *args, **options):
        model = options['model']
        direction = options['direction']
        
        if model == 'all':
            models_to_sync = ['partner', 'product']
        else:
            models_to_sync = [model]
        
        for model_name in models_to_sync:
            if direction in ['to_odoo', 'both']:
                asyncio.run(self.sync_to_odoo(model_name))
            
            if direction in ['from_odoo', 'both']:
                asyncio.run(self.sync_from_odoo(model_name))
    
    async def sync_to_odoo(self, model_name):
        """Sync Django models to Odoo."""
        if model_name == 'partner':
            from myapp.models import Partner
            partners = Partner.objects.filter(odoo_id__isnull=True)
            
            for partner in partners:
                await partner.sync_to_odoo()
                self.stdout.write(f"Synced partner: {partner.name}")
    
    async def sync_from_odoo(self, model_name):
        """Sync from Odoo to Django."""
        # Implementation similar to Celery task
        pass
```

## URL Configuration

```python
# urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PartnerViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'partners', PartnerViewSet)
router.register(r'products', ProductViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]
```

## Usage Examples

```python
# Example usage in Django views
from django.shortcuts import render
from .models import Partner
import asyncio

def partner_list(request):
    """Display partners with sync status."""
    partners = Partner.objects.all()
    return render(request, 'partners/list.html', {'partners': partners})

async def sync_all_partners(request):
    """Sync all partners to Odoo."""
    partners = Partner.objects.filter(odoo_id__isnull=True)
    
    for partner in partners:
        await partner.sync_to_odoo()
    
    return render(request, 'partners/sync_complete.html', {
        'count': len(partners)
    })
```

## Best Practices

1. **Use Background Tasks**: Always use Celery for Odoo operations
2. **Error Handling**: Implement proper error handling and logging
3. **Data Validation**: Validate data before syncing
4. **Incremental Sync**: Use timestamps for incremental synchronization
5. **Testing**: Write comprehensive tests for sync operations

## Next Steps

- [Flask Integration](flask-integration.md) - Flask applications
- [Celery Integration](celery-integration.md) - Background processing
- [Database Integration](database-integration.md) - Database patterns
