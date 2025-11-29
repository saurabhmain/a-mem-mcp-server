#!/usr/bin/env python3
"""
Test Script for Researcher Agent

Tests the Researcher Agent with actual MCP tools (GetWeb, Firecrawl).
Run this to verify the researcher works before integrating into A-MEM.
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


async def test_researcher_with_mcp(query: str):
    """
    Tests researcher with actual MCP tools.
    
    This function would need to be adapted to use actual MCP client calls.
    For now, it demonstrates the structure.
    """
    print("=" * 60)
    print("🧪 Testing Researcher Agent")
    print("=" * 60)
    print(f"\nQuery: {query}\n")
    
    # Initialize researcher
    llm = LLMService()
    researcher = ResearcherAgent(llm_service=llm)
    
    # Perform research
    notes = await researcher.research(
        query=query,
        context="Testing researcher agent functionality"
    )
    
    # Display results
    print("\n" + "=" * 60)
    print(f"✅ Research Complete: {len(notes)} notes created")
    print("=" * 60)
    
    for i, note in enumerate(notes, 1):
        print(f"\n--- Note {i} ---")
        print(f"ID: {note.id}")
        print(f"Type: {note.type}")
        print(f"Summary: {note.contextual_summary}")
        print(f"Keywords: {', '.join(note.keywords)}")
        print(f"Tags: {', '.join(note.tags)}")
        print(f"Content: {note.content[:200]}...")
        print(f"Source: {note.metadata.get('source_url', 'N/A')}")
    
    return notes


def test_researcher_sync(query: str):
    """Synchronous test wrapper."""
    return asyncio.run(test_researcher_with_mcp(query))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Researcher Agent")
    parser.add_argument(
        "query",
        nargs="?",
        default="Python async web scraping best practices 2025",
        help="Research query (default: Python async web scraping best practices 2025)"
    )
    
    args = parser.parse_args()
    
    try:
        test_researcher_sync(args.query)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

