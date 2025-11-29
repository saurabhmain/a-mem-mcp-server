"""
RustworkX GraphStore Adapter - GraphML Persistence

This module provides a RustworkX-based implementation of the GraphStore interface,
replacing NetworkX with a high-performance Rust-based graph library.

Features:
- 3x-100x faster than NetworkX
- GraphML persistence (native RustworkX support)
- Windows-compatible
- Same interface as NetworkX GraphStore
"""

import json
import sys
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

try:
    import rustworkx as rx
    RUSTWORKX_AVAILABLE = True
except ImportError:
    RUSTWORKX_AVAILABLE = False
    rx = None

from ..config import settings
from ..models.note import AtomicNote, NoteRelation

# Log file path (reuse from engine.py)
LOG_FILE = settings.DATA_DIR / "graph_save.log"

def _write_log(message: str):
    """Writes a log message to file and stderr."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[WARNING] Failed to write log: {e}", file=sys.stderr)
    
    print(message, file=sys.stderr)


class RustworkXGraphStore:
    """
    RustworkX-based GraphStore implementation with GraphML persistence.
    
    Provides the same interface as NetworkX GraphStore but uses
    RustworkX for high-performance graph operations (3x-100x faster).
    """
    
    def __init__(self):
        """Initialize RustworkX graph and load from GraphML if exists."""
        if not RUSTWORKX_AVAILABLE:
            raise ImportError(
                "RustworkX is not installed. Install with: pip install rustworkx"
            )
        
        # GraphML file path: data/graph.graphml
        self.graph_path = settings.GRAPH_PATH.with_suffix(".graphml")
        
        # Initialize graph (internal RustworkX graph)
        self._rx_graph = rx.PyDiGraph()  # Directed Graph
        
        # Load from disk if exists
        self.load()
        
        _write_log(f"[RustworkX] Initialized graph (GraphML: {self.graph_path})")
    
    def load(self):
        """
        Loads the graph from GraphML file.
        
        Note: GraphML is a standard format for graph persistence.
        """
        if self.graph_path.exists():
            try:
                graphs = rx.read_graphml(str(self.graph_path))
                if graphs and len(graphs) > 0:
                    self._rx_graph = graphs[0]
                    # Deserialize all node data immediately after loading
                    # This ensures node IDs are accessible for _find_node_index
                    for idx in self._rx_graph.node_indices():
                        node_data = self._rx_graph[idx]
                        if isinstance(node_data, dict):
                            # Deserialize JSON strings back to lists/dicts
                            deserialized = self._deserialize_node_data(node_data.copy())
                            # Update node data in place
                            self._rx_graph[idx] = deserialized
                    
                    node_count = len(self._rx_graph.node_indices())
                    edge_count = len(self._rx_graph.edge_list())
                    _write_log(f"[RustworkX] Loaded graph: {node_count} nodes, {edge_count} edges")
                else:
                    _write_log("[RustworkX] GraphML file exists but is empty")
            except Exception as e:
                _write_log(f"[RustworkX] Error loading graph: {e}")
                import traceback
                _write_log(f"[RustworkX] Traceback: {traceback.format_exc()}")
                # Create new empty graph on error
                self._rx_graph = rx.PyDiGraph()
        else:
            _write_log("[RustworkX] No existing graph found, starting fresh")
            self._rx_graph = rx.PyDiGraph()
    
    def save_snapshot(self):
        """
        Saves the current graph state to GraphML file.
        
        Note: GraphML is a standard XML-based format for graphs.
        """
        try:
            node_count = len(self._rx_graph.node_indices())
            edge_count = len(self._rx_graph.edge_list())
            
            _write_log(f"[RustworkX] [save_snapshot] Saving graph: {node_count} nodes, {edge_count} edges")
            
            # Ensure parent directory exists
            self.graph_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to GraphML (atomic write: temp file, then rename)
            # Ensure all nodes have proper data types before saving (convert lists to JSON strings)
            # Create a temporary graph with sanitized data
            temp_graph = rx.PyDiGraph()
            node_map = {}  # old_idx -> new_idx
            
            # Add all nodes with sanitized data
            for old_idx in self._rx_graph.node_indices():
                node_data = self._rx_graph[old_idx]
                if isinstance(node_data, dict):
                    # Create a copy and sanitize
                    sanitized_data = dict(node_data)
                    # Convert lists/dicts to JSON strings for GraphML
                    if isinstance(sanitized_data.get('keywords'), list):
                        sanitized_data['keywords'] = json.dumps(sanitized_data['keywords'])
                    if isinstance(sanitized_data.get('tags'), list):
                        sanitized_data['tags'] = json.dumps(sanitized_data['tags'])
                    if isinstance(sanitized_data.get('metadata'), dict):
                        sanitized_data['metadata'] = json.dumps(sanitized_data['metadata'])
                    if sanitized_data.get('type') is None:
                        sanitized_data['type'] = ""
                    elif not isinstance(sanitized_data.get('type'), str):
                        sanitized_data['type'] = str(sanitized_data['type'])
                    # Ensure created_at is a string (not datetime object)
                    # Handle 'None' string and None values
                    if 'created_at' in sanitized_data:
                        created_at_val = sanitized_data['created_at']
                        if isinstance(created_at_val, str):
                            # Handle 'None' string case
                            if created_at_val.lower() == 'none' or created_at_val == '':
                                sanitized_data['created_at'] = datetime.utcnow().isoformat()
                            # Otherwise keep as is (should be ISO string already)
                        elif isinstance(created_at_val, datetime):
                            sanitized_data['created_at'] = created_at_val.isoformat()
                        elif created_at_val is None:
                            sanitized_data['created_at'] = datetime.utcnow().isoformat()
                        else:
                            sanitized_data['created_at'] = str(created_at_val)
                    new_idx = temp_graph.add_node(sanitized_data)
                    node_map[old_idx] = new_idx
                else:
                    new_idx = temp_graph.add_node(node_data)
                    node_map[old_idx] = new_idx
            
            # Add all edges with sanitized edge data
            for edge in self._rx_graph.edge_list():
                old_src_idx, old_tgt_idx = edge
                new_src_idx = node_map.get(old_src_idx)
                new_tgt_idx = node_map.get(old_tgt_idx)
                if new_src_idx is not None and new_tgt_idx is not None:
                    edge_data = self._rx_graph.get_edge_data(old_src_idx, old_tgt_idx)
                    if edge_data is None:
                        edge_data = {}
                    # Sanitize edge data (ensure all values are strings/primitives)
                    sanitized_edge = {}
                    for key, value in edge_data.items():
                        if isinstance(value, str):
                            sanitized_edge[key] = value
                        elif isinstance(value, (int, float, bool)):
                            sanitized_edge[key] = value
                        elif value is None:
                            sanitized_edge[key] = ""
                        else:
                            sanitized_edge[key] = str(value)
                    temp_graph.add_edge(new_src_idx, new_tgt_idx, sanitized_edge)
            
            temp_path = self.graph_path.with_suffix(".graphml.tmp")
            rx.write_graphml(temp_graph, str(temp_path))
            
            # Atomic replace
            import os
            os.replace(temp_path, self.graph_path)
            
            _write_log(f"[RustworkX] [save_snapshot] Graph saved to {self.graph_path}")
            
            # Verify
            if self.graph_path.exists():
                file_size = self.graph_path.stat().st_size
                _write_log(f"[RustworkX] [save_snapshot] File size: {file_size} bytes")
        except Exception as e:
            _write_log(f"[RustworkX] [save_snapshot] Error saving graph: {e}")
            raise
    
    def add_node(self, note: AtomicNote):
        """Adds a node to the graph."""
        try:
            # Convert AtomicNote to dict for storage
            node_data = note.model_dump(mode='json')
            # Convert datetime to ISO string for JSON serialization
            # Handle None case (shouldn't happen, but be defensive)
            if note.created_at is not None:
                node_data['created_at'] = note.created_at.isoformat()
            else:
                node_data['created_at'] = datetime.utcnow().isoformat()
            
            # GraphML doesn't support lists/dicts directly - convert to JSON strings
            if isinstance(node_data.get('keywords'), list):
                node_data['keywords'] = json.dumps(node_data['keywords'])
            if isinstance(node_data.get('tags'), list):
                node_data['tags'] = json.dumps(node_data['tags'])
            if isinstance(node_data.get('metadata'), dict):
                node_data['metadata'] = json.dumps(node_data['metadata'])
            # GraphML has issues with 'type' field - convert None to empty string
            if node_data.get('type') is None:
                node_data['type'] = ""
            elif not isinstance(node_data.get('type'), str):
                node_data['type'] = str(node_data['type'])
            
            # Add node to graph
            self._rx_graph.add_node(node_data)
            
            _write_log(f"[RustworkX] Added node: {note.id}")
        except Exception as e:
            _write_log(f"[RustworkX] Error adding node {note.id}: {e}")
            raise
    
    def add_edge(self, relation: NoteRelation):
        """Adds an edge to the graph."""
        try:
            # Find node indices by ID
            source_idx = self._find_node_index(relation.source_id)
            target_idx = self._find_node_index(relation.target_id)
            
            if source_idx is None:
                raise ValueError(f"Source node not found: {relation.source_id}")
            if target_idx is None:
                raise ValueError(f"Target node not found: {relation.target_id}")
            
            # Edge properties
            edge_data = {
                "type": relation.relation_type,
                "reasoning": relation.reasoning or "",
                "weight": relation.weight,
                "created_at": relation.created_at.isoformat()
            }
            
            # Add edge
            self._rx_graph.add_edge(source_idx, target_idx, edge_data)
            
            _write_log(f"[RustworkX] Added edge: {relation.source_id} -> {relation.target_id} ({relation.relation_type})")
        except Exception as e:
            _write_log(f"[RustworkX] Error adding edge: {e}")
            raise
    
    def update_node(self, note: AtomicNote):
        """Updates an existing node in the graph."""
        try:
            node_idx = self._find_node_index(note.id)
            
            if node_idx is None:
                # Node doesn't exist, add it
                self.add_node(note)
                return
            
            # Collect all edges connected to this node before removal
            connected_edges = []
            
            # Incoming edges
            for edge in self._rx_graph.in_edges(node_idx):
                source_idx = edge[0]
                source_data = self._rx_graph[source_idx]
                source_id = source_data.get("id") if isinstance(source_data, dict) else None
                edge_data = self._rx_graph.get_edge_data(source_idx, node_idx)
                if source_id:
                    connected_edges.append(("in", source_id, edge_data))
            
            # Outgoing edges
            for edge in self._rx_graph.out_edges(node_idx):
                target_idx = edge[1]
                target_data = self._rx_graph[target_idx]
                target_id = target_data.get("id") if isinstance(target_data, dict) else None
                edge_data = self._rx_graph.get_edge_data(node_idx, target_idx)
                if target_id:
                    connected_edges.append(("out", target_id, edge_data))
            
            # Remove old node
            self._rx_graph.remove_node(node_idx)
            
            # Add updated node
            node_data = note.model_dump(mode='json')
            # Handle None case (shouldn't happen, but be defensive)
            if note.created_at is not None:
                node_data['created_at'] = note.created_at.isoformat()
            else:
                node_data['created_at'] = datetime.utcnow().isoformat()
            
            # GraphML doesn't support lists/dicts directly - convert to JSON strings
            if isinstance(node_data.get('keywords'), list):
                node_data['keywords'] = json.dumps(node_data['keywords'])
            if isinstance(node_data.get('tags'), list):
                node_data['tags'] = json.dumps(node_data['tags'])
            if isinstance(node_data.get('metadata'), dict):
                node_data['metadata'] = json.dumps(node_data['metadata'])
            # GraphML has issues with 'type' field - convert None to empty string
            if node_data.get('type') is None:
                node_data['type'] = ""
            elif not isinstance(node_data.get('type'), str):
                node_data['type'] = str(node_data['type'])
            
            new_idx = self._rx_graph.add_node(node_data)
            
            # Restore all edges
            for direction, other_node_id, edge_data in connected_edges:
                other_idx = self._find_node_index(other_node_id)
                if other_idx is not None:
                    edge_props = edge_data if isinstance(edge_data, dict) else {}
                    if direction == "in":
                        self._rx_graph.add_edge(other_idx, new_idx, edge_props)
                    else:
                        self._rx_graph.add_edge(new_idx, other_idx, edge_props)
            
            _write_log(f"[RustworkX] Updated node: {note.id}")
        except Exception as e:
            _write_log(f"[RustworkX] Error updating node {note.id}: {e}")
            raise
    
    def get_neighbors(self, node_id: str) -> List[Dict]:
        """Returns all neighbors of a node (both incoming and outgoing edges)."""
        try:
            node_idx = self._find_node_index(node_id)
            if node_idx is None:
                return []
            
            neighbors = []
            
            # Outgoing edges (successors)
            for edge in self._rx_graph.out_edges(node_idx):
                target_idx = edge[1]
                target_data = self._rx_graph[target_idx]
                if isinstance(target_data, dict):
                    # Convert JSON strings back to lists/dicts
                    target_data = self._deserialize_node_data(target_data)
                    neighbors.append(target_data)
            
            # Incoming edges (predecessors)
            for edge in self._rx_graph.in_edges(node_idx):
                source_idx = edge[0]
                source_data = self._rx_graph[source_idx]
                if isinstance(source_data, dict):
                    # Convert JSON strings back to lists/dicts
                    source_data = self._deserialize_node_data(source_data)
                    # Avoid duplicates (compare by id)
                    if not any(n.get('id') == source_data.get('id') for n in neighbors):
                        neighbors.append(source_data)
            
            return neighbors
        except Exception as e:
            _write_log(f"[RustworkX] Error getting neighbors for {node_id}: {e}")
            return []
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Returns a node by ID."""
        try:
            node_idx = self._find_node_index(node_id)
            if node_idx is None:
                return None
            
            node_data = self._rx_graph[node_idx]
            if isinstance(node_data, dict):
                # Convert ISO string back to datetime if needed
                # Handle 'None' string and None values
                if 'created_at' in node_data:
                    created_at_val = node_data['created_at']
                    if isinstance(created_at_val, str):
                        # Handle 'None' string case
                        if created_at_val.lower() == 'none' or created_at_val == '':
                            # Use current time as fallback
                            node_data['created_at'] = datetime.utcnow().isoformat()
                        else:
                            try:
                                node_data['created_at'] = datetime.fromisoformat(created_at_val)
                            except:
                                # Fallback to current time if parsing fails
                                node_data['created_at'] = datetime.utcnow().isoformat()
                    elif created_at_val is None:
                        # Handle None value
                        node_data['created_at'] = datetime.utcnow().isoformat()
                    # If it's already a datetime object, keep it
                # Convert JSON strings back to lists/dicts
                if 'keywords' in node_data and isinstance(node_data['keywords'], str):
                    try:
                        node_data['keywords'] = json.loads(node_data['keywords'])
                    except:
                        pass
                if 'tags' in node_data and isinstance(node_data['tags'], str):
                    try:
                        node_data['tags'] = json.loads(node_data['tags'])
                    except:
                        pass
                if 'metadata' in node_data and isinstance(node_data['metadata'], str):
                    try:
                        node_data['metadata'] = json.loads(node_data['metadata'])
                    except:
                        pass
                return node_data
            return None
        except Exception as e:
            _write_log(f"[RustworkX] Error getting node {node_id}: {e}")
            return None
    
    def has_node(self, node_id: str) -> bool:
        """Checks if a node exists."""
        return self._find_node_index(node_id) is not None
    
    def get_all_nodes(self) -> List[Dict]:
        """Returns all nodes in the graph."""
        try:
            nodes = []
            for idx in self._rx_graph.node_indices():
                node_data = self._rx_graph[idx]
                if isinstance(node_data, dict):
                    # Use _deserialize_node_data for consistent handling
                    node_data = self._deserialize_node_data(node_data.copy())
                    # Convert JSON strings back to lists/dicts
                    if 'keywords' in node_data and isinstance(node_data['keywords'], str):
                        try:
                            node_data['keywords'] = json.loads(node_data['keywords'])
                        except:
                            pass
                    if 'tags' in node_data and isinstance(node_data['tags'], str):
                        try:
                            node_data['tags'] = json.loads(node_data['tags'])
                        except:
                            pass
                    if 'metadata' in node_data and isinstance(node_data['metadata'], str):
                        try:
                            node_data['metadata'] = json.loads(node_data['metadata'])
                        except:
                            pass
                    nodes.append(node_data)
            return nodes
        except Exception as e:
            _write_log(f"[RustworkX] Error getting all nodes: {e}")
            return []
    
    def get_all_edges(self) -> List[Dict]:
        """Returns all edges in the graph."""
        try:
            edges = []
            for edge in self._rx_graph.edge_list():
                source_idx, target_idx = edge
                source_data = self._rx_graph[source_idx]
                target_data = self._rx_graph[target_idx]
                
                source_id = source_data.get("id") if isinstance(source_data, dict) else None
                target_id = target_data.get("id") if isinstance(target_data, dict) else None
                
                edge_data = self._rx_graph.get_edge_data(source_idx, target_idx)
                
                if source_id and target_id:
                    edge_dict = {
                        "source": source_id,
                        "target": target_id,
                        "type": edge_data.get("type") if isinstance(edge_data, dict) else None,
                        "reasoning": edge_data.get("reasoning") if isinstance(edge_data, dict) else None,
                        "weight": edge_data.get("weight", 1.0) if isinstance(edge_data, dict) else 1.0,
                        "created_at": edge_data.get("created_at") if isinstance(edge_data, dict) else None
                    }
                    edges.append(edge_dict)
            
            return edges
        except Exception as e:
            _write_log(f"[RustworkX] Error getting all edges: {e}")
            return []
    
    def remove_node(self, node_id: str):
        """Removes a node and all associated edges."""
        try:
            node_idx = self._find_node_index(node_id)
            if node_idx is not None:
                self._rx_graph.remove_node(node_idx)
                _write_log(f"[RustworkX] Removed node: {node_id}")
            else:
                _write_log(f"[RustworkX] Node not found for removal: {node_id}")
        except Exception as e:
            _write_log(f"[RustworkX] Error removing node {node_id}: {e}")
            raise
    
    def reset(self):
        """Resets the graph completely."""
        try:
            # Delete GraphML file if exists
            if self.graph_path.exists():
                self.graph_path.unlink()
            
            # Create new empty graph
            self._rx_graph = rx.PyDiGraph()
            
            _write_log("[RustworkX] Reset graph")
        except Exception as e:
            _write_log(f"[RustworkX] Error resetting graph: {e}")
            raise
    
    def _find_node_index(self, node_id: str) -> Optional[int]:
        """
        Finds the node index by ID.
        
        RustworkX uses integer indices, but we store node IDs in the node data.
        This helper function finds the index for a given node ID.
        """
        for idx in self._rx_graph.node_indices():
            node_data = self._rx_graph[idx]
            if isinstance(node_data, dict) and node_data.get("id") == node_id:
                return idx
        return None
    
    # Compatibility methods for direct graph access (used by enzymes.py, logic.py, etc.)
    
    def number_of_nodes(self) -> int:
        """Returns the number of nodes in the graph."""
        return len(self._rx_graph.node_indices())
    
    def number_of_edges(self) -> int:
        """Returns the number of edges in the graph."""
        return len(self._rx_graph.edge_list())
    
    def degree(self, node_id: str) -> int:
        """Returns the degree (number of edges) of a node."""
        node_idx = self._find_node_index(node_id)
        if node_idx is None:
            return 0
        # Count incoming + outgoing edges
        in_degree = len(list(self._rx_graph.in_edges(node_idx)))
        out_degree = len(list(self._rx_graph.out_edges(node_idx)))
        return in_degree + out_degree
    
    def successors(self, node_id: str):
        """Returns successors (outgoing neighbors) of a node."""
        node_idx = self._find_node_index(node_id)
        if node_idx is None:
            return []
        # Return list of node IDs (not indices)
        successors = []
        for edge in self._rx_graph.out_edges(node_idx):
            target_idx = edge[1]
            target_data = self._rx_graph[target_idx]
            if isinstance(target_data, dict):
                successors.append(target_data.get("id"))
        return successors
    
    def predecessors(self, node_id: str):
        """Returns predecessors (incoming neighbors) of a node."""
        node_idx = self._find_node_index(node_id)
        if node_idx is None:
            return []
        # Return list of node IDs (not indices)
        predecessors = []
        for edge in self._rx_graph.in_edges(node_idx):
            source_idx = edge[0]
            source_data = self._rx_graph[source_idx]
            if isinstance(source_data, dict):
                predecessors.append(source_data.get("id"))
        return predecessors
    
    def has_edge(self, source_id: str, target_id: str) -> bool:
        """Checks if an edge exists between two nodes."""
        source_idx = self._find_node_index(source_id)
        target_idx = self._find_node_index(target_id)
        if source_idx is None or target_idx is None:
            return False
        # Check if edge exists
        try:
            edge_data = self._rx_graph.get_edge_data(source_idx, target_idx)
            return edge_data is not None
        except:
            return False
    
    def get_edge_data(self, source_id: str, target_id: str) -> Optional[Dict]:
        """Returns edge data between two nodes."""
        source_idx = self._find_node_index(source_id)
        target_idx = self._find_node_index(target_id)
        if source_idx is None or target_idx is None:
            return None
        try:
            edge_data = self._rx_graph.get_edge_data(source_idx, target_idx)
            if isinstance(edge_data, dict):
                return edge_data
            return None
        except:
            return None
    
    def remove_edge(self, source_id: str, target_id: str):
        """Removes an edge between two nodes."""
        source_idx = self._find_node_index(source_id)
        target_idx = self._find_node_index(target_id)
        if source_idx is None or target_idx is None:
            return
        
        try:
            # RustworkX doesn't have direct remove_edge, so we need to rebuild the graph
            # Get all nodes and edges
            all_nodes = []
            for idx in self._rx_graph.node_indices():
                all_nodes.append((idx, self._rx_graph[idx]))
            
            all_edges = []
            for edge in self._rx_graph.edge_list():
                src_idx, tgt_idx = edge
                # Skip the edge we want to remove
                if src_idx == source_idx and tgt_idx == target_idx:
                    continue
                edge_data = self._rx_graph.get_edge_data(src_idx, tgt_idx)
                all_edges.append((src_idx, tgt_idx, edge_data))
            
            # Rebuild graph
            self._rx_graph = rx.PyDiGraph()
            
            # Add all nodes back (with new indices)
            node_map = {}  # old_idx -> new_idx
            for old_idx, node_data in all_nodes:
                new_idx = self._rx_graph.add_node(node_data)
                node_map[old_idx] = new_idx
            
            # Add all edges back (except the removed one)
            for old_src_idx, old_tgt_idx, edge_data in all_edges:
                new_src_idx = node_map[old_src_idx]
                new_tgt_idx = node_map[old_tgt_idx]
                self._rx_graph.add_edge(new_src_idx, new_tgt_idx, edge_data or {})
            
            _write_log(f"[RustworkX] Removed edge: {source_id} -> {target_id}")
        except Exception as e:
            _write_log(f"[RustworkX] Error removing edge: {e}")
            raise
    
    # Compatibility layer: Create a wrapper that mimics NetworkX's graph.graph.nodes/edges API
    class _GraphWrapper:
        """Wrapper to mimic NetworkX graph.graph API for compatibility."""
        def __init__(self, rustworkx_store):
            self._store = rustworkx_store
        
        def __contains__(self, node_id: str):
            """Support 'node_id in graph' syntax."""
            return self._store.has_node(node_id)
        
        def __iter__(self):
            """Support iteration over node IDs."""
            for node in self._store.get_all_nodes():
                yield node.get("id")
        
        @property
        def nodes(self):
            """Mimics graph.graph.nodes access."""
            return self._GraphNodesWrapper(self._store)
        
        @property
        def edges(self):
            """Mimics graph.graph.edges access."""
            return self._GraphEdgesWrapper(self._store)
        
        def number_of_nodes(self):
            return self._store.number_of_nodes()
        
        def number_of_edges(self):
            return self._store.number_of_edges()
        
        def degree(self, node_id: str):
            return self._store.degree(node_id)
        
        def successors(self, node_id: str):
            return self._store.successors(node_id)
        
        def predecessors(self, node_id: str):
            return self._store.predecessors(node_id)
        
        def has_edge(self, source_id: str, target_id: str):
            return self._store.has_edge(source_id, target_id)
        
        def get_edge_data(self, source_id: str, target_id: str):
            return self._store.get_edge_data(source_id, target_id)
        
        def remove_edge(self, source_id: str, target_id: str):
            return self._store.remove_edge(source_id, target_id)
        
        def add_edge(self, source_id: str, target_id: str, **edge_data):
            """
            Adds an edge between two nodes.
            Mimics NetworkX's graph.graph.add_edge(source, target, **kwargs) API.
            
            Args:
                source_id: Source node ID
                target_id: Target node ID
                **edge_data: Edge attributes (relation_type, weight, created_at, reasoning, etc.)
            """
            from ..models.note import NoteRelation
            from datetime import datetime
            
            # Extract edge attributes with defaults
            relation_type = edge_data.get("type") or edge_data.get("relation_type", "relates_to")
            weight = edge_data.get("weight", 1.0)
            reasoning = edge_data.get("reasoning", "")
            created_at_str = edge_data.get("created_at")
            
            # Parse created_at if provided as string, otherwise use current time
            if created_at_str:
                if isinstance(created_at_str, str):
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                    except:
                        created_at = datetime.utcnow()
                else:
                    created_at = created_at_str
            else:
                created_at = datetime.utcnow()
            
            # Create NoteRelation object
            relation = NoteRelation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                weight=weight,
                reasoning=reasoning,
                created_at=created_at
            )
            
            # Add edge via store
            self._store.add_edge(relation)
        
        def remove_node(self, node_id: str):
            """Removes a node from the graph."""
            return self._store.remove_node(node_id)
        
        def __getitem__(self, source_id: str):
            """
            Support graph.graph[source] syntax for NetworkX compatibility.
            Returns a wrapper that supports graph.graph[source][target] = edge_data.
            """
            return self._GraphSourceWrapper(self._store, source_id)
        
        class _GraphSourceWrapper:
            """Wrapper for graph.graph[source] access pattern."""
            def __init__(self, store, source_id):
                self._store = store
                self._source_id = source_id
            
            def __getitem__(self, target_id: str):
                """Support graph.graph[source][target] access."""
                edge_data = self._store.get_edge_data(self._source_id, target_id)
                if edge_data is None:
                    raise KeyError(f"Edge {self._source_id} -> {target_id} not found")
                return self._MutableEdgeDict(self._store, self._source_id, target_id, edge_data)
            
            class _MutableEdgeDict(dict):
                """Mutable dict wrapper for edge data that supports __setitem__ with auto-sync."""
                def __init__(self, store, source_id, target_id, edge_data):
                    super().__init__(edge_data)
                    self._store = store
                    self._source_id = source_id
                    self._target_id = target_id
                
                def __setitem__(self, key, value):
                    """Update edge data and sync back to graph."""
                    super().__setitem__(key, value)
                    # Update edge by removing and re-adding with new data
                    try:
                        from ..models.note import NoteRelation
                        from datetime import datetime
                        
                        # Parse created_at if it's a string
                        created_at_str = self.get("created_at")
                        if created_at_str:
                            if isinstance(created_at_str, str):
                                try:
                                    created_at = datetime.fromisoformat(created_at_str)
                                except:
                                    created_at = datetime.utcnow()
                            else:
                                created_at = created_at_str
                        else:
                            created_at = datetime.utcnow()
                        
                        relation = NoteRelation(
                            source_id=self._source_id,
                            target_id=self._target_id,
                            relation_type=self.get("type") or self.get("relation_type", "relates_to"),
                            weight=self.get("weight", 1.0),
                            reasoning=self.get("reasoning", ""),
                            created_at=created_at
                        )
                        
                        # Remove old edge and add new one with updated data
                        self._store.remove_edge(self._source_id, self._target_id)
                        self._store.add_edge(relation)
                    except Exception as e:
                        _write_log(f"[RustworkX] Error syncing edge data: {e}")
        
        class _GraphNodesWrapper:
            """Wrapper for graph.graph.nodes access."""
            def __init__(self, rustworkx_store):
                self._store = rustworkx_store
            
            def __contains__(self, node_id: str):
                return self._store.has_node(node_id)
            
            def __getitem__(self, node_id: str):
                node_data = self._store.get_node(node_id)
                if node_data is None:
                    raise KeyError(node_id)
                # Return a mutable dict-like object that supports .update()
                return self._MutableNodeDict(self._store, node_id, node_data)
            
            def get(self, node_id: str, default=None):
                node_data = self._store.get_node(node_id)
                if node_data is None:
                    return default
                return self._MutableNodeDict(self._store, node_id, node_data)
            
            def __iter__(self):
                """Iterate over node IDs."""
                for node in self._store.get_all_nodes():
                    yield node.get("id")
            
            def __call__(self, data=False):
                """Mimics graph.graph.nodes(data=True) iterator."""
                if data:
                    for node in self._store.get_all_nodes():
                        yield (node.get("id"), node)
                else:
                    for node in self._store.get_all_nodes():
                        yield node.get("id")
            
            class _MutableNodeDict(dict):
                """Mutable dict wrapper that supports .update() and __setitem__ with auto-sync."""
                def __init__(self, store, node_id, node_data):
                    super().__init__(node_data)
                    self._store = store
                    self._node_id = node_id
                    self._sync_enabled = True
                
                def __setitem__(self, key, value):
                    """Override __setitem__ to auto-sync changes back to graph."""
                    super().__setitem__(key, value)
                    if self._sync_enabled:
                        self._sync_to_graph()
                
                def __delitem__(self, key):
                    """Override __delitem__ to auto-sync changes back to graph."""
                    super().__delitem__(key)
                    if self._sync_enabled:
                        self._sync_to_graph()
                
                def update(self, *args, **kwargs):
                    """Update node data and sync back to graph."""
                    super().update(*args, **kwargs)
                    if self._sync_enabled:
                        self._sync_to_graph()
                
                def _sync_to_graph(self):
                    """Sync current dict state back to graph."""
                    try:
                        from ..models.note import AtomicNote
                        # Temporarily disable sync to avoid recursion during update
                        self._sync_enabled = False
                        note = AtomicNote(**self)
                        self._store.update_node(note)
                        self._sync_enabled = True
                    except Exception as e:
                        self._sync_enabled = True
                        _write_log(f"[RustworkX] Error syncing node to graph: {e}")
        
        class _GraphEdgesWrapper:
            """Wrapper for graph.graph.edges access."""
            def __init__(self, rustworkx_store):
                self._store = rustworkx_store
            
            def __call__(self, data=False):
                """Mimics graph.graph.edges(data=True) iterator."""
                edges = self._store.get_all_edges()
                if data:
                    for edge in edges:
                        # Return (source, target, edge_data_dict)
                        edge_data = {
                            "type": edge.get("type"),
                            "reasoning": edge.get("reasoning"),
                            "weight": edge.get("weight", 1.0),
                            "created_at": edge.get("created_at")
                        }
                        yield (edge.get("source"), edge.get("target"), edge_data)
                else:
                    for edge in edges:
                        yield (edge.get("source"), edge.get("target"))
    
    @property
    def graph(self):
        """Returns a wrapper that mimics NetworkX's graph.graph API."""
        if not hasattr(self, '_graph_wrapper'):
            self._graph_wrapper = self._GraphWrapper(self)
        return self._graph_wrapper
    
    def _deserialize_node_data(self, node_data: Dict) -> Dict:
        """Converts JSON strings back to lists/dicts for node data."""
        if isinstance(node_data, dict):
            # Convert JSON strings back to lists/dicts
            if 'keywords' in node_data and isinstance(node_data['keywords'], str):
                try:
                    node_data['keywords'] = json.loads(node_data['keywords'])
                except:
                    pass
            if 'tags' in node_data and isinstance(node_data['tags'], str):
                try:
                    node_data['tags'] = json.loads(node_data['tags'])
                except:
                    pass
            if 'metadata' in node_data and isinstance(node_data['metadata'], str):
                try:
                    node_data['metadata'] = json.loads(node_data['metadata'])
                except:
                    pass
            # Convert ISO string back to datetime if needed
            # Handle 'None' string and None values
            if 'created_at' in node_data:
                created_at_val = node_data['created_at']
                if isinstance(created_at_val, str):
                    # Handle 'None' string case
                    if created_at_val.lower() == 'none' or created_at_val == '':
                        # Use current time as fallback
                        node_data['created_at'] = datetime.utcnow().isoformat()
                    else:
                        try:
                            node_data['created_at'] = datetime.fromisoformat(created_at_val)
                        except:
                            # Fallback to current time if parsing fails
                            node_data['created_at'] = datetime.utcnow().isoformat()
                elif created_at_val is None:
                    # Handle None value
                    node_data['created_at'] = datetime.utcnow().isoformat()
                # If it's already a datetime object, keep it
        return node_data

