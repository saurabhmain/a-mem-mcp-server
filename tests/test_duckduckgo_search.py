"""Test DuckDuckGo search directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.utils.researcher_tools import search_duckduckgo

def test_search():
    query = "Python async programming"
    print(f"Testing search for: {query}")
    print()
    
    results = search_duckduckgo(query, max_results=5)
    
    print(f"Found {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.get('title', 'N/A')}")
        print(f"   URL: {r.get('url', 'N/A')[:80]}...")
        print(f"   Snippet: {r.get('snippet', 'N/A')[:100]}...")
        print()

if __name__ == "__main__":
    test_search()

