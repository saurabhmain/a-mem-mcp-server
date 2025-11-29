"""
FalkorDBLite GraphStore Adapter - Proof of Concept

This module provides a FalkorDBLite-based implementation of the GraphStore interface,
replacing NetworkX with a persistent graph database.

Features:
- Native disk persistence (no JSON load/save)
- High performance (GraphBLAS, sparse matrices)
- LLM-optimized for Knowledge Graphs
- Cypher query language support
"""

import json
import sys
from typing import List, Dict, Optional
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

try:
    from falkordblite import FalkorDB
    FALKORDB_AVAILABLE = True
except ImportError:
    FALKORDB_AVAILABLE = False
    FalkorDB = None

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


class FalkorDBGraphStore:
    """
    FalkorDBLite-based GraphStore implementation.
    
    Provides the same interface as NetworkX GraphStore but uses
    FalkorDBLite for persistent graph storage on disk.
    """
    
    def __init__(self):
        """Initialize FalkorDBLite database and graph."""
        if not FALKORDB_AVAILABLE:
            raise ImportError(
                "FalkorDBLite is not installed. Install with: pip install falkordblite"
            )
        
        # Database path: data/falkordb/
        self.db_path = settings.DATA_DIR / "falkordb"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize FalkorDB
        self.db = FalkorDB(path=str(self.db_path))
        self.graph = self.db.select_graph("KnowledgeGraph")
        
        _write_log(f"[FalkorDB] Initialized database at {self.db_path}")
    
    def load(self):
        """
        Loads the graph from disk.
        
        Note: FalkorDBLite automatically loads data on initialization.
        This method is kept for interface compatibility.
        """
        # FalkorDBLite loads automatically, but we can verify
        try:
            # Try to get graph stats
            result = self.graph.query("MATCH (n) RETURN count(n) as node_count")
            if result.result_set:
                node_count = result.result_set[0][0]
                _write_log(f"[FalkorDB] Loaded graph with {node_count} nodes")
        except Exception as e:
            _write_log(f"[FalkorDB] Load warning: {e}")
    
    def save_snapshot(self):
        """
        Saves the current state to disk.
        
        Note: FalkorDBLite automatically persists all changes.
        This method is kept for interface compatibility and logs the operation.
        """
        try:
            result = self.graph.query("MATCH (n) RETURN count(n) as node_count")
            edge_result = self.graph.query("MATCH ()-[r]->() RETURN count(r) as edge_count")
            
            node_count = result.result_set[0][0] if result.result_set else 0
            edge_count = edge_result.result_set[0][0] if edge_result.result_set else 0
            
            _write_log(f"[FalkorDB] [save_snapshot] Graph state: {node_count} nodes, {edge_count} edges")
            # FalkorDBLite persists automatically, no explicit save needed
        except Exception as e:
            _write_log(f"[FalkorDB] [save_snapshot] Error: {e}")
    
    def add_node(self, note: AtomicNote):
        """Adds a node to the graph."""
        props = self._note_to_properties(note)
        cypher_props = self._props_to_cypher(props)
        
        query = f"CREATE (n:Note {cypher_props})"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB] Added node: {note.id}")
        except Exception as e:
            _write_log(f"[FalkorDB] Error adding node {note.id}: {e}")
            raise
    
    def add_edge(self, relation: NoteRelation):
        """Adds an edge to the graph."""
        # Escape single quotes in strings
        reasoning = relation.reasoning.replace("'", "\\'") if relation.reasoning else ""
        
        query = f"""
        MATCH (a:Note {{id: '{relation.source_id}'}}),
              (b:Note {{id: '{relation.target_id}'}})
        CREATE (a)-[r:{relation.relation_type} {{
            reasoning: '{reasoning}',
            weight: {relation.weight},
            created_at: '{relation.created_at.isoformat()}'
        }}]->(b)
        RETURN r
        """
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB] Added edge: {relation.source_id} -> {relation.target_id} ({relation.relation_type})")
        except Exception as e:
            _write_log(f"[FalkorDB] Error adding edge: {e}")
            raise
    
    def update_node(self, note: AtomicNote):
        """Updates an existing node in the graph."""
        props = self._note_to_properties(note)
        set_clauses = []
        
        for key, value in props.items():
            if key == "id":
                continue  # Skip ID, used in MATCH
            if isinstance(value, str):
                # Escape single quotes
                escaped_value = value.replace("'", "\\'")
                set_clauses.append(f"n.{key} = '{escaped_value}'")
            elif isinstance(value, (int, float)):
                set_clauses.append(f"n.{key} = {value}")
            elif isinstance(value, bool):
                set_clauses.append(f"n.{key} = {str(value).lower()}")
            else:
                # JSON-encode complex types
                json_value = json.dumps(value).replace("'", "\\'")
                set_clauses.append(f"n.{key} = '{json_value}'")
        
        set_str = ", ".join(set_clauses)
        
        query = f"""
        MATCH (n:Note {{id: '{note.id}'}})
        SET {set_str}
        RETURN n
        """
        
        try:
            result = self.graph.query(query)
            if not result.result_set:
                # Node doesn't exist, create it
                self.add_node(note)
            else:
                _write_log(f"[FalkorDB] Updated node: {note.id}")
        except Exception as e:
            _write_log(f"[FalkorDB] Error updating node {note.id}: {e}")
            raise
    
    def get_neighbors(self, node_id: str) -> List[Dict]:
        """Gets all neighbors (successors and predecessors) of a node."""
        query = f"""
        MATCH (n:Note {{id: '{node_id}'}})-[r]->(m:Note)
        RETURN m
        UNION
        MATCH (n:Note {{id: '{node_id}'}})<-[r]-(m:Note)
        RETURN m
        """
        
        try:
            result = self.graph.query(query)
            neighbors = []
            for row in result.result_set:
                if row and len(row) > 0:
                    node_data = self._cypher_node_to_dict(row[0])
                    if node_data:
                        neighbors.append(node_data)
            return neighbors
        except Exception as e:
            _write_log(f"[FalkorDB] Error getting neighbors for {node_id}: {e}")
            return []
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Gets a single node by ID."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) RETURN n"
        
        try:
            result = self.graph.query(query)
            if result.result_set and len(result.result_set) > 0:
                return self._cypher_node_to_dict(result.result_set[0][0])
            return None
        except Exception as e:
            _write_log(f"[FalkorDB] Error getting node {node_id}: {e}")
            return None
    
    def has_node(self, node_id: str) -> bool:
        """Checks if a node exists."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) RETURN count(n) as count"
        
        try:
            result = self.graph.query(query)
            if result.result_set and len(result.result_set) > 0:
                return result.result_set[0][0] > 0
            return False
        except Exception as e:
            _write_log(f"[FalkorDB] Error checking node {node_id}: {e}")
            return False
    
    def get_all_nodes(self) -> List[Dict]:
        """Gets all nodes in the graph."""
        query = "MATCH (n:Note) RETURN n"
        
        try:
            result = self.graph.query(query)
            nodes = []
            for row in result.result_set:
                if row and len(row) > 0:
                    node_data = self._cypher_node_to_dict(row[0])
                    if node_data:
                        nodes.append(node_data)
            return nodes
        except Exception as e:
            _write_log(f"[FalkorDB] Error getting all nodes: {e}")
            return []
    
    def get_all_edges(self) -> List[Dict]:
        """Gets all edges in the graph."""
        query = "MATCH (a:Note)-[r]->(b:Note) RETURN a.id as source, b.id as target, r"
        
        try:
            result = self.graph.query(query)
            edges = []
            for row in result.result_set:
                if len(row) >= 3:
                    edge_data = {
                        "source": row[0],
                        "target": row[1],
                        "type": getattr(row[2], "type", None),
                        "reasoning": getattr(row[2], "reasoning", None),
                        "weight": getattr(row[2], "weight", 1.0),
                        "created_at": getattr(row[2], "created_at", None)
                    }
                    edges.append(edge_data)
            return edges
        except Exception as e:
            _write_log(f"[FalkorDB] Error getting all edges: {e}")
            return []
    
    def remove_node(self, node_id: str):
        """Removes a node and all associated edges."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) DETACH DELETE n"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB] Removed node: {node_id}")
        except Exception as e:
            _write_log(f"[FalkorDB] Error removing node {node_id}: {e}")
            raise
    
    def reset(self):
        """Resets the graph completely."""
        query = "MATCH (n) DETACH DELETE n"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB] Reset graph")
        except Exception as e:
            _write_log(f"[FalkorDB] Error resetting graph: {e}")
            raise
    
    # Helper methods for property conversion
    
    def _note_to_properties(self, note: AtomicNote) -> Dict:
        """Converts AtomicNote to Cypher properties."""
        return {
            "id": note.id,
            "content": note.content,
            "contextual_summary": note.contextual_summary or "",
            "keywords": note.keywords,
            "tags": note.tags,
            "created_at": note.created_at.isoformat(),
            "type": note.type or "",
            "metadata": note.metadata
        }
    
    def _props_to_cypher(self, props: Dict) -> str:
        """Converts Python dict to Cypher property string."""
        cypher_props = []
        
        for key, value in props.items():
            if isinstance(value, str):
                # Escape single quotes
                escaped_value = value.replace("'", "\\'")
                cypher_props.append(f"{key}: '{escaped_value}'")
            elif isinstance(value, (int, float)):
                cypher_props.append(f"{key}: {value}")
            elif isinstance(value, bool):
                cypher_props.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, list):
                # Convert list to JSON string
                json_value = json.dumps(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{json_value}'")
            elif isinstance(value, dict):
                # Convert dict to JSON string
                json_value = json.dumps(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{json_value}'")
            elif value is None:
                cypher_props.append(f"{key}: null")
            else:
                # Fallback: convert to string
                str_value = str(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{str_value}'")
        
        return "{" + ", ".join(cypher_props) + "}"
    
    def _cypher_node_to_dict(self, cypher_node) -> Optional[Dict]:
        """Converts Cypher node result to Python dict."""
        if not cypher_node:
            return None
        
        try:
            # Extract properties from Cypher node
            node_dict = {}
            
            # Try to get properties (depends on FalkorDBLite API)
            if hasattr(cypher_node, 'properties'):
                node_dict = dict(cypher_node.properties)
            elif hasattr(cypher_node, '__dict__'):
                node_dict = dict(cypher_node.__dict__)
            elif isinstance(cypher_node, dict):
                node_dict = cypher_node
            else:
                # Fallback: try to access as attributes
                for attr in ['id', 'content', 'contextual_summary', 'keywords', 
                           'tags', 'created_at', 'type', 'metadata']:
                    if hasattr(cypher_node, attr):
                        node_dict[attr] = getattr(cypher_node, attr)
            
            # Parse JSON strings back to Python types
            if 'keywords' in node_dict and isinstance(node_dict['keywords'], str):
                try:
                    node_dict['keywords'] = json.loads(node_dict['keywords'])
                except:
                    pass
            
            if 'tags' in node_dict and isinstance(node_dict['tags'], str):
                try:
                    node_dict['tags'] = json.loads(node_dict['tags'])
                except:
                    pass
            
            if 'metadata' in node_dict and isinstance(node_dict['metadata'], str):
                try:
                    node_dict['metadata'] = json.loads(node_dict['metadata'])
                except:
                    pass
            
            # Parse datetime
            if 'created_at' in node_dict and isinstance(node_dict['created_at'], str):
                try:
                    node_dict['created_at'] = datetime.fromisoformat(node_dict['created_at'])
                except:
                    pass
            
            return node_dict
        except Exception as e:
            _write_log(f"[FalkorDB] Error converting Cypher node: {e}")
            return None

