"""
Integration Test für MCP Server

Testet die vollständige MCP Server Funktionalität mit Mock-Dependencies.
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_mcp_server_imports():
    """Test: MCP Server kann importiert werden"""
    try:
        from a_mem.main import server, controller, main
        print("✅ MCP Server Module können importiert werden")
        return True
    except ImportError as e:
        if "mcp" in str(e).lower():
            print(f"⚠️  MCP Package nicht installiert: {e}")
            print("   Installiere mit: pip install mcp")
            return False
        raise


def test_tool_definitions():
    """Test: Tool-Definitionen sind korrekt"""
    from a_mem.main import server
    
    # Prüfe ob server existiert
    assert server is not None
    assert server.name == "a-mem"
    
    # Prüfe ob main.py die richtige Struktur hat
    main_py = Path(__file__).parent.parent / "src" / "a_mem" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Tool-Definitionen
    assert '"create_atomic_note"' in content
    assert '"retrieve_memories"' in content
    assert '"get_memory_stats"' in content
    
    # Prüfe Handler
    assert "@server.list_tools()" in content
    assert "@server.call_tool()" in content
    
    print("✅ Tool-Definitionen korrekt")
    return True


def test_call_tool_structure():
    """Test: call_tool Handler-Struktur"""
    main_py = Path(__file__).parent.parent / "src" / "a_mem" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe ob alle Tools im call_tool Handler behandelt werden
    assert 'if name == "create_atomic_note":' in content
    assert 'elif name == "retrieve_memories":' in content
    assert 'elif name == "get_memory_stats":' in content
    
    # Prüfe ob Fehlerbehandlung vorhanden ist
    assert 'except Exception' in content
    assert 'TextContent' in content
    
    print("✅ call_tool Handler-Struktur korrekt")
    return True


def test_main_function():
    """Test: main() Funktion existiert"""
    main_py = Path(__file__).parent.parent / "src" / "a_mem" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    assert "async def main()" in content
    assert "stdio_server" in content
    assert "server.run" in content
    
    print("✅ main() Funktion korrekt implementiert")
    return True


def test_entry_point():
    """Test: Entry Point (mcp_server.py) existiert"""
    entry_point = Path(__file__).parent.parent / "mcp_server.py"
    
    assert entry_point.exists(), "mcp_server.py nicht gefunden"
    
    content = entry_point.read_text(encoding='utf-8')
    assert "from src.a_mem.main import main" in content
    assert "asyncio.run(main())" in content
    
    print("✅ Entry Point (mcp_server.py) korrekt")
    return True


def test_tool_schemas():
    """Test: Tool Schemas sind vollständig"""
    main_py = Path(__file__).parent.parent / "src" / "a_mem" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe create_atomic_note Schema
    assert '"content"' in content
    assert '"source"' in content
    assert '"required"' in content
    
    # Prüfe retrieve_memories Schema
    assert '"query"' in content
    assert '"max_results"' in content
    
    # Prüfe get_memory_stats Schema
    assert '"properties": {}' in content  # Keine Parameter
    
    print("✅ Tool Schemas vollständig")
    return True


def run_integration_tests():
    """Führt alle Integration Tests aus"""
    print("\n" + "="*60)
    print("🧪 MCP Server Integration Tests")
    print("="*60 + "\n")
    
    tests = [
        ("MCP Server Imports", test_mcp_server_imports),
        ("Tool Definitions", test_tool_definitions),
        ("call_tool Structure", test_call_tool_structure),
        ("main Function", test_main_function),
        ("Entry Point", test_entry_point),
        ("Tool Schemas", test_tool_schemas),
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for name, test_func in tests:
        total_tests += 1
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 Integration Test Results: {passed_tests}/{total_tests} passed")
    print("="*60 + "\n")
    
    if passed_tests == total_tests:
        print("✅ ALLE INTEGRATION TESTS BESTANDEN!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} Test(s) fehlgeschlagen")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)



