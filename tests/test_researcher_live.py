#!/usr/bin/env python3
"""
Live Test Script for Researcher Agent with Real MCP Tools

This script uses the actual MCP tools available in Cursor to test
the Researcher Agent with real web searches and content extraction.

Usage in Cursor:
    Just ask: "Test researcher with query: Python async web scraping"
    
Or run directly (if MCP tools are available):
    python tools/test_researcher_live.py "your query"
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


async def test_researcher_live(query: str):
    """
    Tests researcher with REAL MCP tools (felo-search, jina-reader).
    
    This function will be called by the AI assistant in Cursor,
    which has access to MCP tools via the MCP server.
    """
    print("=" * 60)
    print("🧪 Testing Researcher Agent with REAL MCP Tools")
    print("=" * 60)
    print(f"\nQuery: {query}\n")
    
    # Initialize researcher
    llm = LLMService()
    researcher = ResearcherAgent(llm_service=llm)
    
    # Step 1: Search web using felo-search (via MCP)
    print("[STEP 1] Searching web with felo-search...")
    # Note: MCP tools are called by the AI assistant, not directly here
    # The assistant will call mcp_getweb_felo-search and pass results
    
    # For demonstration, we'll create a wrapper that the assistant can use
    # The actual MCP calls happen via the assistant's tool calls
    
    return researcher


def create_research_workflow(query: str):
    """
    Creates a research workflow that the AI assistant can execute.
    
    Returns instructions for the assistant to:
    1. Call mcp_getweb_felo-search with the query
    2. Extract top 3-5 URLs
    3. Call mcp_getweb_jina-reader for each URL
    4. Feed results to ResearcherAgent
    """
    workflow = {
        "query": query,
        "steps": [
            {
                "step": 1,
                "action": "search",
                "tool": "mcp_getweb_felo-search",
                "params": {"query": query},
                "description": "Search web for technical content"
            },
            {
                "step": 2,
                "action": "extract",
                "tool": "mcp_getweb_jina-reader",
                "params": {"url": "<from_step_1>", "maxLength": 10000},
                "description": "Extract content from top URLs"
            },
            {
                "step": 3,
                "action": "create_notes",
                "tool": "ResearcherAgent._create_notes_from_research",
                "params": {"query": query, "extracted_content": "<from_step_2>"},
                "description": "Create AtomicNotes from research"
            }
        ]
    }
    return workflow


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Live Test for Researcher Agent (requires MCP tools)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Python async web scraping best practices",
        help="Research query"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📋 Research Workflow Instructions")
    print("=" * 60)
    print("\nThis script provides a workflow for testing the Researcher Agent.")
    print("The AI assistant in Cursor will execute the MCP tool calls.\n")
    
    workflow = create_research_workflow(args.query)
    
    print(f"Query: {workflow['query']}\n")
    print("Steps:")
    for step in workflow["steps"]:
        print(f"  {step['step']}. {step['description']}")
        print(f"     Tool: {step['tool']}")
        print(f"     Params: {step['params']}\n")
    
    print("=" * 60)
    print("💡 To execute this workflow, ask the AI assistant:")
    print(f"   'Test researcher with query: {args.query}'")
    print("=" * 60)

