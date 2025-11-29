"""Test research_and_store tool directly."""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.main import call_tool

async def test_research():
    """Test research_and_store with query."""
    print("=" * 60)
    print("🔍 Testing research_and_store")
    print("=" * 60)
    print()
    
    query = "knowledge graph systems comparison"
    print(f"Query: {query}")
    print(f"Max sources: 1 (default)")
    print()
    
    try:
        result = await call_tool("research_and_store", {
            "query": query,
            "context": "Testing research_and_store tool"
        })
        
        if result and len(result) > 0:
            response_text = result[0].text if hasattr(result[0], 'text') else str(result[0])
            response_data = json.loads(response_text)
            
            print("Response:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            print()
            
            if response_data.get("status") == "success":
                print(f"✅ Success: {response_data.get('notes_stored', 0)} notes stored")
                if response_data.get("stored_notes"):
                    print("\nStored notes:")
                    for note in response_data["stored_notes"]:
                        print(f"  - ID: {note.get('id', '')[:8]}...")
                        print(f"    Summary: {note.get('summary', '')[:80]}")
                        print(f"    Type: {note.get('type', 'N/A')}")
                        print(f"    Source URL: {note.get('source_url', 'N/A')}")
                        print()
            else:
                print(f"⚠️  Status: {response_data.get('status', 'unknown')}")
                print(f"Message: {response_data.get('message', 'No message')}")
        else:
            print("❌ No response received")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_research())

