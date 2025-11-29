"""Debug script to test SafeGraphStore reload issue"""
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a_mem.storage.safe_graph_wrapper import SafeGraphStore
from a_mem.storage.rustworkx_store import RustworkXGraphStore
from a_mem.models.note import AtomicNote
import rustworkx as rx

# Create temporary graph
temp_dir = Path(tempfile.mkdtemp())
test_path = temp_dir / "test.graphml"

print("=== Creating and saving node ===")
store1 = RustworkXGraphStore.__new__(RustworkXGraphStore)
store1.graph_path = test_path
store1._rx_graph = rx.PyDiGraph()
safe1 = SafeGraphStore(store1)

note = AtomicNote(content="Test", contextual_summary="Test summary")
print(f"Original note ID: {note.id}")
# Check what _sanitize_note does
sanitized = safe1._sanitize_note(note)
print(f"Sanitized note ID: {sanitized.id}")
print(f"IDs match: {note.id == sanitized.id}")
safe1.add_node(note)
safe1.save_snapshot()

print(f"Node ID: {note.id}")
print(f"Saved to: {test_path}")
print(f"File exists: {test_path.exists()}")

print("\n=== Reloading graph ===")
store2 = RustworkXGraphStore.__new__(RustworkXGraphStore)
store2.graph_path = test_path
store2._rx_graph = rx.PyDiGraph()
store2.load()

print(f"Loaded nodes: {len(store2._rx_graph.node_indices())}")

# Check what's in the graph
for idx in store2._rx_graph.node_indices():
    node_data = store2._rx_graph[idx]
    print(f"\nNode {idx}:")
    print(f"  Type: {type(node_data)}")
    if isinstance(node_data, dict):
        print(f"  Keys: {list(node_data.keys())}")
        print(f"  ID: {node_data.get('id')}")
        print(f"  Content: {node_data.get('content', 'N/A')[:50]}")
    else:
        print(f"  Data: {node_data}")

print("\n=== Testing _find_node_index ===")
node_idx = store2._find_node_index(note.id)
print(f"_find_node_index result: {node_idx}")

print("\n=== Testing get_node ===")
safe2 = SafeGraphStore(store2)
retrieved = safe2.get_node(note.id)
print(f"Retrieved node: {retrieved is not None}")
if retrieved:
    print(f"  ID: {retrieved.get('id')}")
    print(f"  Content: {retrieved.get('content', 'N/A')[:50]}")
else:
    print("  Node not found!")
    # Try direct access
    if node_idx is not None:
        direct_node = store2._rx_graph[node_idx]
        print(f"  Direct access works: {direct_node.get('id') if isinstance(direct_node, dict) else 'N/A'}")

# Cleanup
shutil.rmtree(temp_dir)

