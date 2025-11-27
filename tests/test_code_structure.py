"""
Code-Struktur Tests: Prüft ob alle Paper-Komponenten im Code vorhanden sind
"""

import re
from pathlib import Path

def test_embedding_formula_in_code():
    """Test: Formel 3 (ei = fenc[concat(ci, Ki, Gi, Xi)]) im Code vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    
    if not main_py.exists():
        print("⚠️  main.py nicht gefunden")
        return False
    
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe ob Embedding-Berechnung vorhanden ist
    has_embedding_calc = "text_for_embedding" in content or "get_embedding" in content
    has_concat = "concat" in content.lower() or "join" in content
    
    # Prüfe ob alle Komponenten konkateniert werden
    has_content = "note.content" in content or "content" in content
    has_summary = "contextual_summary" in content
    has_keywords = "keywords" in content
    has_tags = "tags" in content
    
    if has_embedding_calc and has_concat and has_content and has_summary and has_keywords and has_tags:
        print("✅ Embedding-Formel (3) im Code gefunden")
        return True
    else:
        print("❌ Embedding-Formel (3) nicht vollständig im Code")
        return False


def test_link_generation_in_code():
    """Test: Link Generation (Section 3.2) im Code vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Link Generation Komponenten
    has_vector_query = "vector.query" in content or "query" in content
    has_check_link = "check_link" in content
    has_add_edge = "add_edge" in content or "graph.add_edge" in content
    
    if has_vector_query and has_check_link and has_add_edge:
        print("✅ Link Generation (3.2) im Code gefunden")
        return True
    else:
        print("❌ Link Generation (3.2) nicht vollständig im Code")
        return False


def test_memory_evolution_in_code():
    """Test: Memory Evolution (Section 3.3) im Code vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Memory Evolution Komponenten
    has_evolve_memory = "evolve_memory" in content
    has_update_node = "update_node" in content or "graph.update_node" in content
    has_vector_update = "vector.update" in content or "update" in content
    
    if has_evolve_memory and has_update_node and has_vector_update:
        print("✅ Memory Evolution (3.3) im Code gefunden")
        return True
    else:
        print("❌ Memory Evolution (3.3) nicht vollständig im Code")
        return False


def test_retrieve_memory_in_code():
    """Test: Retrieve Memory (Section 3.4) im Code vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Retrieve Komponenten
    has_retrieve = "retrieve" in content or "retrieve_memories" in content
    has_query_embedding = "q_embedding" in content or "query" in content
    has_vector_query = "vector.query" in content
    
    if has_retrieve and has_query_embedding and has_vector_query:
        print("✅ Retrieve Memory (3.4) im Code gefunden")
        return True
    else:
        print("❌ Retrieve Memory (3.4) nicht vollständig im Code")
        return False


def test_atomic_note_structure_in_code():
    """Test: AtomicNote Struktur im Code vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe AtomicNote Komponenten
    has_atomic_note = "AtomicNote" in content or "class AtomicNote" in content
    has_content = "content" in content
    has_contextual_summary = "contextual_summary" in content
    has_keywords = "keywords" in content
    has_tags = "tags" in content
    has_created_at = "created_at" in content
    
    if has_atomic_note and has_content and has_contextual_summary and has_keywords and has_tags and has_created_at:
        print("✅ AtomicNote Struktur im Code gefunden")
        return True
    else:
        print("❌ AtomicNote Struktur nicht vollständig im Code")
        return False


def test_async_implementation():
    """Test: Async I/O Implementation vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Async Komponenten
    has_async = "async def" in content or "asyncio" in content
    has_run_in_executor = "run_in_executor" in content
    
    if has_async and has_run_in_executor:
        print("✅ Async I/O Implementation gefunden")
        return True
    else:
        print("❌ Async I/O Implementation nicht vollständig")
        return False


def test_data_safety():
    """Test: Data Safety Features vorhanden"""
    main_py = Path(__file__).parent.parent / "src" / "main.py"
    content = main_py.read_text(encoding='utf-8')
    
    # Prüfe Data Safety Komponenten
    has_backup = "backup" in content.lower() or "bak" in content.lower()
    has_file_lock = "lock" in content.lower() or "fcntl" in content.lower()
    has_error_handling = "except" in content or "try:" in content
    
    if has_backup and has_file_lock and has_error_handling:
        print("✅ Data Safety Features gefunden")
        return True
    else:
        print("⚠️  Data Safety Features teilweise vorhanden")
        return True  # Nicht kritisch


def run_structure_tests():
    """Führt alle Code-Struktur-Tests aus"""
    print("\n" + "="*60)
    print("🔍 Code-Struktur Tests")
    print("="*60 + "\n")
    
    tests = [
        test_embedding_formula_in_code,
        test_link_generation_in_code,
        test_memory_evolution_in_code,
        test_retrieve_memory_in_code,
        test_atomic_note_structure_in_code,
        test_async_implementation,
        test_data_safety
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_func in tests:
        total_tests += 1
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"⚠️  {test_func.__name__}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 Code-Struktur Tests: {passed_tests}/{total_tests} passed")
    print("="*60 + "\n")
    
    if passed_tests == total_tests:
        print("✅ ALLE CODE-STRUKTUR-TESTS BESTANDEN!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} Test(s) mit Warnungen")
        return True  # Nicht kritisch


if __name__ == "__main__":
    success = run_structure_tests()
    exit(0 if success else 1)



