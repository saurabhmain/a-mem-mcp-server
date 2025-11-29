"""
FalkorDB Windows Adapter - Alternative für Windows-Systeme

Dieser Adapter nutzt falkordb-py direkt mit einem externen Redis-Server
(Memurai, Docker Redis, oder normaler Redis) statt redislite.

Warum?
- redislite unterstützt Windows nicht (braucht gcc/make)
- falkordb-py funktioniert mit jedem Redis-Server, der das FalkorDB-Modul hat

Voraussetzungen:
1. Redis-Server mit FalkorDB-Modul installiert:
   - Memurai (Windows-native): https://www.memurai.com/
   - Docker Redis + FalkorDB: docker run -p 6379:6379 falkordb/falkordb
   - Oder normaler Redis mit FalkorDB-Modul

2. Python-Pakete:
   pip install falkordb redis

Verwendung:
- Automatisch aktiviert, wenn GRAPH_BACKEND=falkordb und sys.platform == 'win32'
- Oder manuell: from a_mem.storage.falkordb_store_windows import FalkorDBGraphStoreWindows
"""

import json
import sys
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

try:
    from falkordb import FalkorDB
    FALKORDB_AVAILABLE = True
except ImportError:
    FALKORDB_AVAILABLE = False
    FalkorDB = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config import settings
from ..models.note import AtomicNote, NoteRelation

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


class FalkorDBGraphStoreWindows:
    """
    Windows-kompatible FalkorDB GraphStore-Implementierung.
    
    Nutzt falkordb-py direkt mit einem externen Redis-Server.
    """
    
    def __init__(self, redis_host: str = None, redis_port: int = None, redis_password: str = None):
        """
        Initialisiert den FalkorDB-Adapter für Windows.
        
        Args:
            redis_host: Redis-Server Host (default: localhost)
            redis_port: Redis-Server Port (default: 6379)
            redis_password: Redis-Passwort (optional)
        """
        if not FALKORDB_AVAILABLE:
            raise ImportError(
                "falkordb-py is not installed. Install with: pip install falkordb"
            )
        
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis-py is not installed. Install with: pip install redis"
            )
        
        # Redis-Verbindungsparameter aus Environment oder Defaults
        self.redis_host = redis_host or os.getenv("REDIS_HOST", "localhost")
        self.redis_port = redis_port or int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = redis_password or os.getenv("REDIS_PASSWORD", None)
        
        # FalkorDB-Instanz erstellen
        try:
            self.db = FalkorDB(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password
            )
            self.graph = self.db.select_graph("KnowledgeGraph")
            
            # Test-Verbindung
            try:
                result = self.graph.query("RETURN 1 as test")
                _write_log(f"[FalkorDB-Windows] Connected to Redis at {self.redis_host}:{self.redis_port}")
            except Exception as e:
                _write_log(f"[FalkorDB-Windows] WARNING: Connection test failed: {e}")
                _write_log("[FalkorDB-Windows] Make sure Redis is running and FalkorDB module is loaded!")
                raise
                
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error initializing: {e}")
            raise
    
    def load(self):
        """Lädt den Graph (nur für Kompatibilität, Daten sind persistent)."""
        try:
            result = self.graph.query("MATCH (n) RETURN count(n) as node_count")
            if result.result_set:
                node_count = result.result_set[0][0]
                _write_log(f"[FalkorDB-Windows] Loaded graph with {node_count} nodes")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Load warning: {e}")
    
    def save_snapshot(self):
        """Speichert Snapshot (nur für Kompatibilität, Daten sind persistent)."""
        try:
            result = self.graph.query("MATCH (n) RETURN count(n) as node_count")
            edge_result = self.graph.query("MATCH ()-[r]->() RETURN count(r) as edge_count")
            
            node_count = result.result_set[0][0] if result.result_set else 0
            edge_count = edge_result.result_set[0][0] if edge_result.result_set else 0
            
            _write_log(f"[FalkorDB-Windows] [save_snapshot] Graph state: {node_count} nodes, {edge_count} edges")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] [save_snapshot] Error: {e}")
    
    def add_node(self, note: AtomicNote):
        """Fügt einen Knoten hinzu."""
        props = self._note_to_properties(note)
        cypher_props = self._props_to_cypher(props)
        
        query = f"CREATE (n:Note {cypher_props})"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB-Windows] Added node: {note.id}")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error adding node {note.id}: {e}")
            raise
    
    def add_edge(self, relation: NoteRelation):
        """Fügt eine Kante hinzu."""
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
            _write_log(f"[FalkorDB-Windows] Added edge: {relation.source_id} -> {relation.target_id} ({relation.relation_type})")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error adding edge: {e}")
            raise
    
    def update_node(self, note: AtomicNote):
        """Aktualisiert einen Knoten."""
        props = self._note_to_properties(note)
        set_clauses = []
        
        for key, value in props.items():
            if key == "id":
                continue
            if isinstance(value, str):
                escaped_value = value.replace("'", "\\'")
                set_clauses.append(f"n.{key} = '{escaped_value}'")
            elif isinstance(value, (int, float)):
                set_clauses.append(f"n.{key} = {value}")
            elif isinstance(value, bool):
                set_clauses.append(f"n.{key} = {str(value).lower()}")
            else:
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
                self.add_node(note)
            else:
                _write_log(f"[FalkorDB-Windows] Updated node: {note.id}")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error updating node {note.id}: {e}")
            raise
    
    def get_neighbors(self, node_id: str) -> List[Dict]:
        """Gibt alle Nachbarn eines Knotens zurück."""
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
            _write_log(f"[FalkorDB-Windows] Error getting neighbors for {node_id}: {e}")
            return []
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Gibt einen Knoten zurück."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) RETURN n"
        
        try:
            result = self.graph.query(query)
            if result.result_set and len(result.result_set) > 0:
                return self._cypher_node_to_dict(result.result_set[0][0])
            return None
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error getting node {node_id}: {e}")
            return None
    
    def has_node(self, node_id: str) -> bool:
        """Prüft, ob ein Knoten existiert."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) RETURN count(n) as count"
        
        try:
            result = self.graph.query(query)
            if result.result_set and len(result.result_set) > 0:
                return result.result_set[0][0] > 0
            return False
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error checking node {node_id}: {e}")
            return False
    
    def get_all_nodes(self) -> List[Dict]:
        """Gibt alle Knoten zurück."""
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
            _write_log(f"[FalkorDB-Windows] Error getting all nodes: {e}")
            return []
    
    def get_all_edges(self) -> List[Dict]:
        """Gibt alle Kanten zurück."""
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
            _write_log(f"[FalkorDB-Windows] Error getting all edges: {e}")
            return []
    
    def remove_node(self, node_id: str):
        """Entfernt einen Knoten."""
        query = f"MATCH (n:Note {{id: '{node_id}'}}) DETACH DELETE n"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB-Windows] Removed node: {node_id}")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error removing node {node_id}: {e}")
            raise
    
    def reset(self):
        """Setzt den Graph zurück."""
        query = "MATCH (n) DETACH DELETE n"
        
        try:
            self.graph.query(query)
            _write_log(f"[FalkorDB-Windows] Reset graph")
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error resetting graph: {e}")
            raise
    
    def _note_to_properties(self, note: AtomicNote) -> Dict:
        """Konvertiert AtomicNote zu Properties-Dict."""
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
        """Konvertiert Properties-Dict zu Cypher-String."""
        cypher_props = []
        
        for key, value in props.items():
            if isinstance(value, str):
                escaped_value = value.replace("'", "\\'")
                cypher_props.append(f"{key}: '{escaped_value}'")
            elif isinstance(value, (int, float)):
                cypher_props.append(f"{key}: {value}")
            elif isinstance(value, bool):
                cypher_props.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, list):
                json_value = json.dumps(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{json_value}'")
            elif isinstance(value, dict):
                json_value = json.dumps(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{json_value}'")
            elif value is None:
                cypher_props.append(f"{key}: null")
            else:
                str_value = str(value).replace("'", "\\'")
                cypher_props.append(f"{key}: '{str_value}'")
        
        return "{" + ", ".join(cypher_props) + "}"
    
    def _cypher_node_to_dict(self, cypher_node) -> Optional[Dict]:
        """Konvertiert Cypher-Node zu Dict."""
        if not cypher_node:
            return None
        
        try:
            node_dict = {}
            
            if hasattr(cypher_node, 'properties'):
                node_dict = dict(cypher_node.properties)
            elif hasattr(cypher_node, '__dict__'):
                node_dict = dict(cypher_node.__dict__)
            elif isinstance(cypher_node, dict):
                node_dict = cypher_node
            else:
                for attr in ['id', 'content', 'contextual_summary', 'keywords', 
                          'tags', 'created_at', 'type', 'metadata']:
                    if hasattr(cypher_node, attr):
                        node_dict[attr] = getattr(cypher_node, attr)
            
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
            
            if 'created_at' in node_dict and isinstance(node_dict['created_at'], str):
                try:
                    node_dict['created_at'] = datetime.fromisoformat(node_dict['created_at'])
                except:
                    pass
            
            return node_dict
        except Exception as e:
            _write_log(f"[FalkorDB-Windows] Error converting Cypher node: {e}")
            return None

