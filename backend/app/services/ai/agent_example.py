"""
AI Agent Usage Example

This module demonstrates how to use the AI agent for the "Resolve with AI" functionality.
This example shows how the agent will be integrated with the dashboard.
"""

import asyncio
import logging
from typing import Dict, Any
from app.services.ai.agent import query_agent, get_agent, reset_agent
from app.core.ai_config import ai_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_agent_usage():
    """
    Demonstrate various use cases for the AI agent
    """
    print("🤖 AI Agent Usage Demonstration")
    print("=" * 50)
    
    # Check configuration
    print("\n📋 Configuration Status:")
    config = ai_config.get_safe_config()
    print(f"Google API Key: {'✅ Configured' if config['google_api_key_configured'] else '❌ Missing'}")
    print(f"RAG Enabled: {'✅ Yes' if config['rag_enabled'] else '❌ No'}")
    print(f"Web Search: {'✅ Enabled' if config['web_search_enabled'] else '❌ Disabled'}")
    print(f"Serper API Key: {'✅ Configured' if config['serper_api_key_configured'] else '❌ Missing'}")
    
    # Example queries that would come from the "Resolve with AI" button
    example_queries = [
        {
            "query": "How do I reset my password?",
            "description": "Company policy question - should use knowledge base"
        },
        {
            "query": "What are the latest cybersecurity trends in 2024?",
            "description": "External information - should use web search"
        },
        {
            "query": "What is our company's vacation policy?",
            "description": "Internal policy - should use knowledge base"
        },
        {
            "query": "How to install Python on Windows?",
            "description": "General tech question - might use both sources"
        }
    ]
    
    print("\n🔍 Testing Agent Queries:")
    print("-" * 30)
    
    for i, example in enumerate(example_queries, 1):
        print(f"\n{i}. Query: {example['query']}")
        print(f"   Expected: {example['description']}")
        
        try:
            # Query the agent (this is how it will be called from the dashboard)
            result = query_agent(
                query=example['query'],
                session_id=f"demo_session_{i}"
            )
            
            print(f"   ✅ Response: {result['answer'][:100]}...")
            print(f"   📊 Metadata: Query length: {result['metadata']['query_length']}, "
                  f"Response length: {result['metadata']['response_length']}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Demo completed!")


def simulate_dashboard_integration():
    """
    Simulate how the agent would be integrated with the dashboard's "Resolve with AI" button
    """
    print("\n🎯 Dashboard Integration Simulation")
    print("=" * 40)
    
    # This is how the agent would be called from the dashboard endpoint
    def resolve_with_ai(user_query: str, user_id: str = None) -> Dict[str, Any]:
        """
        Simulate the dashboard's "Resolve with AI" functionality
        
        Args:
            user_query: The user's question
            user_id: Optional user ID for session tracking
            
        Returns:
            Response dictionary for the frontend
        """
        try:
            # Generate session ID
            session_id = f"user_{user_id}" if user_id else None
            
            # Query the agent
            result = query_agent(user_query, session_id=session_id)
            
            # Format response for frontend
            return {
                "success": True,
                "answer": result["answer"],
                "sources": result["sources"],
                "session_id": result["session_id"],
                "metadata": {
                    "tools_used": result["metadata"].get("tools_available", []),
                    "response_time": "< 1s",  # Would be calculated in real implementation
                    "confidence": "high"  # Would be determined by agent
                }
            }
            
        except Exception as e:
            logger.error(f"AI resolution failed: {str(e)}")
            return {
                "success": False,
                "error": "I'm currently unable to process your request. Please contact support.",
                "fallback_message": "For immediate assistance, please create a ticket or contact the appropriate support team."
            }
    
    # Test the integration
    test_queries = [
        "How do I request time off?",
        "My computer won't start, what should I do?",
        "What's the latest version of Microsoft Office?"
    ]
    
    for query in test_queries:
        print(f"\n📝 User Query: {query}")
        response = resolve_with_ai(query, user_id="demo_user")
        
        if response["success"]:
            print(f"✅ AI Response: {response['answer'][:100]}...")
            print(f"📚 Sources: {', '.join(response['sources'])}")
        else:
            print(f"❌ Error: {response['error']}")


def test_agent_tools_individually():
    """
    Test individual agent tools to verify functionality
    """
    print("\n🔧 Individual Tool Testing")
    print("=" * 30)
    
    # Test RAG tool
    print("\n1. Testing Knowledge Base Tool:")
    try:
        from app.services.ai.agent import query_knowledge_base
        result = query_knowledge_base("company policy")
        print(f"   ✅ Knowledge Base Response: {result[:100]}...")
    except Exception as e:
        print(f"   ❌ Knowledge Base Error: {str(e)}")
    
    # Test Web Search tool
    print("\n2. Testing Web Search Tool:")
    try:
        from app.services.ai.agent import search_web
        result = search_web("latest technology trends")
        print(f"   ✅ Web Search Response: {result[:100]}...")
    except Exception as e:
        print(f"   ❌ Web Search Error: {str(e)}")


def main():
    """
    Main demonstration function
    """
    print("🚀 Starting AI Agent Demonstration")
    
    # Test individual tools
    test_agent_tools_individually()
    
    # Simulate dashboard integration
    simulate_dashboard_integration()
    
    # Run full agent demonstration
    asyncio.run(demonstrate_agent_usage())
    
    print("\n🎉 All demonstrations completed!")
    print("\nNext Steps:")
    print("1. Configure environment variables (GOOGLE_API_KEY, SERPER_API_KEY)")
    print("2. Integrate with dashboard 'Resolve with AI' button")
    print("3. Add endpoint in routers/ai_bot.py for frontend integration")
    print("4. Test with real user queries")


if __name__ == "__main__":
    main()
