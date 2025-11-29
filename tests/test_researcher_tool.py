"""Test script for research_and_store MCP tool."""

import sys
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.main import call_tool
from mcp.types import TextContent

async def test_research_tool():
    """Test the research_and_store tool."""
    print("=" * 60)
    print("🧪 Testing research_and_store MCP Tool")
    print("=" * 60)
    print()
    
    # Test query - something that might find PDFs and web content
    # Using a more specific query that DuckDuckGo can handle
    test_query = "Python async programming best practices"
    print(f"🔍 Research Query: {test_query}")
    print()
    
    try:
        # Call the tool
        arguments = {
            "query": test_query,
            "context": "Testing Researcher Agent with PDF and web content extraction"
        }
        
        print("📡 Calling research_and_store tool...")
        print()
        
        result = await call_tool("research_and_store", arguments)
        
        # Parse result
        if result and len(result) > 0:
            content = result[0].text if hasattr(result[0], 'text') else str(result[0])
            data = json.loads(content)
            
            print("✅ Research completed!")
            print()
            print(f"📊 Results:")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Notes created: {data.get('notes_created', 0)}")
            print(f"   Notes stored: {data.get('notes_stored', 0)}")
            print(f"   Notes failed: {data.get('notes_failed', 0)}")
            print()
            
            if data.get('stored_notes'):
                print("📝 Stored Notes:")
                for i, note in enumerate(data['stored_notes'][:5], 1):  # Show first 5
                    print(f"   {i}. ID: {note.get('id', 'N/A')[:8]}...")
                    print(f"      Type: {note.get('type', 'N/A')}")
                    print(f"      Summary: {note.get('summary', 'N/A')[:80]}...")
                    print(f"      Source: {note.get('source_url', 'N/A')[:60]}...")
                    print()
            
            if data.get('failed_notes'):
                print("⚠️  Failed Notes:")
                for i, note in enumerate(data['failed_notes'], 1):
                    print(f"   {i}. Error: {note.get('error', 'N/A')}")
                    print()
            
            print("=" * 60)
            print("✅ Test completed successfully!")
            print("=" * 60)
        else:
            print("❌ No result returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_research_tool())

