#!/usr/bin/env python3
"""
Full Test for Researcher Agent with Real MCP Tools

This test demonstrates the complete workflow:
1. Search web (via MCP tools - called by AI assistant)
2. Extract content (via MCP tools - called by AI assistant)
3. Create notes from research
4. Store notes in A-MEM
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from a_mem.utils.researcher import ResearcherAgent
from a_mem.utils.llm import LLMService
from a_mem.core.logic import MemoryController
from a_mem.models.note import NoteInput


async def test_researcher_full_workflow():
    """Full workflow test with real extracted content."""
    print("=" * 60)
    print("🧪 Full Researcher Agent Test")
    print("=" * 60)
    
    query = "Python async web scraping best practices"
    
    # Real content extracted from jina-reader (from previous MCP call)
    extracted_content = [{
        "url": "https://www.scrapingbee.com/blog/async-scraping-in-python/",
        "content": """How to use asyncio to scrape websites with Python.

asyncio is part of Python's standard library which enables concurrency using async/await syntax.

Key concepts:
- Coroutines: async functions executed concurrently
- Tasks: Components for scheduling coroutines
- Futures: Return values of coroutines

Best practices:
- Use aiohttp for async HTTP requests
- Use asyncio.create_task() for concurrent execution
- Use asyncio.gather() to wait for multiple tasks
- Handle errors with try/except in async context

Example:
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

This approach allows scraping multiple URLs concurrently without threads."""
    }]
    
    print(f"\nQuery: {query}")
    print(f"Extracted content from: {len(extracted_content)} source(s)\n")
    
    # Initialize researcher
    llm = LLMService()
    researcher = ResearcherAgent(llm_service=llm)
    
    # Create notes from research
    print("[STEP] Creating notes from research...\n")
    notes = await researcher._create_notes_from_research(
        query=query,
        extracted_content=extracted_content,
        context="Full workflow test"
    )
    
    print(f"\n✅ Created {len(notes)} note(s)\n")
    
    # Store notes in A-MEM
    controller = MemoryController()
    notes_stored = []
    
    for note in notes:
        try:
            note_input = NoteInput(
                content=note.content,
                source="researcher_agent"
            )
            note_id = await controller.create_note(note_input)
            notes_stored.append(note_id)
            print(f"✅ Stored note: {note_id[:8]}... - {note.contextual_summary[:50]}")
        except Exception as e:
            print(f"❌ Error storing note: {e}")
    
    print(f"\n✅ Total: {len(notes_stored)} notes stored in A-MEM")
    
    return notes_stored


if __name__ == "__main__":
    try:
        stored = asyncio.run(test_researcher_full_workflow())
        print(f"\n🎉 Test successful! {len(stored)} notes stored")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

