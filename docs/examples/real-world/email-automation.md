# Email Automation and Communication Workflows

A comprehensive example demonstrating how to implement email automation, template management, and communication workflows using Zenoo RPC with various email providers and advanced features.

## Overview

This example shows how to:

- Create automated email campaigns
- Manage email templates and personalization
- Implement transactional email workflows
- Handle email delivery and tracking
- Integrate with email service providers
- Monitor email performance and analytics

## Complete Implementation

### Email Automation Service

```python
import asyncio
import json
import smtplib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import jinja2
import uuid

from zenoo_rpc import ZenooClient
from zenoo_rpc.models.common import ResPartner, SaleOrder
from zenoo_rpc.query.filters import Q

class EmailStatus(Enum):
    """Email delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"

class EmailType(Enum):
    """Email type classification."""
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    NOTIFICATION = "notification"
    REMINDER = "reminder"

@dataclass
class EmailTemplate:
    """Email template definition."""
    template_id: str
    name: str
    subject: str
    html_content: str
    text_content: str
    email_type: EmailType
    variables: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class EmailCampaign:
    """Email campaign definition."""
    campaign_id: str
    name: str
    description: str
    template_id: str
    target_audience: Dict[str, Any]
    schedule: Optional[datetime] = None
    status: str = "draft"  # draft, scheduled, running, completed, paused
    created_at: datetime = field(default_factory=datetime.now)
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0

@dataclass
class EmailMessage:
    """Individual email message."""
    message_id: str
    campaign_id: Optional[str]
    template_id: str
    recipient_email: str
    recipient_name: str
    subject: str
    html_content: str
    text_content: str
    status: EmailStatus = EmailStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tracking_data: Dict[str, Any] = field(default_factory=dict)

class EmailAutomationService:
    """Email automation service with template management and delivery."""
    
    def __init__(self, client: ZenooClient, smtp_config: Optional[Dict[str, Any]] = None):
        self.client = client
        self.smtp_config = smtp_config or self._get_default_smtp_config()
        self.templates: Dict[str, EmailTemplate] = {}
        self.campaigns: Dict[str, EmailCampaign] = {}
        self.messages: Dict[str, EmailMessage] = {}
        self.jinja_env = jinja2.Environment(loader=jinja2.DictLoader({}))
        self._create_default_templates()
    
    def _get_default_smtp_config(self) -> Dict[str, Any]:
        """Get default SMTP configuration."""
        return {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "your-email@gmail.com",
            "password": "your-app-password",
            "use_tls": True
        }
    
    def create_template(self, template: EmailTemplate):
        """Create a new email template."""
        self.templates[template.template_id] = template
        
        # Add to Jinja environment
        self.jinja_env.loader.mapping[template.template_id + "_html"] = template.html_content
        self.jinja_env.loader.mapping[template.template_id + "_text"] = template.text_content
        
        print(f"Created email template: {template.name}")
    
    async def send_transactional_email(
        self,
        template_id: str,
        recipient_email: str,
        recipient_name: str,
        variables: Dict[str, Any],
        attachments: Optional[List[str]] = None
    ) -> str:
        """Send a transactional email immediately."""
        
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Render email content
        subject = self._render_template_string(template.subject, variables)
        html_content = self._render_template(template_id + "_html", variables)
        text_content = self._render_template(template_id + "_text", variables)
        
        # Create email message
        message = EmailMessage(
            message_id=str(uuid.uuid4()),
            campaign_id=None,
            template_id=template_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            scheduled_at=datetime.now()
        )
        
        self.messages[message.message_id] = message
        
        # Send immediately
        await self._send_email(message, attachments)
        
        return message.message_id
    
    async def create_email_campaign(
        self,
        name: str,
        description: str,
        template_id: str,
        target_filters: Dict[str, Any],
        schedule: Optional[datetime] = None
    ) -> str:
        """Create an email campaign."""
        
        campaign_id = str(uuid.uuid4())
        
        campaign = EmailCampaign(
            campaign_id=campaign_id,
            name=name,
            description=description,
            template_id=template_id,
            target_audience=target_filters,
            schedule=schedule,
            status="scheduled" if schedule else "draft"
        )
        
        self.campaigns[campaign_id] = campaign
        
        print(f"Created email campaign: {name}")
        return campaign_id
    
    async def execute_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Execute an email campaign."""
        
        if campaign_id not in self.campaigns:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        campaign = self.campaigns[campaign_id]
        template = self.templates[campaign.template_id]
        
        # Get target audience
        recipients = await self._get_campaign_recipients(campaign.target_audience)
        
        campaign.status = "running"
        
        # Create and send emails
        sent_messages = []
        
        for recipient in recipients:
            try:
                # Prepare variables for personalization
                variables = await self._prepare_recipient_variables(recipient)
                
                # Render email content
                subject = self._render_template_string(template.subject, variables)
                html_content = self._render_template(template.template_id + "_html", variables)
                text_content = self._render_template(template.template_id + "_text", variables)
                
                # Create email message
                message = EmailMessage(
                    message_id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    template_id=template.template_id,
                    recipient_email=recipient["email"],
                    recipient_name=recipient["name"],
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    scheduled_at=datetime.now()
                )
                
                self.messages[message.message_id] = message
                
                # Send email
                await self._send_email(message)
                sent_messages.append(message.message_id)
                
                # Small delay to avoid overwhelming SMTP server
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Failed to send email to {recipient['email']}: {e}")
        
        campaign.status = "completed"
        campaign.sent_count = len(sent_messages)
        
        return {
            "campaign_id": campaign_id,
            "sent_count": len(sent_messages),
            "total_recipients": len(recipients),
            "success_rate": len(sent_messages) / len(recipients) * 100 if recipients else 0
        }
    
    async def setup_automated_workflows(self):
        """Setup automated email workflows based on customer actions."""
        
        # Welcome email workflow
        await self._setup_welcome_email_workflow()
        
        # Order confirmation workflow
        await self._setup_order_confirmation_workflow()
        
        # Abandoned cart workflow
        await self._setup_abandoned_cart_workflow()
        
        # Customer retention workflow
        await self._setup_retention_workflow()
    
    async def _setup_welcome_email_workflow(self):
        """Setup welcome email workflow for new customers."""
        
        # This would typically be triggered by a webhook or event
        # For demonstration, we'll check for new customers periodically
        
        # Get customers created in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        new_customers = await (
            self.client.model(ResPartner)
            .filter(
                Q(create_date__gte=one_hour_ago) &
                Q(customer_rank__gt=0) &
                Q(email__ne=False)
            )
            .only("name", "email")
            .all()
        )
        
        for customer in new_customers:
            try:
                await self.send_transactional_email(
                    template_id="welcome_email",
                    recipient_email=customer.email,
                    recipient_name=customer.name,
                    variables={
                        "customer_name": customer.name,
                        "company_name": "Your Company"
                    }
                )
                print(f"Sent welcome email to {customer.name}")
                
            except Exception as e:
                print(f"Failed to send welcome email to {customer.name}: {e}")
    
    async def _setup_order_confirmation_workflow(self):
        """Setup order confirmation email workflow."""
        
        # Get recent orders that need confirmation emails
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        recent_orders = await (
            self.client.model(SaleOrder)
            .filter(
                Q(create_date__gte=one_hour_ago) &
                Q(state__in=["sale", "done"])
            )
            .only("name", "partner_id", "amount_total", "date_order")
            .all()
        )
        
        for order in recent_orders:
            try:
                # Get customer details
                customer = await self.client.model(ResPartner).filter(
                    id=order.partner_id.id if hasattr(order.partner_id, 'id') else order.partner_id
                ).first()
                
                if customer and customer.email:
                    await self.send_transactional_email(
                        template_id="order_confirmation",
                        recipient_email=customer.email,
                        recipient_name=customer.name,
                        variables={
                            "customer_name": customer.name,
                            "order_number": order.name,
                            "order_amount": f"${order.amount_total:,.2f}",
                            "order_date": order.date_order.strftime("%Y-%m-%d")
                        }
                    )
                    print(f"Sent order confirmation to {customer.name}")
                
            except Exception as e:
                print(f"Failed to send order confirmation: {e}")
    
    async def _send_email(self, message: EmailMessage, attachments: Optional[List[str]] = None):
        """Send an email message via SMTP."""
        
        try:
            # Create MIME message
            msg = MimeMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = self.smtp_config['username']
            msg['To'] = message.recipient_email
            
            # Add text and HTML parts
            text_part = MimeText(message.text_content, 'plain')
            html_part = MimeText(message.html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    with open(file_path, "rb") as attachment:
                        part = MimeBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {file_path.split("/")[-1]}'
                        )
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                if self.smtp_config.get('use_tls'):
                    server.starttls()
                
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            # Update message status
            message.status = EmailStatus.SENT
            message.sent_at = datetime.now()
            
            print(f"Email sent to {message.recipient_email}")
            
        except Exception as e:
            message.status = EmailStatus.FAILED
            message.error_message = str(e)
            print(f"Failed to send email to {message.recipient_email}: {e}")
    
    async def _get_campaign_recipients(self, target_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recipients for a campaign based on target filters."""
        
        # Build query based on filters
        query_builder = self.client.model(ResPartner).filter(
            Q(customer_rank__gt=0) & Q(email__ne=False)
        )
        
        # Apply additional filters
        if "is_company" in target_filters:
            query_builder = query_builder.filter(is_company=target_filters["is_company"])
        
        if "country_code" in target_filters:
            # This would need to be implemented based on your country model
            pass
        
        # Get customers
        customers = await query_builder.only("name", "email", "is_company").all()
        
        return [
            {
                "name": customer.name,
                "email": customer.email,
                "is_company": customer.is_company
            }
            for customer in customers
        ]
    
    async def _prepare_recipient_variables(self, recipient: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables for email personalization."""
        
        variables = {
            "recipient_name": recipient["name"],
            "recipient_email": recipient["email"],
            "company_name": "Your Company",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "unsubscribe_url": f"https://yoursite.com/unsubscribe?email={recipient['email']}"
        }
        
        # Add customer-specific data
        if recipient.get("is_company"):
            variables["greeting"] = f"Dear {recipient['name']} Team"
        else:
            variables["greeting"] = f"Dear {recipient['name']}"
        
        return variables
    
    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render a Jinja2 template with variables."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**variables)
    
    def _render_template_string(self, template_string: str, variables: Dict[str, Any]) -> str:
        """Render a template string with variables."""
        template = self.jinja_env.from_string(template_string)
        return template.render(**variables)
    
    def _create_default_templates(self):
        """Create default email templates."""
        
        # Welcome email template
        welcome_template = EmailTemplate(
            template_id="welcome_email",
            name="Welcome Email",
            subject="Welcome to {{ company_name }}!",
            html_content="""
            <html>
            <body>
                <h1>Welcome {{ customer_name }}!</h1>
                <p>Thank you for joining {{ company_name }}. We're excited to have you on board!</p>
                <p>Here are some things you can do to get started:</p>
                <ul>
                    <li>Complete your profile</li>
                    <li>Explore our products</li>
                    <li>Contact our support team if you need help</li>
                </ul>
                <p>Best regards,<br>The {{ company_name }} Team</p>
            </body>
            </html>
            """,
            text_content="""
            Welcome {{ customer_name }}!
            
            Thank you for joining {{ company_name }}. We're excited to have you on board!
            
            Here are some things you can do to get started:
            - Complete your profile
            - Explore our products
            - Contact our support team if you need help
            
            Best regards,
            The {{ company_name }} Team
            """,
            email_type=EmailType.TRANSACTIONAL,
            variables=["customer_name", "company_name"]
        )
        
        # Order confirmation template
        order_confirmation_template = EmailTemplate(
            template_id="order_confirmation",
            name="Order Confirmation",
            subject="Order Confirmation - {{ order_number }}",
            html_content="""
            <html>
            <body>
                <h1>Order Confirmation</h1>
                <p>Dear {{ customer_name }},</p>
                <p>Thank you for your order! Here are the details:</p>
                <ul>
                    <li><strong>Order Number:</strong> {{ order_number }}</li>
                    <li><strong>Order Date:</strong> {{ order_date }}</li>
                    <li><strong>Total Amount:</strong> {{ order_amount }}</li>
                </ul>
                <p>We'll send you another email when your order ships.</p>
                <p>Best regards,<br>The Sales Team</p>
            </body>
            </html>
            """,
            text_content="""
            Order Confirmation
            
            Dear {{ customer_name }},
            
            Thank you for your order! Here are the details:
            - Order Number: {{ order_number }}
            - Order Date: {{ order_date }}
            - Total Amount: {{ order_amount }}
            
            We'll send you another email when your order ships.
            
            Best regards,
            The Sales Team
            """,
            email_type=EmailType.TRANSACTIONAL,
            variables=["customer_name", "order_number", "order_date", "order_amount"]
        )
        
        self.create_template(welcome_template)
        self.create_template(order_confirmation_template)
    
    def get_email_analytics(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Get email analytics and performance metrics."""
        
        # Filter messages by campaign if specified
        if campaign_id:
            messages = [msg for msg in self.messages.values() if msg.campaign_id == campaign_id]
        else:
            messages = list(self.messages.values())
        
        if not messages:
            return {"error": "No messages found"}
        
        # Calculate metrics
        total_sent = len([msg for msg in messages if msg.status != EmailStatus.PENDING])
        total_delivered = len([msg for msg in messages if msg.status in [EmailStatus.DELIVERED, EmailStatus.OPENED, EmailStatus.CLICKED]])
        total_opened = len([msg for msg in messages if msg.status in [EmailStatus.OPENED, EmailStatus.CLICKED]])
        total_clicked = len([msg for msg in messages if msg.status == EmailStatus.CLICKED])
        total_bounced = len([msg for msg in messages if msg.status == EmailStatus.BOUNCED])
        total_failed = len([msg for msg in messages if msg.status == EmailStatus.FAILED])
        
        return {
            "total_messages": len(messages),
            "sent": total_sent,
            "delivered": total_delivered,
            "opened": total_opened,
            "clicked": total_clicked,
            "bounced": total_bounced,
            "failed": total_failed,
            "delivery_rate": (total_delivered / total_sent * 100) if total_sent > 0 else 0,
            "open_rate": (total_opened / total_delivered * 100) if total_delivered > 0 else 0,
            "click_rate": (total_clicked / total_opened * 100) if total_opened > 0 else 0,
            "bounce_rate": (total_bounced / total_sent * 100) if total_sent > 0 else 0
        }

# Usage Example
async def main():
    """Demonstrate email automation capabilities."""
    
    async with ZenooClient("localhost", port=8069) as client:
        await client.login("demo", "admin", "admin")
        
        # Initialize email service
        email_service = EmailAutomationService(client)
        
        print("📧 Starting email automation...")
        
        # Send a transactional email
        message_id = await email_service.send_transactional_email(
            template_id="welcome_email",
            recipient_email="customer@example.com",
            recipient_name="John Doe",
            variables={
                "customer_name": "John Doe",
                "company_name": "Zenoo Corp"
            }
        )
        print(f"Sent welcome email: {message_id}")
        
        # Create and execute a marketing campaign
        campaign_id = await email_service.create_email_campaign(
            name="Monthly Newsletter",
            description="Monthly newsletter for all customers",
            template_id="welcome_email",  # Using welcome template for demo
            target_filters={"is_company": False}
        )
        
        campaign_results = await email_service.execute_campaign(campaign_id)
        print(f"Campaign results: {campaign_results}")
        
        # Setup automated workflows
        await email_service.setup_automated_workflows()
        
        # Get analytics
        analytics = email_service.get_email_analytics()
        print(f"\n📊 Email Analytics:")
        print(f"  Total Messages: {analytics['total_messages']}")
        print(f"  Delivery Rate: {analytics['delivery_rate']:.1f}%")
        print(f"  Open Rate: {analytics['open_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Features Demonstrated

### 1. **Template Management**
- Jinja2 template engine
- Variable substitution
- HTML and text versions
- Template versioning

### 2. **Campaign Management**
- Audience targeting
- Scheduled campaigns
- Batch sending
- Performance tracking

### 3. **Transactional Emails**
- Immediate delivery
- Event-triggered emails
- Personalization
- Attachment support

### 4. **Automation Workflows**
- Welcome email sequences
- Order confirmations
- Abandoned cart recovery
- Customer retention

### 5. **Analytics & Monitoring**
- Delivery tracking
- Open/click rates
- Bounce monitoring
- Performance metrics

## Integration Examples

### Webhook Integration

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/customer-created")
async def customer_created_webhook(request: Request):
    """Webhook for new customer creation."""
    data = await request.json()
    
    await email_service.send_transactional_email(
        template_id="welcome_email",
        recipient_email=data["email"],
        recipient_name=data["name"],
        variables={"customer_name": data["name"]}
    )
    
    return {"status": "email_sent"}
```

### Celery Task Integration

```python
from celery import Celery

celery_app = Celery('email_tasks')

@celery_app.task
def send_campaign_email(campaign_id: str):
    """Send campaign emails as background task."""
    asyncio.run(email_service.execute_campaign(campaign_id))

@celery_app.task
def process_email_workflows():
    """Process automated email workflows."""
    asyncio.run(email_service.setup_automated_workflows())
```

## Next Steps

- [Document Processing](document-processing.md) - Generate email attachments
- [Automated Workflows](automated-workflows.md) - Advanced workflow integration
- [Performance Metrics](performance-metrics.md) - Monitor email performance
