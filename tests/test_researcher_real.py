#!/usr/bin/env python3
"""
Real Test for Researcher Agent with Actual MCP Data

This script tests the Researcher Agent with real data from MCP tools.
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


async def test_researcher_real():
    """Test researcher with real extracted content."""
    print("=" * 60)
    print("🧪 Testing Researcher Agent with REAL Data")
    print("=" * 60)
    
    # Initialize researcher
    llm = LLMService()
    researcher = ResearcherAgent(llm_service=llm)
    
    # Real content extracted from jina-reader
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
    
    query = "Python async web scraping best practices"
    context = "Testing researcher agent with real MCP data"
    
    print(f"\nQuery: {query}")
    print(f"Sources: {len(extracted_content)}")
    print("\n[STEP] Creating notes from research...\n")
    
    # Create notes
    notes = await researcher._create_notes_from_research(
        query=query,
        extracted_content=extracted_content,
        context=context
    )
    
    # Display results
    print("\n" + "=" * 60)
    print(f"✅ Research Complete: {len(notes)} notes created")
    print("=" * 60)
    
    for i, note in enumerate(notes, 1):
        print(f"\n--- Note {i} ---")
        print(f"ID: {note.id[:8]}...")
        print(f"Type: {note.type}")
        print(f"Summary: {note.contextual_summary}")
        print(f"Keywords: {', '.join(note.keywords)}")
        print(f"Tags: {', '.join(note.tags)}")
        print(f"Content: {note.content[:200]}...")
        if note.metadata:
            print(f"Source: {note.metadata.get('source_url', 'N/A')}")
            print(f"Query: {note.metadata.get('research_query', 'N/A')}")
    
    return notes


if __name__ == "__main__":
    try:
        notes = asyncio.run(test_researcher_real())
        print(f"\n✅ Test successful! Created {len(notes)} note(s)")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

