"""Test script for local Jina Reader integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.utils.researcher_tools import extract_with_jina_reader
from a_mem.config import settings

def test_local_jina():
    """Test local Jina Reader extraction."""
    print("=" * 60)
    print("🧪 Testing Local Jina Reader Integration")
    print("=" * 60)
    print()
    
    print(f"📡 Configuration:")
    print(f"   JINA_READER_ENABLED: {settings.JINA_READER_ENABLED}")
    print(f"   JINA_READER_URL: {settings.JINA_READER_URL}")
    print()
    
    test_url = "https://www.scrapingbee.com/blog/async-scraping-in-python/"
    print(f"🔗 Testing URL: {test_url}")
    print()
    
    try:
        content = extract_with_jina_reader(test_url, max_length=1000, use_local=True)
        
        if content:
            print(f"✅ Success!")
            print(f"   Content length: {len(content)} chars")
            print(f"   Preview (first 300 chars):")
            print(f"   {'-' * 60}")
            print(f"   {content[:300]}...")
            print(f"   {'-' * 60}")
        else:
            print("❌ Failed: No content extracted")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_local_jina()

