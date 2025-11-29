"""
Edge Case Tests für RustworkX-Integration

Testet:
- Große Datenmengen
- Spezielle Zeichen
- Sehr lange Strings
- Viele Edges
- Zyklische Referenzen
- Serialisierung/Deserialisierung
- GraphML-Persistenz
- Performance
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.storage.rustworkx_store import RustworkXGraphStore
from a_mem.models.note import AtomicNote, NoteRelation
from a_mem.storage.engine import create_graph_store


class EdgeCaseTester:
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
    
    def test_special_characters(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 1: Spezielle Zeichen in Content"""
        print("\n=== Test 1: Spezielle Zeichen ===")
        try:
            special_content = "Test mit: émojis 🚀, Umlaute äöü, Quotes \"'`, Newlines\n\n, Tabs\t, Unicode 中文, Emojis 😀🎉"
            note = AtomicNote(
                content=special_content,
                contextual_summary="Test mit speziellen Zeichen",
                keywords=["test", "special", "chars"],
                tags=["edge-case"]
            )
            graph_store.add_node(note)
            graph_store.save_snapshot()
            
            # Reload and check (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2._rx_graph = graph_store2._rx_graph.__class__()  # Reset
            graph_store2.load()
            retrieved = graph_store2.get_node(note.id)
            
            if retrieved and retrieved.get("content") == special_content:
                self.log_test("Special Characters", True, "Alle Zeichen korrekt gespeichert/geladen")
            else:
                self.log_test("Special Characters", False, f"Content mismatch: {retrieved.get('content')[:50] if retrieved else 'None'}")
        except Exception as e:
            self.log_test("Special Characters", False, f"Exception: {e}")
    
    def test_very_long_content(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 2: Sehr langer Content"""
        print("\n=== Test 2: Sehr langer Content ===")
        try:
            long_content = "A" * 100000  # 100KB Content
            note = AtomicNote(
                content=long_content,
                contextual_summary="Test mit sehr langem Content",
                keywords=["test", "long"],
                tags=["edge-case"]
            )
            start = time.time()
            graph_store.add_node(note)
            graph_store.save_snapshot()
            save_time = time.time() - start
            
            # Reload (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2._rx_graph = graph_store2._rx_graph.__class__()  # Reset
            graph_store2.load()
            retrieved = graph_store2.get_node(note.id)
            
            if retrieved and len(retrieved.get("content", "")) == 100000:
                self.log_test("Very Long Content", True, f"100KB Content gespeichert/geladen in {save_time:.2f}s")
            else:
                self.log_test("Very Long Content", False, f"Content length mismatch: {len(retrieved.get('content', '')) if retrieved else 0}")
        except Exception as e:
            self.log_test("Very Long Content", False, f"Exception: {e}")
    
    def test_many_edges(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 3: Viele Edges von einem Node"""
        print("\n=== Test 3: Viele Edges ===")
        try:
            # Create central node
            central = AtomicNote(
                content="Central node with many connections",
                contextual_summary="Hub node"
            )
            graph_store.add_node(central)
            
            # Create 100 connected nodes
            connected_nodes = []
            for i in range(100):
                node = AtomicNote(
                    content=f"Connected node {i}",
                    contextual_summary=f"Node {i}"
                )
                graph_store.add_node(node)
                connected_nodes.append(node)
                
                # Add edge
                relation = NoteRelation(
                    source_id=central.id,
                    target_id=node.id,
                    relation_type="relates_to",
                    reasoning=f"Connection {i}",
                    weight=0.5 + (i % 50) / 100.0
                )
                graph_store.add_edge(relation)
            
            graph_store.save_snapshot()
            
            # Reload and check (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2._rx_graph = graph_store2._rx_graph.__class__()  # Reset
            graph_store2.load()
            neighbors = graph_store2.get_neighbors(central.id)
            
            if len(neighbors) == 100:
                self.log_test("Many Edges", True, f"100 Edges korrekt gespeichert/geladen")
            else:
                self.log_test("Many Edges", False, f"Edge count mismatch: {len(neighbors)}")
        except Exception as e:
            self.log_test("Many Edges", False, f"Exception: {e}")
    
    def test_cyclic_references(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 4: Zyklische Referenzen"""
        print("\n=== Test 4: Zyklische Referenzen ===")
        try:
            # Create 3 nodes in cycle
            nodes = []
            for i in range(3):
                node = AtomicNote(
                    content=f"Cycle node {i}",
                    contextual_summary=f"Node {i}"
                )
                graph_store.add_node(node)
                nodes.append(node)
            
            # Create cycle: A->B->C->A
            for i in range(3):
                relation = NoteRelation(
                    source_id=nodes[i].id,
                    target_id=nodes[(i+1) % 3].id,
                    relation_type="relates_to",
                    reasoning=f"Cycle edge {i}",
                    weight=0.8
                )
                graph_store.add_edge(relation)
            
            graph_store.save_snapshot()
            
            # Reload and check
            graph_store2 = RustworkXGraphStore()
            graph_store2.load()
            
            # Check cycle exists
            n0_neighbors = graph_store2.get_neighbors(nodes[0].id)
            n1_neighbors = graph_store2.get_neighbors(nodes[1].id)
            n2_neighbors = graph_store2.get_neighbors(nodes[2].id)
            
            if len(n0_neighbors) == 1 and len(n1_neighbors) == 1 and len(n2_neighbors) == 1:
                self.log_test("Cyclic References", True, "Zyklische Referenzen korrekt gespeichert")
            else:
                self.log_test("Cyclic References", False, f"Cycle broken: {len(n0_neighbors)}, {len(n1_neighbors)}, {len(n2_neighbors)}")
        except Exception as e:
            self.log_test("Cyclic References", False, f"Exception: {e}")
    
    def test_metadata_complexity(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 5: Komplexe Metadata-Strukturen"""
        print("\n=== Test 5: Komplexe Metadata ===")
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
                content="Test mit komplexer Metadata",
                contextual_summary="Metadata test",
                metadata=complex_metadata
            )
            graph_store.add_node(note)
            graph_store.save_snapshot()
            
            # Reload and check (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2._rx_graph = graph_store2._rx_graph.__class__()  # Reset
            graph_store2.load()
            retrieved = graph_store2.get_node(note.id)
            
            if retrieved and retrieved.get("metadata") == complex_metadata:
                self.log_test("Complex Metadata", True, "Komplexe Metadata-Struktur korrekt serialisiert")
            else:
                self.log_test("Complex Metadata", False, f"Metadata mismatch")
        except Exception as e:
            self.log_test("Complex Metadata", False, f"Exception: {e}")
    
    def test_rapid_updates(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 6: Schnelle Updates"""
        print("\n=== Test 6: Schnelle Updates ===")
        try:
            note = AtomicNote(
                content="Initial content",
                contextual_summary="Initial summary"
            )
            graph_store.add_node(note)
            
            # Rapid updates
            for i in range(10):
                note.contextual_summary = f"Updated summary {i}"
                note.keywords = [f"keyword{i}", f"tag{i}"]
                graph_store.update_node(note)
            
            graph_store.save_snapshot()
            
            # Reload and check (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2.load()
            retrieved = graph_store2.get_node(note.id)
            
            if retrieved and retrieved.get("contextual_summary") == "Updated summary 9":
                self.log_test("Rapid Updates", True, "10 schnelle Updates korrekt verarbeitet")
            else:
                self.log_test("Rapid Updates", False, f"Final state mismatch: {retrieved.get('contextual_summary') if retrieved else 'None'}")
        except Exception as e:
            self.log_test("Rapid Updates", False, f"Exception: {e}")
    
    def test_edge_data_variations(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 7: Verschiedene Edge-Daten"""
        print("\n=== Test 7: Edge-Daten-Variationen ===")
        try:
            node1 = AtomicNote(content="Node 1")
            node2 = AtomicNote(content="Node 2")
            graph_store.add_node(node1)
            graph_store.add_node(node2)
            
            # Test verschiedene Edge-Konfigurationen
            edge_configs = [
                {"weight": 0.0, "reasoning": "Min weight"},
                {"weight": 1.0, "reasoning": "Max weight"},
                {"weight": 0.5, "reasoning": "Mid weight"},
                {"weight": 0.99, "reasoning": "High weight"},
            ]
            
            for i, config in enumerate(edge_configs):
                relation = NoteRelation(
                    source_id=node1.id,
                    target_id=node2.id,
                    relation_type="relates_to",
                    reasoning=config["reasoning"],
                    weight=config["weight"]
                )
                # Note: Same nodes, different edges (RustworkX allows only one edge per pair)
                # So we'll create different target nodes
                if i > 0:
                    node = AtomicNote(content=f"Target {i}")
                    graph_store.add_node(node)
                    relation.target_id = node.id
                
                graph_store.add_edge(relation)
            
            graph_store.save_snapshot()
            
            # Reload and check
            graph_store2 = RustworkXGraphStore()
            graph_store2.load()
            edges = graph_store2.get_all_edges()
            
            if len(edges) >= 4:
                self.log_test("Edge Data Variations", True, f"{len(edges)} Edges mit verschiedenen Daten gespeichert")
            else:
                self.log_test("Edge Data Variations", False, f"Edge count: {len(edges)}")
        except Exception as e:
            self.log_test("Edge Data Variations", False, f"Exception: {e}")
    
    def test_graphml_persistence(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 8: GraphML-Persistenz"""
        print("\n=== Test 8: GraphML-Persistenz ===")
        try:
            # Create test data
            note = AtomicNote(
                content="Persistence test",
                contextual_summary="Test summary",
                keywords=["test", "persistence"],
                tags=["edge-case"]
            )
            graph_store.add_node(note)
            graph_store.save_snapshot()
            
            # Check file exists
            graphml_path = graph_store.graph_path
            if not graphml_path.exists():
                self.log_test("GraphML Persistence", False, "GraphML file not created")
                return
            
            file_size = graphml_path.stat().st_size
            if file_size > 0:
                self.log_test("GraphML Persistence", True, f"GraphML file created ({file_size} bytes)")
            else:
                self.log_test("GraphML Persistence", False, "GraphML file is empty")
        except Exception as e:
            self.log_test("GraphML Persistence", False, f"Exception: {e}")
    
    def test_networkx_compatibility(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 9: NetworkX-Kompatibilität"""
        print("\n=== Test 9: NetworkX-Kompatibilität ===")
        try:
            # Create nodes
            nodes = []
            for i in range(5):
                node = AtomicNote(content=f"Node {i}")
                graph_store.add_node(node)
                nodes.append(node)
            
            # Create edges
            for i in range(4):
                relation = NoteRelation(
                    source_id=nodes[i].id,
                    target_id=nodes[i+1].id,
                    relation_type="relates_to"
                )
                graph_store.add_edge(relation)
            
            # Test NetworkX-compatible API
            graph = graph_store.graph
            
            # Test various NetworkX methods
            node_count = graph.number_of_nodes()
            edge_count = graph.number_of_edges()
            has_nodes = all(node.id in graph for node in nodes)
            has_edges = all(
                graph.has_edge(nodes[i].id, nodes[i+1].id) 
                for i in range(4)
            )
            
            # Test nodes/edges access
            nodes_data = list(graph.nodes(data=True))
            edges_data = list(graph.edges(data=True))
            
            if (node_count == 5 and edge_count == 4 and has_nodes and has_edges and 
                len(nodes_data) == 5 and len(edges_data) == 4):
                self.log_test("NetworkX Compatibility", True, "Alle NetworkX-API-Methoden funktionieren")
            else:
                self.log_test("NetworkX Compatibility", False, 
                    f"API mismatch: nodes={node_count}, edges={edge_count}, has_nodes={has_nodes}, has_edges={has_edges}")
        except Exception as e:
            self.log_test("NetworkX Compatibility", False, f"Exception: {e}")
    
    def test_performance_large_graph(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 10: Performance mit großem Graph"""
        print("\n=== Test 10: Performance (großer Graph) ===")
        try:
            # Create 100 nodes
            start = time.time()
            nodes = []
            for i in range(100):
                node = AtomicNote(
                    content=f"Performance test node {i}",
                    contextual_summary=f"Summary {i}",
                    keywords=[f"kw{i}", f"tag{i}"],
                    tags=[f"tag{i}"]
                )
                graph_store.add_node(node)
                nodes.append(node)
            add_time = time.time() - start
            
            # Create 50 edges
            start = time.time()
            for i in range(50):
                relation = NoteRelation(
                    source_id=nodes[i].id,
                    target_id=nodes[i+50].id,
                    relation_type="relates_to",
                    weight=0.5
                )
                graph_store.add_edge(relation)
            edge_time = time.time() - start
            
            # Save
            start = time.time()
            graph_store.save_snapshot()
            save_time = time.time() - start
            
            # Load
            graph_store2 = RustworkXGraphStore()
            start = time.time()
            graph_store2.load()
            load_time = time.time() - start
            
            # Query
            start = time.time()
            all_nodes = graph_store2.get_all_nodes()
            all_edges = graph_store2.get_all_edges()
            query_time = time.time() - start
            
            total_time = add_time + edge_time + save_time + load_time + query_time
            
            self.log_test("Performance Large Graph", True, 
                f"100 nodes, 50 edges: Add={add_time:.3f}s, Edges={edge_time:.3f}s, "
                f"Save={save_time:.3f}s, Load={load_time:.3f}s, Query={query_time:.3f}s, Total={total_time:.3f}s")
        except Exception as e:
            self.log_test("Performance Large Graph", False, f"Exception: {e}")
    
    def test_unicode_edge_cases(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 11: Unicode Edge Cases"""
        print("\n=== Test 11: Unicode Edge Cases ===")
        try:
            unicode_tests = [
                "Zero-width space: \u200B",
                "Right-to-left: \u202E",
                "Combining characters: e\u0301",
                "Emoji sequences: 👨‍👩‍👧‍👦",
                "Mathematical: ∑∫√",
                "CJK: 中文日本語한국어",
            ]
            
            nodes = []
            for i, content in enumerate(unicode_tests):
                node = AtomicNote(
                    content=content,
                    contextual_summary=f"Unicode test {i}",
                    keywords=[f"unicode{i}"],
                    tags=[f"test{i}"]
                )
                graph_store.add_node(node)
                nodes.append(node)
            
            graph_store.save_snapshot()
            
            # Reload and verify
            graph_store2 = RustworkXGraphStore()
            graph_store2.load()
            
            all_match = True
            for i, node in enumerate(nodes):
                retrieved = graph_store2.get_node(node.id)
                if not retrieved or retrieved.get("content") != unicode_tests[i]:
                    all_match = False
                    break
            
            if all_match:
                self.log_test("Unicode Edge Cases", True, f"{len(unicode_tests)} Unicode-Tests erfolgreich")
            else:
                self.log_test("Unicode Edge Cases", False, "Unicode-Content mismatch")
        except Exception as e:
            self.log_test("Unicode Edge Cases", False, f"Exception: {e}")
    
    def test_empty_fields(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 12: Leere Felder"""
        print("\n=== Test 12: Leere Felder ===")
        try:
            note = AtomicNote(
                content="Test with empty fields",
                contextual_summary="",  # Empty summary
                keywords=[],  # Empty keywords
                tags=[],  # Empty tags
                metadata={}  # Empty metadata
            )
            graph_store.add_node(note)
            graph_store.save_snapshot()
            
            # Reload (use same path)
            graph_store2 = RustworkXGraphStore()
            graph_store2.graph_path = test_graph_path
            graph_store2._rx_graph = graph_store2._rx_graph.__class__()  # Reset
            graph_store2.load()
            retrieved = graph_store2.get_node(note.id)
            
            if (retrieved and 
                retrieved.get("contextual_summary") == "" and
                retrieved.get("keywords") == [] and
                retrieved.get("tags") == [] and
                retrieved.get("metadata") == {}):
                self.log_test("Empty Fields", True, "Leere Felder korrekt gespeichert/geladen")
            else:
                self.log_test("Empty Fields", False, "Leere Felder nicht korrekt behandelt")
        except Exception as e:
            self.log_test("Empty Fields", False, f"Exception: {e}")
    
    def test_concurrent_operations(self, graph_store: RustworkXGraphStore, test_graph_path: Path):
        """Test 13: Sequenzielle Operationen (Simulation)"""
        print("\n=== Test 13: Sequenzielle Operationen ===")
        try:
            # Create nodes
            nodes = []
            for i in range(10):
                node = AtomicNote(content=f"Node {i}")
                graph_store.add_node(node)
                nodes.append(node)
            
            # Add edges
            for i in range(9):
                relation = NoteRelation(
                    source_id=nodes[i].id,
                    target_id=nodes[i+1].id,
                    relation_type="relates_to"
                )
                graph_store.add_edge(relation)
            
            # Update nodes
            for node in nodes:
                node.contextual_summary = "Updated"
                graph_store.update_node(node)
            
            # Remove some edges
            for i in range(5):
                graph_store.remove_edge(nodes[i].id, nodes[i+1].id)
            
            # Remove some nodes
            for i in range(3):
                graph_store.remove_node(nodes[i].id)
            
            graph_store.save_snapshot()
            
            # Reload and verify
            graph_store2 = RustworkXGraphStore()
            graph_store2.load()
            
            remaining_nodes = graph_store2.get_all_nodes()
            remaining_edges = graph_store2.get_all_edges()
            
            if len(remaining_nodes) == 7 and len(remaining_edges) == 4:
                self.log_test("Sequential Operations", True, "Sequenzielle Operationen erfolgreich")
            else:
                self.log_test("Sequential Operations", False, 
                    f"State mismatch: nodes={len(remaining_nodes)}, edges={len(remaining_edges)}")
        except Exception as e:
            self.log_test("Sequential Operations", False, f"Exception: {e}")
    
    def run_all_tests(self):
        """Führt alle Tests aus."""
        print("=" * 60)
        print("RustworkX Edge Case Tests")
        print("=" * 60)
        
        # Create temporary graph store for testing
        import tempfile
        import shutil
        
        # Use temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        test_graph_path = temp_dir / "test_graph.graphml"
        
        try:
            # Create graph store and override path
            graph_store = RustworkXGraphStore()
            graph_store.graph_path = test_graph_path
            # Ensure graph is empty
            graph_store._rx_graph = graph_store._rx_graph.__class__()
            
            # Run all tests (pass test_graph_path for reloads)
            self.test_special_characters(graph_store, test_graph_path)
            self.test_very_long_content(graph_store, test_graph_path)
            self.test_many_edges(graph_store, test_graph_path)
            self.test_cyclic_references(graph_store, test_graph_path)
            self.test_metadata_complexity(graph_store, test_graph_path)
            self.test_rapid_updates(graph_store, test_graph_path)
            self.test_edge_data_variations(graph_store, test_graph_path)
            self.test_graphml_persistence(graph_store, test_graph_path)
            self.test_networkx_compatibility(graph_store, test_graph_path)
            self.test_performance_large_graph(graph_store, test_graph_path)
            self.test_unicode_edge_cases(graph_store, test_graph_path)
            self.test_empty_fields(graph_store, test_graph_path)
            self.test_concurrent_operations(graph_store, test_graph_path)
            
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
        results_file = Path(__file__).parent.parent / "test_results_edge_cases.json"
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
    tester = EdgeCaseTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

