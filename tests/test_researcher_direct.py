"""Test Researcher Agent with direct URL (bypassing search)."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.utils.researcher import ResearcherAgent
from a_mem.utils.llm import LLMService

async def test_researcher_direct():
    """Test Researcher Agent with known URLs."""
    print("=" * 60)
    print("🧪 Testing Researcher Agent (Direct URL Test)")
    print("=" * 60)
    print()
    
    researcher = ResearcherAgent(llm_service=LLMService())
    
    # Simulate search results with known URLs (mix of web and PDF)
    test_urls = [
        {
            "url": "https://www.scrapingbee.com/blog/async-scraping-in-python/",
            "title": "Async Scraping in Python",
            "snippet": "Learn how to use asyncio for web scraping"
        },
        {
            "url": "https://arxiv.org/pdf/2301.10608.pdf",
            "title": "Connecting metrics for shape-texture knowledge",
            "snippet": "Research paper on computer vision"
        }
    ]
    
    print("📡 Testing content extraction from URLs:")
    for url_info in test_urls:
        print(f"   - {url_info['url']}")
    print()
    
    # Test extraction
    extracted = await researcher._extract_content(test_urls)
    
    print(f"✅ Extracted content from {len(extracted)} URLs:")
    print()
    
    for i, item in enumerate(extracted, 1):
        print(f"{i}. URL: {item.get('url', 'N/A')[:60]}...")
        print(f"   Content length: {len(item.get('content', ''))} chars")
        print(f"   Preview: {item.get('content', '')[:150]}...")
        print()
    
    # Test note creation
    if extracted:
        print("📝 Testing note creation from extracted content...")
        print()
        
        notes = await researcher._create_notes_from_research(
            query="Python async programming and computer vision research",
            extracted_content=extracted,
            context="Direct URL test"
        )
        
        print(f"✅ Created {len(notes)} notes:")
        for i, note in enumerate(notes, 1):
            print(f"   {i}. ID: {note.id[:8]}...")
            print(f"      Type: {note.type}")
            print(f"      Summary: {note.contextual_summary[:80]}...")
            print(f"      Keywords: {', '.join(note.keywords[:3])}")
            print(f"      Tags: {', '.join(note.tags[:3])}")
            print()
    
    print("=" * 60)
    print("✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_researcher_direct())

