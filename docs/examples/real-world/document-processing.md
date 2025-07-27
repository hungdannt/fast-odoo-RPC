# Document Processing and Generation

A comprehensive example demonstrating how to implement document processing, PDF generation, and automated document workflows using Zenoo RPC with various document libraries and templates.

## Overview

This example shows how to:

- Generate PDF documents from templates
- Process and extract data from documents
- Create automated document workflows
- Handle document storage and retrieval
- Integrate with document management systems
- Implement digital signatures and security

## Complete Implementation

### Document Processing Service

```python
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Union, BinaryIO
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
import uuid
import base64

# Document processing libraries
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from jinja2 import Environment, FileSystemLoader
import PyPDF2
from PIL import Image as PILImage

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q

class DocumentType(Enum):
    """Document type classification."""
    INVOICE = "invoice"
    QUOTE = "quote"
    REPORT = "report"
    CONTRACT = "contract"
    CERTIFICATE = "certificate"
    LETTER = "letter"

class DocumentStatus(Enum):
    """Document processing status."""
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

@dataclass
class DocumentTemplate:
    """Document template definition."""
    template_id: str
    name: str
    description: str
    document_type: DocumentType
    template_path: str
    variables: List[str] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DocumentRequest:
    """Document generation request."""
    request_id: str
    template_id: str
    data: Dict[str, Any]
    output_format: str = "pdf"  # pdf, html, docx
    status: DocumentStatus = DocumentStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None

class DocumentProcessingService:
    """Document processing service with PDF generation and template management."""
    
    def __init__(self, client: ZenooClient, storage_path: str = "/tmp/documents"):
        self.client = client
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.templates: Dict[str, DocumentTemplate] = {}
        self.requests: Dict[str, DocumentRequest] = {}
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))
        self._create_default_templates()
    
    def register_template(self, template: DocumentTemplate):
        """Register a new document template."""
        self.templates[template.template_id] = template
        print(f"Registered document template: {template.name}")
    
    async def generate_document(
        self,
        template_id: str,
        data: Dict[str, Any],
        output_format: str = "pdf"
    ) -> str:
        """Generate a document from template and data."""
        
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Create document request
        request_id = str(uuid.uuid4())
        request = DocumentRequest(
            request_id=request_id,
            template_id=template_id,
            data=data,
            output_format=output_format,
            status=DocumentStatus.PROCESSING
        )
        
        self.requests[request_id] = request
        
        try:
            # Generate document based on type
            if template.document_type == DocumentType.INVOICE:
                file_path = await self._generate_invoice_pdf(template, data, request_id)
            elif template.document_type == DocumentType.QUOTE:
                file_path = await self._generate_quote_pdf(template, data, request_id)
            elif template.document_type == DocumentType.REPORT:
                file_path = await self._generate_report_pdf(template, data, request_id)
            else:
                file_path = await self._generate_generic_pdf(template, data, request_id)
            
            # Update request
            request.status = DocumentStatus.COMPLETED
            request.completed_at = datetime.now()
            request.file_path = file_path
            
            print(f"Document generated: {file_path}")
            return request_id
            
        except Exception as e:
            request.status = DocumentStatus.FAILED
            request.error_message = str(e)
            print(f"Document generation failed: {e}")
            raise
    
    async def generate_invoice_document(
        self,
        order_id: int,
        include_logo: bool = True
    ) -> str:
        """Generate an invoice document for a sales order."""
        
        # Get order data
        order = await self.client.model(SaleOrder).filter(id=order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Get customer data
        customer = await self.client.model(ResPartner).filter(
            id=order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id
        ).first()
        
        # Prepare invoice data
        invoice_data = {
            "invoice_number": f"INV-{order.name}",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "customer": {
                "name": customer.name if customer else "Unknown Customer",
                "email": customer.email if customer else "",
                "address": getattr(customer, 'street', '') if customer else ""
            },
            "order": {
                "number": order.name,
                "date": order.date_order.strftime("%Y-%m-%d") if order.date_order else "",
                "amount": float(order.amount_total),
                "currency": "USD"  # Default currency
            },
            "company": {
                "name": "Your Company Name",
                "address": "123 Business St, City, State 12345",
                "phone": "+1-555-0123",
                "email": "info@yourcompany.com"
            },
            "include_logo": include_logo
        }
        
        return await self.generate_document("invoice_template", invoice_data)
    
    async def generate_customer_report(
        self,
        start_date: date,
        end_date: date,
        customer_id: Optional[int] = None
    ) -> str:
        """Generate a customer activity report."""
        
        # Build query
        query_builder = self.client.model(SaleOrder).filter(
            Q(date_order__gte=start_date) &
            Q(date_order__lte=end_date) &
            Q(state__in=["sale", "done"])
        )
        
        if customer_id:
            query_builder = query_builder.filter(partner_id=customer_id)
        
        # Get orders
        orders = await query_builder.only(
            "name", "partner_id", "date_order", "amount_total", "state"
        ).all()
        
        # Get customer data
        customer_ids = list(set(
            order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id
            for order in orders
        ))
        
        customers = {}
        if customer_ids:
            customer_list = await self.client.model(ResPartner).filter(
                Q(id__in=customer_ids)
            ).only("name", "email", "is_company").all()
            
            customers = {c.id: c for c in customer_list}
        
        # Prepare report data
        report_data = {
            "title": "Customer Activity Report",
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            "summary": {
                "total_orders": len(orders),
                "total_revenue": sum(order.amount_total for order in orders),
                "unique_customers": len(customer_ids)
            },
            "orders": [
                {
                    "order_number": order.name,
                    "customer_name": customers.get(
                        order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id,
                        type('obj', (object,), {'name': 'Unknown'})()
                    ).name,
                    "date": order.date_order.strftime("%Y-%m-%d") if order.date_order else "",
                    "amount": float(order.amount_total),
                    "status": order.state
                }
                for order in orders
            ],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return await self.generate_document("report_template", report_data)
    
    async def _generate_invoice_pdf(
        self,
        template: DocumentTemplate,
        data: Dict[str, Any],
        request_id: str
    ) -> str:
        """Generate an invoice PDF document."""
        
        filename = f"invoice_{request_id}.pdf"
        file_path = self.storage_path / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Company and customer info
        info_data = [
            ["Invoice Number:", data.get("invoice_number", "")],
            ["Invoice Date:", data.get("invoice_date", "")],
            ["Due Date:", data.get("due_date", "")],
            ["", ""],
            ["Bill To:", ""],
            [data["customer"]["name"], ""],
            [data["customer"]["email"], ""],
            [data["customer"]["address"], ""]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        # Order details
        order_data = [
            ["Description", "Amount"],
            [f"Order {data['order']['number']}", f"${data['order']['amount']:,.2f}"]
        ]
        
        order_table = Table(order_data, colWidths=[4*inch, 2*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(order_table)
        story.append(Spacer(1, 30))
        
        # Total
        total_style = ParagraphStyle(
            'Total',
            parent=styles['Normal'],
            fontSize=14,
            alignment=2,  # Right align
            textColor=colors.darkblue
        )
        story.append(Paragraph(f"<b>Total: ${data['order']['amount']:,.2f}</b>", total_style))
        
        # Build PDF
        doc.build(story)
        
        return str(file_path)
    
    async def _generate_quote_pdf(
        self,
        template: DocumentTemplate,
        data: Dict[str, Any],
        request_id: str
    ) -> str:
        """Generate a quote PDF document."""
        
        filename = f"quote_{request_id}.pdf"
        file_path = self.storage_path / filename
        
        # Similar to invoice but with quote-specific formatting
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkgreen
        )
        story.append(Paragraph("QUOTATION", title_style))
        story.append(Spacer(1, 20))
        
        # Add quote-specific content
        quote_text = f"""
        Thank you for your interest in our services. Please find below our quotation
        for your requirements. This quote is valid for 30 days from the date of issue.
        """
        
        story.append(Paragraph(quote_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        
        return str(file_path)
    
    async def _generate_report_pdf(
        self,
        template: DocumentTemplate,
        data: Dict[str, Any],
        request_id: str
    ) -> str:
        """Generate a report PDF document."""
        
        filename = f"report_{request_id}.pdf"
        file_path = self.storage_path / filename
        
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = data.get("title", "Report")
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 20))
        
        # Period
        if "period" in data:
            period_text = f"Period: {data['period']['start_date']} to {data['period']['end_date']}"
            story.append(Paragraph(period_text, styles['Normal']))
            story.append(Spacer(1, 10))
        
        # Summary
        if "summary" in data:
            story.append(Paragraph("Summary", styles['Heading2']))
            summary = data["summary"]
            
            summary_data = [
                ["Metric", "Value"],
                ["Total Orders", str(summary.get("total_orders", 0))],
                ["Total Revenue", f"${summary.get('total_revenue', 0):,.2f}"],
                ["Unique Customers", str(summary.get("unique_customers", 0))]
            ]
            
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
        
        # Orders table
        if "orders" in data and data["orders"]:
            story.append(Paragraph("Order Details", styles['Heading2']))
            
            # Limit to first 20 orders for PDF size
            orders = data["orders"][:20]
            
            order_data = [["Order", "Customer", "Date", "Amount", "Status"]]
            for order in orders:
                order_data.append([
                    order["order_number"],
                    order["customer_name"][:20] + "..." if len(order["customer_name"]) > 20 else order["customer_name"],
                    order["date"],
                    f"${order['amount']:,.2f}",
                    order["status"]
                ])
            
            order_table = Table(order_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
            order_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(order_table)
        
        # Generated timestamp
        story.append(Spacer(1, 30))
        timestamp = data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        story.append(Paragraph(f"Generated: {timestamp}", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return str(file_path)
    
    async def _generate_generic_pdf(
        self,
        template: DocumentTemplate,
        data: Dict[str, Any],
        request_id: str
    ) -> str:
        """Generate a generic PDF document."""
        
        filename = f"document_{request_id}.pdf"
        file_path = self.storage_path / filename
        
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = data.get("title", template.name)
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 20))
        
        # Content
        content = data.get("content", "No content provided")
        story.append(Paragraph(content, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return str(file_path)
    
    def _create_default_templates(self):
        """Create default document templates."""
        
        # Invoice template
        invoice_template = DocumentTemplate(
            template_id="invoice_template",
            name="Standard Invoice",
            description="Standard invoice template for sales orders",
            document_type=DocumentType.INVOICE,
            template_path="invoice.html",
            variables=["invoice_number", "customer", "order", "company"]
        )
        
        # Quote template
        quote_template = DocumentTemplate(
            template_id="quote_template",
            name="Standard Quote",
            description="Standard quotation template",
            document_type=DocumentType.QUOTE,
            template_path="quote.html",
            variables=["quote_number", "customer", "items", "company"]
        )
        
        # Report template
        report_template = DocumentTemplate(
            template_id="report_template",
            name="Standard Report",
            description="Standard report template",
            document_type=DocumentType.REPORT,
            template_path="report.html",
            variables=["title", "period", "summary", "data"]
        )
        
        self.register_template(invoice_template)
        self.register_template(quote_template)
        self.register_template(report_template)
    
    def get_document_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get document generation status."""
        
        if request_id not in self.requests:
            return None
        
        request = self.requests[request_id]
        
        return {
            "request_id": request_id,
            "template_id": request.template_id,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "file_path": request.file_path,
            "error_message": request.error_message
        }
    
    def get_document_file(self, request_id: str) -> Optional[bytes]:
        """Get generated document file content."""
        
        if request_id not in self.requests:
            return None
        
        request = self.requests[request_id]
        
        if request.status != DocumentStatus.COMPLETED or not request.file_path:
            return None
        
        try:
            with open(request.file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading document file: {e}")
            return None

# Usage Example
async def main():
    """Demonstrate document processing capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize document service
        doc_service = DocumentProcessingService(client)
        
        print("📄 Starting document processing...")
        
        # Generate an invoice for a sales order
        # First, get a sales order
        orders = await client.model(SaleOrder).filter(
            state__in=["sale", "done"]
        ).limit(1).all()
        
        if orders:
            order = orders[0]
            invoice_request_id = await doc_service.generate_invoice_document(
                order_id=order.id,
                include_logo=True
            )
            
            print(f"Generated invoice: {invoice_request_id}")
            
            # Check status
            status = doc_service.get_document_status(invoice_request_id)
            print(f"Invoice status: {status['status']}")
        
        # Generate a customer report
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        report_request_id = await doc_service.generate_customer_report(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"Generated report: {report_request_id}")
        
        # Check report status
        report_status = doc_service.get_document_status(report_request_id)
        print(f"Report status: {report_status['status']}")
        
        # List generated documents
        print(f"\n📋 Generated Documents:")
        for request_id, request in doc_service.requests.items():
            print(f"  {request_id}: {request.status.value} - {request.file_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **PDF Generation**
- ReportLab integration
- Template-based generation
- Professional formatting
- Table and chart support

### 2. **Document Templates**
- Flexible template system
- Variable substitution
- Multiple document types
- Reusable components

### 3. **Business Documents**
- Invoice generation
- Quote creation
- Report generation
- Custom documents

### 4. **File Management**
- Document storage
- File retrieval
- Status tracking
- Error handling

### 5. **Integration Ready**
- Async processing
- Batch generation
- API endpoints
- Workflow integration

## Integration Examples

### FastAPI Document API

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

@app.post("/api/documents/invoice/{order_id}")
async def generate_invoice(order_id: int):
    """Generate invoice for order."""
    request_id = await doc_service.generate_invoice_document(order_id)
    return {"request_id": request_id}

@app.get("/api/documents/{request_id}/download")
async def download_document(request_id: str):
    """Download generated document."""
    status = doc_service.get_document_status(request_id)
    
    if not status or status["status"] != "completed":
        raise HTTPException(404, "Document not ready")
    
    return FileResponse(
        status["file_path"],
        media_type="application/pdf",
        filename=f"document_{request_id}.pdf"
    )
```

### Email Integration

```python
async def send_invoice_email(order_id: int, customer_email: str):
    """Generate and email invoice."""
    # Generate invoice
    request_id = await doc_service.generate_invoice_document(order_id)
    
    # Wait for completion
    await asyncio.sleep(2)
    
    # Get file content
    file_content = doc_service.get_document_file(request_id)
    
    if file_content:
        # Send email with attachment
        await email_service.send_transactional_email(
            template_id="invoice_email",
            recipient_email=customer_email,
            attachments=[("invoice.pdf", file_content)]
        )
```

## Next Steps

- [Email Automation](email-automation.md) - Integrate with email workflows
- [Automated Workflows](automated-workflows.md) - Document workflow automation
- [Scheduled Tasks](scheduled-tasks.md) - Schedule document generation
