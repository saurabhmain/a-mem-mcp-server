"""
Safe Graph Store Wrapper

Ein Wrapper, der Edge Cases automatisch abfängt und sicheren Zugriff auf die DB gewährleistet.
- Automatische Validierung & Sanitization
- Edge Case Handling (leere Felder, Unicode, etc.)
- Konsistente Deserialisierung/Serialisierung
- Fehlerbehandlung & Recovery
"""
import json
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path

from .rustworkx_store import RustworkXGraphStore
from ..models.note import AtomicNote, NoteRelation


class SafeGraphStore:
    """
    Wrapper um RustworkXGraphStore, der Edge Cases automatisch abfängt.
    
    Features:
    - Automatische Validierung & Sanitization aller Daten
    - Edge Case Handling (leere Felder, Unicode, None-Werte)
    - Konsistente Deserialisierung/Serialisierung
    - Fehlerbehandlung & Recovery
    """
    
    def __init__(self, graph_store: Optional[RustworkXGraphStore] = None):
        """Initialisiert den Safe Wrapper."""
        if graph_store is None:
            self._store = RustworkXGraphStore()
        else:
            self._store = graph_store
    
    # ========== Node Operations (Safe) ==========
    
    def add_node(self, note: AtomicNote) -> str:
        """Fügt einen Node hinzu mit automatischer Validierung."""
        try:
            # Sanitize & Validate
            sanitized_note = self._sanitize_note(note)
            
            # Add via store
            self._store.add_node(sanitized_note)
            return sanitized_note.id
        except Exception as e:
            # Recovery: Try with minimal data
            try:
                minimal_note = AtomicNote(
                    content=note.content or "",
                    contextual_summary=note.contextual_summary or "",
                    keywords=note.keywords or [],
                    tags=note.tags or [],
                    metadata=note.metadata or {}
                )
                self._store.add_node(minimal_note)
                return minimal_note.id
            except Exception as e2:
                raise Exception(f"Failed to add node even with minimal data: {e2}")
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Gibt einen Node zurück mit automatischer Deserialisierung."""
        try:
            node_data = self._store.get_node(node_id)
            if node_data:
                # Ensure deserialization
                return self._deserialize_node_data(node_data)
            return None
        except Exception as e:
            # Recovery: Try direct access
            try:
                node_data = self._store.get_node(node_id)
                if node_data:
                    return self._ensure_node_data_types(node_data)
                return None
            except:
                return None
    
    def update_node(self, note: AtomicNote):
        """Aktualisiert einen Node mit automatischer Validierung."""
        try:
            # Sanitize & Validate
            sanitized_note = self._sanitize_note(note)
            self._store.update_node(sanitized_note)
        except Exception as e:
            # Recovery: Try with minimal data
            try:
                minimal_note = AtomicNote(
                    id=note.id,
                    content=note.content or "",
                    contextual_summary=note.contextual_summary or "",
                    keywords=note.keywords or [],
                    tags=note.tags or [],
                    metadata=note.metadata or {}
                )
                self._store.update_node(minimal_note)
            except Exception as e2:
                raise Exception(f"Failed to update node even with minimal data: {e2}")
    
    def remove_node(self, node_id: str):
        """Entfernt einen Node."""
        try:
            self._store.remove_node(node_id)
        except Exception as e:
            # Silently fail if node doesn't exist
            if not self._store.has_node(node_id):
                return
            raise
    
    def has_node(self, node_id: str) -> bool:
        """Prüft, ob ein Node existiert."""
        return self._store.has_node(node_id)
    
    def get_all_nodes(self) -> List[Dict]:
        """Gibt alle Nodes zurück mit automatischer Deserialisierung."""
        try:
            nodes = self._store.get_all_nodes()
            return [self._deserialize_node_data(node) for node in nodes]
        except Exception as e:
            # Recovery: Return empty list
            return []
    
    # ========== Edge Operations (Safe) ==========
    
    def add_edge(self, relation: NoteRelation):
        """Fügt eine Edge hinzu mit automatischer Validierung."""
        try:
            # Sanitize & Validate
            sanitized_relation = self._sanitize_relation(relation)
            
            # Ensure nodes exist
            if not self._store.has_node(sanitized_relation.source_id):
                raise ValueError(f"Source node {sanitized_relation.source_id} does not exist")
            if not self._store.has_node(sanitized_relation.target_id):
                raise ValueError(f"Target node {sanitized_relation.target_id} does not exist")
            
            self._store.add_edge(sanitized_relation)
        except Exception as e:
            # Recovery: Try with minimal data
            try:
                minimal_relation = NoteRelation(
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    relation_type=relation.relation_type or "relates_to",
                    weight=max(0.0, min(1.0, relation.weight or 1.0)),
                    reasoning=relation.reasoning or "",
                    created_at=relation.created_at or datetime.utcnow()
                )
                self._store.add_edge(minimal_relation)
            except Exception as e2:
                raise Exception(f"Failed to add edge even with minimal data: {e2}")
    
    def remove_edge(self, source_id: str, target_id: str):
        """Entfernt eine Edge."""
        try:
            self._store.remove_edge(source_id, target_id)
        except Exception as e:
            # Silently fail if edge doesn't exist
            if not self._store.get_edge_data(source_id, target_id):
                return
            raise
    
    def get_edge_data(self, source_id: str, target_id: str) -> Optional[Dict]:
        """Gibt Edge-Daten zurück mit automatischer Deserialisierung."""
        try:
            edge_data = self._store.get_edge_data(source_id, target_id)
            if edge_data:
                return self._deserialize_edge_data(edge_data)
            return None
        except Exception as e:
            return None
    
    def get_all_edges(self) -> List[Dict]:
        """Gibt alle Edges zurück mit automatischer Deserialisierung."""
        try:
            edges = self._store.get_all_edges()
            return [self._deserialize_edge_data(edge) for edge in edges]
        except Exception as e:
            # Recovery: Return empty list
            return []
    
    def get_neighbors(self, node_id: str) -> List[Dict]:
        """Gibt Nachbarn zurück mit automatischer Deserialisierung."""
        try:
            neighbors = self._store.get_neighbors(node_id)
            return [self._deserialize_node_data(n) for n in neighbors]
        except Exception as e:
            # Recovery: Return empty list
            return []
    
    # ========== Graph Operations ==========
    
    def save_snapshot(self):
        """Speichert den Graph."""
        try:
            self._store.save_snapshot()
        except Exception as e:
            # Recovery: Try again
            try:
                self._store.save_snapshot()
            except Exception as e2:
                raise Exception(f"Failed to save snapshot: {e2}")
    
    def load(self):
        """Lädt den Graph."""
        try:
            # Ensure we load from the correct path
            if hasattr(self._store, 'graph_path'):
                # Store might have been initialized with default path, override it
                pass
            self._store.load()
            # Ensure all nodes are deserialized after load
            self._ensure_all_nodes_deserialized()
        except Exception as e:
            # Recovery: Create new graph
            self._store._rx_graph = self._store._rx_graph.__class__()
    
    def reset(self):
        """Setzt den Graph zurück."""
        self._store.reset()
    
    @property
    def graph(self):
        """Gibt den Graph-Wrapper zurück (für NetworkX-Kompatibilität)."""
        return self._store.graph
    
    @property
    def graph_path(self) -> Path:
        """Gibt den Graph-Pfad zurück."""
        return self._store.graph_path
    
    @graph_path.setter
    def graph_path(self, path: Path):
        """Setzt den Graph-Pfad."""
        self._store.graph_path = path
    
    # ========== Sanitization & Validation ==========
    
    def _sanitize_note(self, note: AtomicNote) -> AtomicNote:
        """Sanitized & validiert einen Note."""
        # Ensure all fields are valid
        content = note.content or ""
        contextual_summary = note.contextual_summary or ""
        keywords = note.keywords if isinstance(note.keywords, list) else []
        tags = note.tags if isinstance(note.tags, list) else []
        metadata = note.metadata if isinstance(note.metadata, dict) else {}
        
        # Ensure created_at is valid
        created_at = note.created_at
        if not created_at or (isinstance(created_at, str) and created_at.lower() == 'none'):
            created_at = datetime.utcnow()
        elif isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = datetime.utcnow()
        
        # Create sanitized note
        sanitized = AtomicNote(
            id=note.id,
            content=content,
            contextual_summary=contextual_summary,
            keywords=keywords,
            tags=tags,
            metadata=metadata,
            created_at=created_at,
            type=note.type
        )
        
        return sanitized
    
    def _sanitize_relation(self, relation: NoteRelation) -> NoteRelation:
        """Sanitized & validiert eine Relation."""
        # Ensure all fields are valid
        relation_type = relation.relation_type or "relates_to"
        weight = max(0.0, min(1.0, relation.weight or 1.0))
        reasoning = relation.reasoning or ""
        
        # Ensure created_at is valid
        created_at = relation.created_at
        if not created_at or (isinstance(created_at, str) and created_at.lower() == 'none'):
            created_at = datetime.utcnow()
        elif isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = datetime.utcnow()
        
        # Create sanitized relation
        sanitized = NoteRelation(
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation_type,
            weight=weight,
            reasoning=reasoning,
            created_at=created_at
        )
        
        return sanitized
    
    def _deserialize_node_data(self, node_data: Dict) -> Dict:
        """Deserialisiert Node-Daten (JSON strings → lists/dicts)."""
        if not isinstance(node_data, dict):
            return node_data
        
        deserialized = dict(node_data)
        
        # Deserialize keywords
        if 'keywords' in deserialized:
            keywords_val = deserialized['keywords']
            if isinstance(keywords_val, str):
                if keywords_val.lower() == 'none' or keywords_val == '':
                    deserialized['keywords'] = []
                else:
                    try:
                        deserialized['keywords'] = json.loads(keywords_val)
                    except:
                        deserialized['keywords'] = []
            elif keywords_val is None:
                deserialized['keywords'] = []
        
        # Deserialize tags
        if 'tags' in deserialized:
            tags_val = deserialized['tags']
            if isinstance(tags_val, str):
                if tags_val.lower() == 'none' or tags_val == '':
                    deserialized['tags'] = []
                else:
                    try:
                        deserialized['tags'] = json.loads(tags_val)
                    except:
                        deserialized['tags'] = []
            elif tags_val is None:
                deserialized['tags'] = []
        
        # Deserialize metadata
        if 'metadata' in deserialized:
            metadata_val = deserialized['metadata']
            if isinstance(metadata_val, str):
                if metadata_val.lower() == 'none' or metadata_val == '':
                    deserialized['metadata'] = {}
                else:
                    try:
                        deserialized['metadata'] = json.loads(metadata_val)
                    except:
                        deserialized['metadata'] = {}
            elif metadata_val is None:
                deserialized['metadata'] = {}
        
        # Deserialize created_at
        if 'created_at' in deserialized:
            created_at_val = deserialized['created_at']
            if isinstance(created_at_val, str):
                if created_at_val.lower() == 'none' or created_at_val == '':
                    deserialized['created_at'] = datetime.utcnow().isoformat()
                else:
                    try:
                        # Keep as ISO string for consistency
                        datetime.fromisoformat(created_at_val)
                    except:
                        deserialized['created_at'] = datetime.utcnow().isoformat()
            elif created_at_val is None:
                deserialized['created_at'] = datetime.utcnow().isoformat()
        
        return deserialized
    
    def _deserialize_edge_data(self, edge_data: Dict) -> Dict:
        """Deserialisiert Edge-Daten."""
        if not isinstance(edge_data, dict):
            return edge_data
        
        deserialized = dict(edge_data)
        
        # Deserialize created_at
        if 'created_at' in deserialized:
            created_at_val = deserialized['created_at']
            if isinstance(created_at_val, str):
                if created_at_val.lower() == 'none' or created_at_val == '':
                    deserialized['created_at'] = datetime.utcnow().isoformat()
                else:
                    try:
                        datetime.fromisoformat(created_at_val)
                    except:
                        deserialized['created_at'] = datetime.utcnow().isoformat()
            elif created_at_val is None:
                deserialized['created_at'] = datetime.utcnow().isoformat()
        
        return deserialized
    
    def _ensure_node_data_types(self, node_data: Dict) -> Dict:
        """Stellt sicher, dass alle Node-Daten-Typen korrekt sind."""
        if not isinstance(node_data, dict):
            return {}
        
        ensured = dict(node_data)
        
        # Ensure keywords is list
        if 'keywords' not in ensured or not isinstance(ensured.get('keywords'), list):
            ensured['keywords'] = []
        
        # Ensure tags is list
        if 'tags' not in ensured or not isinstance(ensured.get('tags'), list):
            ensured['tags'] = []
        
        # Ensure metadata is dict
        if 'metadata' not in ensured or not isinstance(ensured.get('metadata'), dict):
            ensured['metadata'] = {}
        
        # Ensure created_at is valid
        if 'created_at' not in ensured or not ensured.get('created_at'):
            ensured['created_at'] = datetime.utcnow().isoformat()
        
        return ensured
    
    def _ensure_all_nodes_deserialized(self):
        """Stellt sicher, dass alle Nodes nach dem Laden deserialisiert sind."""
        try:
            # Use _deserialize_node_data from RustworkXGraphStore if available
            if hasattr(self._store, '_deserialize_node_data'):
                for idx in self._store._rx_graph.node_indices():
                    node_data = self._store._rx_graph[idx]
                    if isinstance(node_data, dict):
                        # Use store's deserialization first, then our own
                        deserialized = self._store._deserialize_node_data(node_data.copy())
                        # Also apply our deserialization for consistency
                        deserialized = self._deserialize_node_data(deserialized)
                        self._store._rx_graph[idx] = deserialized
            else:
                # Fallback: Use our own deserialization
                for idx in self._store._rx_graph.node_indices():
                    node_data = self._store._rx_graph[idx]
                    if isinstance(node_data, dict):
                        deserialized = self._deserialize_node_data(node_data.copy())
                        self._store._rx_graph[idx] = deserialized
        except Exception as e:
            # Silently fail - nodes will be deserialized on access
            pass

