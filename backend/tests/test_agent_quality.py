"""
Quick test script to verify the improved AI agent quality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.agent import query_agent, search_web, query_knowledge_base
from app.core.ai_config import ai_config

def test_individual_tools():
    """Test individual tools to see their responses"""
    print("🔧 Testing Individual Tools")
    print("=" * 40)
    
    # Test knowledge base tool
    print("\n1. Testing Knowledge Base Tool:")
    try:
        kb_result = query_knowledge_base("company vacation policy")
        print(f"   Result: {kb_result[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test web search tool
    print("\n2. Testing Web Search Tool:")
    try:
        web_result = search_web("current price of Apple stock")
        print(f"   Result: {web_result[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")

def test_agent_responses():
    """Test the full agent with various queries"""
    print("\n🤖 Testing Full Agent Responses")
    print("=" * 40)
    
    test_queries = [
        "What is the current price of media stock?",
        "How do I troubleshoot my wifi connection?",
        "What are the latest cybersecurity trends?",
        "How do I reset my password?",
        "What is Python programming language?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        try:
            result = query_agent(query, session_id=f"test_{i}")
            print(f"   ✅ Response: {result['answer'][:300]}...")
            print(f"   📊 Length: {result['metadata']['response_length']} chars")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_configuration():
    """Check if the agent is properly configured"""
    print("📋 Configuration Check")
    print("=" * 25)
    
    config = ai_config.get_safe_config()
    print(f"Google API Key: {'✅ Configured' if config['google_api_key_configured'] else '❌ Missing'}")
    print(f"RAG Enabled: {'✅ Yes' if config['rag_enabled'] else '❌ No'}")
    print(f"Web Search: {'✅ Enabled' if config['web_search_enabled'] else '❌ Disabled'}")
    print(f"Serper API Key: {'✅ Configured' if config['serper_api_key_configured'] else '❌ Missing'}")
    print(f"Gemini Model: {config['gemini_model']}")
    print(f"Temperature: {config['gemini_temperature']}")

def main():
    """Run all tests"""
    print("🚀 AI Agent Quality Test")
    print("=" * 30)
    
    # Check configuration first
    check_configuration()
    
    # Test individual tools
    test_individual_tools()
    
    # Test full agent
    test_agent_responses()
    
    print("\n✅ Testing completed!")
    print("\nIf you see poor responses, check:")
    print("1. Environment variables are set correctly")
    print("2. API keys are valid and have quota")
    print("3. Network connectivity")
    print("4. Agent system prompt is being followed")

if __name__ == "__main__":
    main()
