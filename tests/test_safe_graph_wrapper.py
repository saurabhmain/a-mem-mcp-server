"""
Umfassende Tests für SafeGraphStore Wrapper

Testet:
- Edge Case Handling (leere Felder, Unicode, None-Werte)
- Sanitization & Validation
- Deserialisierung nach Load
- Recovery-Mechanismen
- Integration mit RustworkX
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.storage.safe_graph_wrapper import SafeGraphStore
from a_mem.storage.rustworkx_store import RustworkXGraphStore
from a_mem.models.note import AtomicNote, NoteRelation


class SafeGraphWrapperTester:
    def __init__(self):
        self.test_results = []
        self.errors = []
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Loggt ein Test-Ergebnis."""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if message:
            print(f"  → {message}")
        if not passed:
            self.errors.append(result)
    
    def test_empty_fields_sanitization(self, safe_store: SafeGraphStore):
        """Test 1: Leere Felder werden korrekt sanitized"""
        print("\n=== Test 1: Leere Felder Sanitization ===")
        try:
            note = AtomicNote(
                content="Test with empty fields",
                contextual_summary="",  # Empty
                keywords=[],  # Empty
                tags=[],  # Empty
                metadata={}  # Empty
            )
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("contextual_summary") == "" and
                retrieved.get("keywords") == [] and
                retrieved.get("tags") == [] and
                retrieved.get("metadata") == {}):
                self.log_test("Empty Fields Sanitization", True, "Leere Felder korrekt behandelt")
            else:
                self.log_test("Empty Fields Sanitization", False, 
                    f"Mismatch: summary={retrieved.get('contextual_summary') if retrieved else None}, "
                    f"keywords={retrieved.get('keywords') if retrieved else None}")
        except Exception as e:
            self.log_test("Empty Fields Sanitization", False, f"Exception: {e}")
    
    def test_none_values_sanitization(self, safe_store: SafeGraphStore):
        """Test 2: None-Werte werden korrekt sanitized"""
        print("\n=== Test 2: None-Werte Sanitization ===")
        try:
            # Create note with None values (simulating corrupted data)
            note = AtomicNote(
                content="Test with None values",
                contextual_summary="Valid summary"
            )
            # Manually set None values (simulating corruption)
            note.keywords = None
            note.tags = None
            note.metadata = None
            
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                isinstance(retrieved.get("keywords"), list) and
                isinstance(retrieved.get("tags"), list) and
                isinstance(retrieved.get("metadata"), dict)):
                self.log_test("None Values Sanitization", True, "None-Werte korrekt zu []/{} konvertiert")
            else:
                self.log_test("None Values Sanitization", False, 
                    f"Mismatch: keywords={type(retrieved.get('keywords')) if retrieved else None}")
        except Exception as e:
            self.log_test("None Values Sanitization", False, f"Exception: {e}")
    
    def test_unicode_handling(self, safe_store: SafeGraphStore):
        """Test 3: Unicode wird korrekt behandelt"""
        print("\n=== Test 3: Unicode Handling ===")
        try:
            unicode_content = "Test mit: émojis 🚀, Umlaute äöü, CJK 中文日本語한국어, Emojis 😀🎉"
            note = AtomicNote(
                content=unicode_content,
                contextual_summary="Unicode test",
                keywords=["unicode", "test", "中文"],
                tags=["test", "🚀"]
            )
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("content") == unicode_content and
                "中文" in retrieved.get("keywords", [])):
                self.log_test("Unicode Handling", True, "Unicode korrekt gespeichert/geladen")
            else:
                self.log_test("Unicode Handling", False, 
                    f"Content mismatch: {retrieved.get('content')[:50] if retrieved else None}")
        except Exception as e:
            self.log_test("Unicode Handling", False, f"Exception: {e}")
    
    def test_corrupted_created_at_repair(self, safe_store: SafeGraphStore):
        """Test 4: Korrupte created_at wird repariert"""
        print("\n=== Test 4: Corrupted created_at Repair ===")
        try:
            note = AtomicNote(
                content="Test with corrupted created_at",
                contextual_summary="Test"
            )
            safe_store.add_node(note)
            
            # Manually corrupt the created_at (simulating corruption)
            # Access via internal store
            node_idx = safe_store._store._find_node_index(note.id)
            if node_idx is not None:
                node_data = safe_store._store._rx_graph[node_idx]
                if isinstance(node_data, dict):
                    node_data['created_at'] = 'None'  # Corrupt
                    safe_store._store._rx_graph[node_idx] = node_data
            
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("created_at") and
                retrieved.get("created_at") != 'None' and
                retrieved.get("created_at") != ''):
                self.log_test("Corrupted created_at Repair", True, "Korrupte created_at wurde repariert")
            else:
                self.log_test("Corrupted created_at Repair", False, 
                    f"created_at nicht repariert: {retrieved.get('created_at') if retrieved else None}")
        except Exception as e:
            self.log_test("Corrupted created_at Repair", False, f"Exception: {e}")
    
    def test_json_string_deserialization(self, safe_store: SafeGraphStore):
        """Test 5: JSON-Strings werden korrekt deserialisiert"""
        print("\n=== Test 5: JSON String Deserialization ===")
        try:
            note = AtomicNote(
                content="Test JSON deserialization",
                contextual_summary="Test",
                keywords=["test", "json"],
                tags=["test"],
                metadata={"key": "value", "nested": {"level": 1}}
            )
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Manually serialize to JSON strings (simulating GraphML storage)
            node_idx = safe_store._store._find_node_index(note.id)
            if node_idx is not None:
                node_data = safe_store._store._rx_graph[node_idx]
                if isinstance(node_data, dict):
                    node_data['keywords'] = json.dumps(node_data.get('keywords', []))
                    node_data['tags'] = json.dumps(node_data.get('tags', []))
                    node_data['metadata'] = json.dumps(node_data.get('metadata', {}))
                    safe_store._store._rx_graph[node_idx] = node_data
            
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                isinstance(retrieved.get("keywords"), list) and
                isinstance(retrieved.get("tags"), list) and
                isinstance(retrieved.get("metadata"), dict) and
                retrieved.get("metadata", {}).get("key") == "value"):
                self.log_test("JSON String Deserialization", True, "JSON-Strings korrekt zu Lists/Dicts deserialisiert")
            else:
                self.log_test("JSON String Deserialization", False, 
                    f"Deserialization failed: keywords={type(retrieved.get('keywords')) if retrieved else None}")
        except Exception as e:
            self.log_test("JSON String Deserialization", False, f"Exception: {e}")
    
    def test_edge_sanitization(self, safe_store: SafeGraphStore):
        """Test 6: Edge-Sanitization"""
        print("\n=== Test 6: Edge Sanitization ===")
        try:
            node1 = AtomicNote(content="Node 1")
            node2 = AtomicNote(content="Node 2")
            safe_store.add_node(node1)
            safe_store.add_node(node2)
            
            # Create edge with None values
            relation = NoteRelation(
                source_id=node1.id,
                target_id=node2.id,
                relation_type="relates_to",
                weight=0.5,
                reasoning=""
            )
            safe_store.add_edge(relation)
            safe_store.save_snapshot()
            
            # Reload
            safe_store2 = SafeGraphStore(RustworkXGraphStore())
            safe_store2.graph_path = safe_store.graph_path
            safe_store2._store._rx_graph = safe_store2._store._rx_graph.__class__()
            safe_store2.load()
            
            edge_data = safe_store2.get_edge_data(node1.id, node2.id)
            
            if (edge_data and 
                edge_data.get("weight") == 0.5 and
                edge_data.get("reasoning") == ""):
                self.log_test("Edge Sanitization", True, "Edge korrekt sanitized")
            else:
                self.log_test("Edge Sanitization", False, 
                    f"Edge data mismatch: {edge_data}")
        except Exception as e:
            self.log_test("Edge Sanitization", False, f"Exception: {e}")
    
    def test_recovery_mechanism(self, safe_store: SafeGraphStore):
        """Test 7: Recovery-Mechanismus bei Fehlern"""
        print("\n=== Test 7: Recovery Mechanism ===")
        try:
            # Try to add node with invalid data (should trigger recovery)
            # Create note with very long content (should still work)
            long_content = "A" * 50000  # 50KB
            note = AtomicNote(
                content=long_content,
                contextual_summary="Long content test"
            )
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if retrieved and len(retrieved.get("content", "")) == 50000:
                self.log_test("Recovery Mechanism", True, "Recovery funktioniert bei großen Daten")
            else:
                self.log_test("Recovery Mechanism", False, 
                    f"Content length: {len(retrieved.get('content', '')) if retrieved else 0}")
        except Exception as e:
            self.log_test("Recovery Mechanism", False, f"Exception: {e}")
    
    def test_rapid_updates(self, safe_store: SafeGraphStore):
        """Test 8: Schnelle Updates mit Sanitization"""
        print("\n=== Test 8: Rapid Updates ===")
        try:
            note = AtomicNote(
                content="Initial content",
                contextual_summary="Initial summary"
            )
            safe_store.add_node(note)
            
            # Rapid updates
            for i in range(10):
                note.contextual_summary = f"Updated summary {i}"
                note.keywords = [f"kw{i}", f"tag{i}"]
                safe_store.update_node(note)
            
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("contextual_summary") == "Updated summary 9" and
                len(retrieved.get("keywords", [])) == 2):
                self.log_test("Rapid Updates", True, "10 schnelle Updates korrekt verarbeitet")
            else:
                self.log_test("Rapid Updates", False, 
                    f"Final state: summary={retrieved.get('contextual_summary') if retrieved else None}")
        except Exception as e:
            self.log_test("Rapid Updates", False, f"Exception: {e}")
    
    def test_complex_metadata(self, safe_store: SafeGraphStore):
        """Test 9: Komplexe Metadata-Strukturen"""
        print("\n=== Test 9: Complex Metadata ===")
        try:
            complex_metadata = {
                "nested": {
                    "level1": {
                        "level2": ["list", "with", "items"],
                        "number": 42,
                        "boolean": True
                    }
                },
                "array": [1, 2, 3, {"nested": "object"}],
                "unicode": "中文 🚀 émojis"
            }
            
            note = AtomicNote(
                content="Test complex metadata",
                contextual_summary="Test",
                metadata=complex_metadata
            )
            safe_store.add_node(note)
            safe_store.save_snapshot()
            
            # Reload (use same path) - Create store and manually set path before load
            rustworkx_store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
            # Set path before initializing graph
            rustworkx_store2.graph_path = safe_store.graph_path
            # Initialize graph manually (skip __init__'s auto-load)
            import rustworkx as rx
            rustworkx_store2._rx_graph = rx.PyDiGraph()
            # Now load from the correct path
            rustworkx_store2.load()
            safe_store2 = SafeGraphStore(rustworkx_store2)
            
            retrieved = safe_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("metadata") == complex_metadata):
                self.log_test("Complex Metadata", True, "Komplexe Metadata korrekt gespeichert/geladen")
            else:
                self.log_test("Complex Metadata", False, "Metadata mismatch")
        except Exception as e:
            self.log_test("Complex Metadata", False, f"Exception: {e}")
    
    def test_graph_property_access(self, safe_store: SafeGraphStore):
        """Test 10: graph.graph Property Access (für Enzyme)"""
        print("\n=== Test 10: graph.graph Property Access ===")
        try:
            note = AtomicNote(content="Test node")
            safe_store.add_node(note)
            
            # Test graph.graph access (used by enzymes)
            graph = safe_store.graph
            nodes = list(graph.nodes())
            edges = list(graph.edges())
            
            if (note.id in nodes and
                len(nodes) >= 1):
                self.log_test("graph.graph Property Access", True, 
                    f"Graph property funktioniert: {len(nodes)} nodes, {len(edges)} edges")
            else:
                self.log_test("graph.graph Property Access", False, 
                    f"Graph property nicht zugänglich: nodes={len(nodes)}")
        except Exception as e:
            self.log_test("graph.graph Property Access", False, f"Exception: {e}")
    
    def test_all_nodes_deserialized_after_load(self, safe_store: SafeGraphStore):
        """Test 11: Alle Nodes werden nach Load deserialisiert"""
        print("\n=== Test 11: All Nodes Deserialized After Load ===")
        try:
            # Create multiple nodes with JSON strings
            nodes = []
            for i in range(5):
                note = AtomicNote(
                    content=f"Node {i}",
                    keywords=[f"kw{i}"],
                    tags=[f"tag{i}"]
                )
                safe_store.add_node(note)
                nodes.append(note)
            
            safe_store.save_snapshot()
            
            # Manually serialize to JSON (simulating GraphML)
            for node in nodes:
                node_idx = safe_store._store._find_node_index(node.id)
                if node_idx is not None:
                    node_data = safe_store._store._rx_graph[node_idx]
                    if isinstance(node_data, dict):
                        node_data['keywords'] = json.dumps(node_data.get('keywords', []))
                        node_data['tags'] = json.dumps(node_data.get('tags', []))
                        safe_store._store._rx_graph[node_idx] = node_data
            
            safe_store.save_snapshot()
            
            # Reload
            safe_store2 = SafeGraphStore(RustworkXGraphStore())
            safe_store2.graph_path = safe_store.graph_path
            safe_store2._store._rx_graph = safe_store2._store._rx_graph.__class__()
            safe_store2.load()
            
            # Check all nodes are deserialized
            all_deserialized = True
            for node in nodes:
                retrieved = safe_store2.get_node(node.id)
                if not retrieved:
                    all_deserialized = False
                    break
                if not isinstance(retrieved.get("keywords"), list):
                    all_deserialized = False
                    break
                if not isinstance(retrieved.get("tags"), list):
                    all_deserialized = False
                    break
            
            if all_deserialized:
                self.log_test("All Nodes Deserialized After Load", True, 
                    f"Alle {len(nodes)} Nodes korrekt deserialisiert")
            else:
                self.log_test("All Nodes Deserialized After Load", False, 
                    "Nicht alle Nodes wurden deserialisiert")
        except Exception as e:
            self.log_test("All Nodes Deserialized After Load", False, f"Exception: {e}")
    
    def test_edge_weight_validation(self, safe_store: SafeGraphStore):
        """Test 12: Edge Weight Validation"""
        print("\n=== Test 12: Edge Weight Validation ===")
        try:
            node1 = AtomicNote(content="Node 1")
            node2 = AtomicNote(content="Node 2")
            safe_store.add_node(node1)
            safe_store.add_node(node2)
            
            # Test invalid weights (should be clamped to 0.0-1.0)
            invalid_weights = [-0.5, 1.5, 2.0, -1.0]
            for weight in invalid_weights:
                relation = NoteRelation(
                    source_id=node1.id,
                    target_id=node2.id,
                    relation_type="relates_to",
                    weight=weight,
                    reasoning=f"Test weight {weight}"
                )
                # Should sanitize weight to valid range
                safe_store.add_edge(relation)
            
            safe_store.save_snapshot()
            
            # Reload and check
            safe_store2 = SafeGraphStore(RustworkXGraphStore())
            safe_store2.graph_path = safe_store.graph_path
            safe_store2._store._rx_graph = safe_store2._store._rx_graph.__class__()
            safe_store2.load()
            
            edges = safe_store2.get_all_edges()
            
            # Check all weights are in valid range
            all_valid = True
            for edge in edges:
                weight = edge.get("weight", 1.0)
                if weight < 0.0 or weight > 1.0:
                    all_valid = False
                    break
            
            if all_valid:
                self.log_test("Edge Weight Validation", True, 
                    f"Alle {len(edges)} Edge-Weights im gültigen Bereich (0.0-1.0)")
            else:
                self.log_test("Edge Weight Validation", False, 
                    "Einige Edge-Weights außerhalb des gültigen Bereichs")
        except Exception as e:
            self.log_test("Edge Weight Validation", False, f"Exception: {e}")
    
    def run_all_tests(self):
        """Führt alle Tests aus."""
        print("=" * 60)
        print("SafeGraphStore Wrapper - Umfassende Tests")
        print("=" * 60)
        
        # Create temporary graph store for testing
        temp_dir = Path(tempfile.mkdtemp())
        test_graph_path = temp_dir / "test_safe_graph.graphml"
        
        try:
            # Create safe graph store
            rustworkx_store = RustworkXGraphStore()
            rustworkx_store.graph_path = test_graph_path
            rustworkx_store._rx_graph = rustworkx_store._rx_graph.__class__()
            
            safe_store = SafeGraphStore(rustworkx_store)
            
            # Run all tests
            self.test_empty_fields_sanitization(safe_store)
            self.test_none_values_sanitization(safe_store)
            self.test_unicode_handling(safe_store)
            self.test_corrupted_created_at_repair(safe_store)
            self.test_json_string_deserialization(safe_store)
            self.test_edge_sanitization(safe_store)
            self.test_recovery_mechanism(safe_store)
            self.test_rapid_updates(safe_store)
            self.test_complex_metadata(safe_store)
            self.test_graph_property_access(safe_store)
            self.test_all_nodes_deserialized_after_load(safe_store)
            self.test_edge_weight_validation(safe_store)
            
        finally:
            # Cleanup
            if test_graph_path.exists():
                test_graph_path.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if self.errors:
            print("\nFailed Tests:")
            for error in self.errors:
                print(f"  ❌ {error['test']}: {error['message']}")
        
        # Save results
        results_file = Path(__file__).parent.parent / "test_results_safe_wrapper.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": passed/total*100
                },
                "tests": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {results_file}")
        
        return passed == total


if __name__ == "__main__":
    tester = SafeGraphWrapperTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

