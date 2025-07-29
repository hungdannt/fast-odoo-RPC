#!/usr/bin/env python3
"""
AI-Powered Customer Service Automation System

This example demonstrates a production-ready customer service automation using
Zenoo RPC's AI capabilities for:
- Intelligent ticket routing and prioritization
- AI-powered chatbot with context awareness
- Automated response generation
- Sentiment analysis and escalation
- Customer satisfaction prediction
- Knowledge base integration

Based on real-world Gemini API production patterns for customer service.
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager

from zenoo_rpc import ZenooClient
from zenoo_rpc.exceptions import ZenooError


# Configure logging for customer service operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('customer_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class SentimentScore(Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class CustomerTicket:
    """Customer support ticket with AI analysis."""
    id: Optional[int]
    subject: str
    description: str
    customer_id: int
    priority: TicketPriority
    category: str
    sentiment: SentimentScore
    urgency_score: float
    estimated_resolution_time: int  # minutes
    suggested_agent: Optional[str]
    ai_summary: str
    recommended_actions: List[str]
    created_at: datetime


@dataclass
class ChatbotResponse:
    """AI chatbot response with context."""
    message: str
    confidence: float
    intent: str
    entities: Dict[str, Any]
    requires_human: bool
    suggested_actions: List[str]
    escalation_reason: Optional[str]


@dataclass
class CustomerInsight:
    """AI-generated customer insight."""
    customer_id: int
    satisfaction_score: float
    churn_risk: str  # 'low', 'medium', 'high'
    value_segment: str  # 'low', 'medium', 'high', 'vip'
    communication_preference: str
    key_issues: List[str]
    recommendations: List[str]


class CustomerServiceAutomation:
    """
    Production-ready customer service automation with AI capabilities.
    
    Features:
    - Intelligent ticket classification and routing
    - AI-powered chatbot with natural language understanding
    - Automated response generation and suggestions
    - Real-time sentiment analysis and escalation
    - Customer behavior analysis and insights
    - Performance monitoring and optimization
    """
    
    def __init__(self, odoo_url: str, database: str, username: str, password: str):
        self.odoo_url = odoo_url
        self.database = database
        self.username = username
        self.password = password
        self.client: Optional[ZenooClient] = None
        self.knowledge_base = {}
        self.conversation_context = {}
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager for Odoo client with customer service configuration."""
        client = ZenooClient(self.odoo_url)
        try:
            await client.login(self.database, self.username, self.password)
            
            # Setup AI for customer service
            await client.setup_ai(
                provider="gemini",
                model="gemini-2.5-flash-lite",  # Fast responses for customer service
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.2,  # Balanced creativity for customer interactions
                max_tokens=4096,
                timeout=15.0,  # Quick response for real-time chat
                max_retries=3
            )
            
            yield client
            
        except Exception as e:
            logger.error(f"Customer service client setup failed: {e}")
            raise
        finally:
            await client.close()
    
    async def process_incoming_ticket(self, ticket_data: Dict) -> CustomerTicket:
        """Process incoming customer ticket with AI analysis."""
        
        async with self.get_client() as client:
            logger.info(f"Processing ticket: {ticket_data.get('subject', 'No subject')}")
            
            # Get customer history for context
            customer_history = await self._get_customer_history(client, ticket_data['customer_id'])
            
            # AI analysis of the ticket
            ticket_analysis = await client.ai.chat(
                f"Analyze this customer support ticket:\n"
                f"Subject: {ticket_data['subject']}\n"
                f"Description: {ticket_data['description']}\n"
                f"Customer History: {json.dumps(customer_history, default=str)}\n"
                f"Provide:\n"
                f"1. Priority level (low/medium/high/urgent/critical)\n"
                f"2. Category classification\n"
                f"3. Sentiment analysis (very_negative/negative/neutral/positive/very_positive)\n"
                f"4. Urgency score (0.0-1.0)\n"
                f"5. Estimated resolution time in minutes\n"
                f"6. Suggested agent type or department\n"
                f"7. Brief summary and recommended actions\n"
                f"Respond with JSON format.",
                context="Customer ticket analysis and routing"
            )
            
            try:
                analysis = json.loads(ticket_analysis)
                
                # Create ticket object with AI insights
                ticket = CustomerTicket(
                    id=None,  # Will be set when created in Odoo
                    subject=ticket_data['subject'],
                    description=ticket_data['description'],
                    customer_id=ticket_data['customer_id'],
                    priority=TicketPriority(analysis.get('priority', 'medium')),
                    category=analysis.get('category', 'general'),
                    sentiment=SentimentScore(analysis.get('sentiment', 'neutral')),
                    urgency_score=float(analysis.get('urgency_score', 0.5)),
                    estimated_resolution_time=int(analysis.get('estimated_resolution_time', 60)),
                    suggested_agent=analysis.get('suggested_agent'),
                    ai_summary=analysis.get('summary', ''),
                    recommended_actions=analysis.get('recommended_actions', []),
                    created_at=datetime.now()
                )
                
                # Create ticket in Odoo
                ticket_id = await self._create_ticket_in_odoo(client, ticket)
                ticket.id = ticket_id
                
                # Auto-route if possible
                await self._auto_route_ticket(client, ticket)
                
                # Check for escalation
                if ticket.priority in [TicketPriority.URGENT, TicketPriority.CRITICAL]:
                    await self._escalate_ticket(client, ticket)
                
                logger.info(f"Ticket processed: ID={ticket_id}, Priority={ticket.priority.value}")
                return ticket
                
            except json.JSONDecodeError as e:
                logger.error(f"Ticket analysis parsing failed: {e}")
                # Fallback to basic ticket creation
                return await self._create_basic_ticket(client, ticket_data)
    
    async def chatbot_respond(self, customer_id: int, message: str, 
                            conversation_id: str) -> ChatbotResponse:
        """Generate AI chatbot response with context awareness."""
        
        async with self.get_client() as client:
            # Get conversation context
            context = self.conversation_context.get(conversation_id, [])
            
            # Get customer information
            customer_info = await self._get_customer_info(client, customer_id)
            
            # Get relevant knowledge base entries
            kb_entries = await self._search_knowledge_base(client, message)
            
            # AI chatbot response generation
            chatbot_analysis = await client.ai.chat(
                f"Generate a helpful customer service response:\n"
                f"Customer Message: {message}\n"
                f"Customer Info: {json.dumps(customer_info, default=str)}\n"
                f"Conversation History: {json.dumps(context[-5:], default=str)}\n"  # Last 5 messages
                f"Knowledge Base: {json.dumps(kb_entries, default=str)}\n"
                f"Provide:\n"
                f"1. Helpful response message\n"
                f"2. Confidence level (0.0-1.0)\n"
                f"3. Detected intent\n"
                f"4. Extracted entities\n"
                f"5. Whether human agent is needed\n"
                f"6. Suggested actions\n"
                f"7. Escalation reason if needed\n"
                f"Be empathetic, professional, and solution-focused.\n"
                f"Respond with JSON format.",
                context="Customer service chatbot response"
            )
            
            try:
                response_data = json.loads(chatbot_analysis)
                
                response = ChatbotResponse(
                    message=response_data.get('message', 'I apologize, but I need a moment to process your request.'),
                    confidence=float(response_data.get('confidence', 0.5)),
                    intent=response_data.get('intent', 'unknown'),
                    entities=response_data.get('entities', {}),
                    requires_human=response_data.get('requires_human', False),
                    suggested_actions=response_data.get('suggested_actions', []),
                    escalation_reason=response_data.get('escalation_reason')
                )
                
                # Update conversation context
                context.append({
                    'timestamp': datetime.now().isoformat(),
                    'customer_message': message,
                    'bot_response': response.message,
                    'intent': response.intent
                })
                self.conversation_context[conversation_id] = context
                
                # Log interaction for analysis
                await self._log_chatbot_interaction(client, customer_id, message, response)
                
                return response
                
            except json.JSONDecodeError as e:
                logger.error(f"Chatbot response parsing failed: {e}")
                # Fallback response
                return ChatbotResponse(
                    message="I apologize for the technical difficulty. Let me connect you with a human agent.",
                    confidence=0.0,
                    intent="technical_error",
                    entities={},
                    requires_human=True,
                    suggested_actions=["escalate_to_human"],
                    escalation_reason="AI processing error"
                )
    
    async def analyze_customer_satisfaction(self, customer_id: int) -> CustomerInsight:
        """Analyze customer satisfaction and generate insights."""
        
        async with self.get_client() as client:
            # Get comprehensive customer data
            customer_data = await self._get_comprehensive_customer_data(client, customer_id)
            
            # AI analysis for customer insights
            insight_analysis = await client.ai.chat(
                f"Analyze this customer's satisfaction and behavior:\n"
                f"Customer Data: {json.dumps(customer_data, default=str)}\n"
                f"Analyze:\n"
                f"1. Overall satisfaction score (0.0-1.0)\n"
                f"2. Churn risk level (low/medium/high)\n"
                f"3. Customer value segment (low/medium/high/vip)\n"
                f"4. Preferred communication style\n"
                f"5. Key issues and pain points\n"
                f"6. Specific recommendations for improvement\n"
                f"Consider: ticket history, response times, resolution rates, feedback.\n"
                f"Respond with JSON format.",
                context="Customer satisfaction and behavior analysis"
            )
            
            try:
                insight_data = json.loads(insight_analysis)
                
                insight = CustomerInsight(
                    customer_id=customer_id,
                    satisfaction_score=float(insight_data.get('satisfaction_score', 0.5)),
                    churn_risk=insight_data.get('churn_risk', 'medium'),
                    value_segment=insight_data.get('value_segment', 'medium'),
                    communication_preference=insight_data.get('communication_preference', 'email'),
                    key_issues=insight_data.get('key_issues', []),
                    recommendations=insight_data.get('recommendations', [])
                )
                
                # Store insights in Odoo for future reference
                await self._store_customer_insights(client, insight)
                
                return insight
                
            except json.JSONDecodeError as e:
                logger.error(f"Customer insight parsing failed: {e}")
                # Return basic insight
                return CustomerInsight(
                    customer_id=customer_id,
                    satisfaction_score=0.5,
                    churn_risk='medium',
                    value_segment='medium',
                    communication_preference='email',
                    key_issues=[],
                    recommendations=[]
                )
    
    async def generate_response_suggestions(self, ticket_id: int) -> List[str]:
        """Generate AI-powered response suggestions for agents."""
        
        async with self.get_client() as client:
            # Get ticket details
            ticket_data = await self._get_ticket_details(client, ticket_id)
            
            # Get similar resolved tickets
            similar_tickets = await self._find_similar_tickets(client, ticket_data)
            
            # AI response suggestions
            suggestions_analysis = await client.ai.chat(
                f"Generate response suggestions for this customer service ticket:\n"
                f"Ticket: {json.dumps(ticket_data, default=str)}\n"
                f"Similar Resolved Tickets: {json.dumps(similar_tickets, default=str)}\n"
                f"Generate 3-5 different response approaches:\n"
                f"1. Empathetic and solution-focused\n"
                f"2. Technical and detailed\n"
                f"3. Quick resolution if possible\n"
                f"4. Escalation if needed\n"
                f"Each suggestion should be professional and actionable.\n"
                f"Respond with JSON array of suggestion strings.",
                context="Customer service response suggestions"
            )
            
            try:
                suggestions = json.loads(suggestions_analysis)
                return suggestions if isinstance(suggestions, list) else []
                
            except json.JSONDecodeError as e:
                logger.error(f"Response suggestions parsing failed: {e}")
                return ["I understand your concern and will investigate this issue immediately."]
    
    async def _get_customer_history(self, client: ZenooClient, customer_id: int) -> Dict:
        """Get customer's support history."""
        
        # Get recent tickets
        tickets = await client.search_read(
            'helpdesk.ticket',
            [('partner_id', '=', customer_id)],
            ['name', 'stage_id', 'priority', 'create_date'],
            limit=10
        )
        
        # Get customer info
        customer = await client.read('res.partner', [customer_id], ['name', 'email', 'phone'])
        
        return {
            'customer_info': customer[0] if customer else {},
            'recent_tickets': tickets,
            'total_tickets': len(tickets)
        }
    
    async def _create_ticket_in_odoo(self, client: ZenooClient, ticket: CustomerTicket) -> int:
        """Create ticket in Odoo helpdesk."""
        
        ticket_data = {
            'name': ticket.subject,
            'description': ticket.description,
            'partner_id': ticket.customer_id,
            'priority': '1' if ticket.priority == TicketPriority.CRITICAL else '0',
            'tag_ids': [(6, 0, [])],  # Add relevant tags
        }
        
        return await client.create('helpdesk.ticket', ticket_data)
    
    async def _auto_route_ticket(self, client: ZenooClient, ticket: CustomerTicket):
        """Automatically route ticket to appropriate team/agent."""
        
        # AI-based routing logic would go here
        # For now, simple category-based routing
        routing_map = {
            'technical': 'Technical Support',
            'billing': 'Billing Department',
            'general': 'General Support'
        }
        
        team_name = routing_map.get(ticket.category, 'General Support')
        logger.info(f"Routing ticket {ticket.id} to {team_name}")
    
    async def _escalate_ticket(self, client: ZenooClient, ticket: CustomerTicket):
        """Escalate high-priority tickets."""
        
        logger.warning(f"Escalating {ticket.priority.value} priority ticket {ticket.id}")
        
        # Send notifications, update priority, assign to senior agents, etc.
        # Implementation would depend on specific escalation procedures
    
    async def _create_basic_ticket(self, client: ZenooClient, ticket_data: Dict) -> CustomerTicket:
        """Create basic ticket without AI analysis (fallback)."""
        
        ticket = CustomerTicket(
            id=None,
            subject=ticket_data['subject'],
            description=ticket_data['description'],
            customer_id=ticket_data['customer_id'],
            priority=TicketPriority.MEDIUM,
            category='general',
            sentiment=SentimentScore.NEUTRAL,
            urgency_score=0.5,
            estimated_resolution_time=120,
            suggested_agent=None,
            ai_summary='Basic ticket creation without AI analysis',
            recommended_actions=[],
            created_at=datetime.now()
        )
        
        ticket.id = await self._create_ticket_in_odoo(client, ticket)
        return ticket
    
    async def _get_customer_info(self, client: ZenooClient, customer_id: int) -> Dict:
        """Get customer information for chatbot context."""
        
        customer = await client.read(
            'res.partner', 
            [customer_id], 
            ['name', 'email', 'phone', 'category_id']
        )
        
        return customer[0] if customer else {}
    
    async def _search_knowledge_base(self, client: ZenooClient, query: str) -> List[Dict]:
        """Search knowledge base for relevant information."""
        
        # In a real implementation, this would search a knowledge base
        # For demo, return empty list
        return []
    
    async def _log_chatbot_interaction(self, client: ZenooClient, customer_id: int, 
                                     message: str, response: ChatbotResponse):
        """Log chatbot interaction for analysis."""
        
        # Log interaction data for performance analysis
        logger.info(f"Chatbot interaction: Customer {customer_id}, Intent: {response.intent}, Confidence: {response.confidence}")
    
    async def _get_comprehensive_customer_data(self, client: ZenooClient, customer_id: int) -> Dict:
        """Get comprehensive customer data for satisfaction analysis."""
        
        # Get customer basic info
        customer = await client.read('res.partner', [customer_id])
        
        # Get ticket history
        tickets = await client.search_read(
            'helpdesk.ticket',
            [('partner_id', '=', customer_id)],
            ['name', 'stage_id', 'priority', 'create_date', 'close_date']
        )
        
        # Get sales history
        orders = await client.search_read(
            'sale.order',
            [('partner_id', '=', customer_id)],
            ['name', 'state', 'amount_total', 'date_order']
        )
        
        return {
            'customer_info': customer[0] if customer else {},
            'tickets': tickets,
            'orders': orders
        }
    
    async def _store_customer_insights(self, client: ZenooClient, insight: CustomerInsight):
        """Store customer insights in Odoo."""
        
        # In a real implementation, this would store insights in a custom model
        logger.info(f"Storing insights for customer {insight.customer_id}: Satisfaction={insight.satisfaction_score}")
    
    async def _get_ticket_details(self, client: ZenooClient, ticket_id: int) -> Dict:
        """Get detailed ticket information."""
        
        ticket = await client.read('helpdesk.ticket', [ticket_id])
        return ticket[0] if ticket else {}
    
    async def _find_similar_tickets(self, client: ZenooClient, ticket_data: Dict) -> List[Dict]:
        """Find similar resolved tickets for reference."""
        
        # In a real implementation, this would use AI similarity search
        # For demo, return empty list
        return []


async def main():
    """Example usage of the Customer Service Automation system."""
    
    # Initialize automation system
    cs_automation = CustomerServiceAutomation(
        odoo_url="http://localhost:8069",
        database="demo",
        username="admin",
        password="admin"
    )
    
    try:
        # Example: Process incoming ticket
        logger.info("Processing incoming customer ticket...")
        
        ticket_data = {
            'subject': 'Unable to login to my account',
            'description': 'I have been trying to login for the past hour but keep getting error messages. This is very frustrating as I need to access my account urgently.',
            'customer_id': 1
        }
        
        ticket = await cs_automation.process_incoming_ticket(ticket_data)
        logger.info(f"Ticket processed: {ticket.subject} - Priority: {ticket.priority.value}")
        
        # Example: Chatbot interaction
        logger.info("Testing chatbot response...")
        
        chatbot_response = await cs_automation.chatbot_respond(
            customer_id=1,
            message="Hi, I'm having trouble with my recent order. It hasn't arrived yet.",
            conversation_id="conv_123"
        )
        
        logger.info(f"Chatbot response: {chatbot_response.message}")
        logger.info(f"Confidence: {chatbot_response.confidence}, Requires human: {chatbot_response.requires_human}")
        
        # Example: Customer satisfaction analysis
        logger.info("Analyzing customer satisfaction...")
        
        insight = await cs_automation.analyze_customer_satisfaction(customer_id=1)
        logger.info(f"Customer satisfaction: {insight.satisfaction_score}")
        logger.info(f"Churn risk: {insight.churn_risk}, Value segment: {insight.value_segment}")
        
        # Example: Response suggestions
        if ticket.id:
            logger.info("Generating response suggestions...")
            suggestions = await cs_automation.generate_response_suggestions(ticket.id)
            
            for i, suggestion in enumerate(suggestions, 1):
                logger.info(f"Suggestion {i}: {suggestion}")
        
    except Exception as e:
        logger.error(f"Customer service automation failed: {e}")
        raise


if __name__ == "__main__":
    import os
    
    # Ensure API key is set
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        exit(1)
    
    asyncio.run(main())
