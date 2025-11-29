"""Test script for Unstructured PDF extraction integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.utils.researcher_tools import extract_pdf_with_unstructured
from a_mem.config import settings

def test_unstructured_pdf():
    """Test Unstructured PDF extraction."""
    print("=" * 60)
    print("🧪 Testing Unstructured PDF Extraction")
    print("=" * 60)
    print()
    
    print(f"📡 Configuration:")
    print(f"   UNSTRUCTURED_ENABLED: {settings.UNSTRUCTURED_ENABLED}")
    print(f"   UNSTRUCTURED_API_URL: {settings.UNSTRUCTURED_API_URL}")
    print(f"   UNSTRUCTURED_USE_LIBRARY: {settings.UNSTRUCTURED_USE_LIBRARY}")
    print()
    
    # Test with a public PDF
    test_url = "https://arxiv.org/pdf/2301.10608.pdf"  # Example: A-Mem paper
    print(f"🔗 Testing PDF URL: {test_url}")
    print()
    
    try:
        content = extract_pdf_with_unstructured(test_url, max_length=2000)
        
        if content:
            print(f"✅ Success!")
            print(f"   Content length: {len(content)} chars")
            print(f"   Preview (first 500 chars):")
            print(f"   {'-' * 60}")
            print(f"   {content[:500]}...")
            print(f"   {'-' * 60}")
        else:
            print("❌ Failed: No content extracted")
            print()
            print("💡 Troubleshooting:")
            print("   1. Check if Unstructured is installed: pip install unstructured")
            print("   2. Or set UNSTRUCTURED_API_URL if using API")
            print("   3. Or set UNSTRUCTURED_USE_LIBRARY=true if library is installed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    test_unstructured_pdf()

