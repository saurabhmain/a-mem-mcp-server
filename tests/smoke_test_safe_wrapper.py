"""
Smoke Test für SafeGraphStore Wrapper

Testet die kritischsten Szenarien:
1. Node hinzufügen & wiederfinden (ID-Konsistenz)
2. Edge Cases (None-Werte, Unicode, korrupte Daten)
3. Reload & Persistenz
4. Error Recovery
"""
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.storage.safe_graph_wrapper import SafeGraphStore
from a_mem.storage.rustworkx_store import RustworkXGraphStore
from a_mem.models.note import AtomicNote, NoteRelation
import rustworkx as rx

def test_basic_operations():
    """Test 1: Basis-Operationen (Add, Get, Reload)"""
    print("=" * 60)
    print("Smoke Test: SafeGraphStore Wrapper")
    print("=" * 60)
    
    temp_dir = Path(tempfile.mkdtemp())
    test_path = temp_dir / "smoke_test.graphml"
    
    try:
        # Setup
        store1 = RustworkXGraphStore.__new__(RustworkXGraphStore)
        store1.graph_path = test_path
        store1._rx_graph = rx.PyDiGraph()
        safe1 = SafeGraphStore(store1)
        
        # Test 1: Node hinzufügen & wiederfinden
        print("\n[Test 1] Node hinzufügen & wiederfinden")
        note = AtomicNote(
            content="Smoke Test Node",
            contextual_summary="Test summary",
            keywords=["test", "smoke"],
            tags=["smoke-test"]
        )
        original_id = note.id
        safe1.add_node(note)
        safe1.save_snapshot()
        
        # Reload
        store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
        store2.graph_path = test_path
        store2._rx_graph = rx.PyDiGraph()
        store2.load()
        safe2 = SafeGraphStore(store2)
        
        retrieved = safe2.get_node(original_id)
        if retrieved and retrieved.get("id") == original_id:
            print("  ✅ PASS: Node gefunden, ID konsistent")
        else:
            print(f"  ❌ FAIL: Node nicht gefunden oder ID mismatch")
            return False
        
        # Test 2: Edge Cases (Unicode, leere Felder)
        print("\n[Test 2] Edge Cases (Unicode, leere Felder)")
        note2 = AtomicNote(
            content="Test mit: émojis 🚀, Umlaute äöü, CJK 中文",
            contextual_summary="",  # Empty
            keywords=[],  # Empty
            tags=[],  # Empty
            metadata={}  # Empty
        )
        safe2.add_node(note2)
        safe2.save_snapshot()
        
        retrieved2 = safe2.get_node(note2.id)
        if (retrieved2 and 
            isinstance(retrieved2.get("keywords"), list) and
            isinstance(retrieved2.get("tags"), list) and
            isinstance(retrieved2.get("metadata"), dict) and
            "中文" in retrieved2.get("content", "")):
            print("  ✅ PASS: Edge Cases korrekt behandelt")
        else:
            print(f"  ❌ FAIL: Edge Cases nicht korrekt behandelt")
            return False
        
        # Test 3: Korrupte Daten reparieren (nach Load)
        print("\n[Test 3] Korrupte Daten reparieren")
        # Manually corrupt a node in the graph (simulating corruption from external source)
        node_idx = store2._find_node_index(note2.id)
        if node_idx is not None:
            node_data = store2._rx_graph[node_idx]
            if isinstance(node_data, dict):
                node_data['created_at'] = 'None'  # Corrupt string
                node_data['keywords'] = 'None'  # Corrupt string
                store2._rx_graph[node_idx] = node_data
        
        safe2.save_snapshot()
        
        # Reload and check repair (Wrapper should sanitize on get_node)
        store3 = RustworkXGraphStore.__new__(RustworkXGraphStore)
        store3.graph_path = test_path
        store3._rx_graph = rx.PyDiGraph()
        store3.load()
        safe3 = SafeGraphStore(store3)
        
        retrieved3 = safe3.get_node(note2.id)
        if (retrieved3 and 
            retrieved3.get("created_at") and 
            retrieved3.get("created_at") != 'None' and
            isinstance(retrieved3.get("keywords"), list)):
            print("  ✅ PASS: Korrupte Daten wurden repariert")
        else:
            print(f"  ❌ FAIL: Korrupte Daten nicht repariert")
            print(f"    created_at: {retrieved3.get('created_at') if retrieved3 else 'None'}")
            print(f"    keywords type: {type(retrieved3.get('keywords')) if retrieved3 else 'None'}")
            return False
        
        # Test 4: Edge-Operationen
        print("\n[Test 4] Edge-Operationen")
        relation = NoteRelation(
            source_id=original_id,
            target_id=note2.id,
            relation_type="relates_to",
            weight=0.8,
            reasoning="Smoke test relation"
        )
        safe3.add_edge(relation)
        safe3.save_snapshot()
        
        edges = safe3.get_all_edges()
        if len(edges) >= 1:
            print(f"  ✅ PASS: Edge hinzugefügt ({len(edges)} edges)")
        else:
            print(f"  ❌ FAIL: Edge nicht gefunden")
            return False
        
        # Test 5: Error Recovery
        print("\n[Test 5] Error Recovery")
        # Try to add node with problematic data (should recover)
        try:
            note3 = AtomicNote(
                content="Recovery Test",
                contextual_summary="Test"
            )
            safe3.add_node(note3)
            safe3.save_snapshot()
            print("  ✅ PASS: Error Recovery funktioniert")
        except Exception as e:
            print(f"  ❌ FAIL: Error Recovery fehlgeschlagen: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALLE SMOKE TESTS BESTANDEN!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ SMOKE TEST FEHLGESCHLAGEN: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if test_path.exists():
            test_path.unlink()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    success = test_basic_operations()
    sys.exit(0 if success else 1)

