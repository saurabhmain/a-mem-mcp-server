#!/usr/bin/env python3
"""
Integrated Test for Researcher Agent

This script demonstrates how the Researcher Agent works when called
by the AI assistant, which has access to MCP tools.

The assistant will:
1. Call mcp_getweb_felo-search to search the web
2. Extract top URLs from results
3. Call mcp_getweb_jina-reader for each URL
4. Feed results to ResearcherAgent to create notes
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


async def test_researcher_with_real_mcp(query: str):
    """
    Tests researcher by having the AI assistant call MCP tools.
    
    This function will be executed by the AI assistant, which has
    direct access to MCP tools via the MCP server.
    """
    print("=" * 60)
    print("🧪 Testing Researcher Agent with REAL MCP Tools")
    print("=" * 60)
    print(f"\nQuery: {query}\n")
    
    # Initialize researcher
    llm = LLMService()
    researcher = ResearcherAgent(llm_service=llm)
    
    # Step 1: Search web using felo-search (AI assistant will call this)
    print("[STEP 1] Searching web with felo-search...")
    # The AI assistant will call: mcp_getweb_felo-search(query=query)
    # and pass the results to us
    
    # For now, we'll demonstrate the workflow
    # In actual execution, the assistant will make the MCP calls
    
    return researcher, query


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integrated Test for Researcher Agent (requires AI assistant with MCP tools)"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Python async web scraping best practices 2025",
        help="Research query"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📋 Researcher Agent Test")
    print("=" * 60)
    print(f"\nQuery: {args.query}\n")
    print("This test will be executed by the AI assistant,")
    print("which has access to MCP tools (felo-search, jina-reader).\n")
    print("The assistant will:")
    print("  1. Call felo-search to find relevant URLs")
    print("  2. Extract content from top URLs using jina-reader")
    print("  3. Create AtomicNotes from the research results\n")
    print("=" * 60)

