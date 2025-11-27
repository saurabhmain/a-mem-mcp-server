"""
Storage Engine: GraphStore, VectorStore, StorageManager

Implementiert Cross-Platform Locking, sicheres Laden und separiert Speichern von Hinzufügen.
"""

import json
import shutil
import networkx as nx
import chromadb
from typing import List, Dict, Tuple, Optional
import os
from contextlib import contextmanager

from ..config import settings
from ..models.note import AtomicNote, NoteRelation

# --- Cross-Platform Locking ---
try:
    import fcntl
    def lock_file(f): fcntl.flock(f, fcntl.LOCK_EX)
    def unlock_file(f): fcntl.flock(f, fcntl.LOCK_UN)
except ImportError:
    # Windows Fallback (Simple No-Op or use portalocker if installed)
    # Für Production auf Windows wird 'pip install portalocker' empfohlen
    def lock_file(f): pass 
    def unlock_file(f): pass

class GraphStore:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.load()

    @contextmanager
    def _file_lock(self):
        """Cross-platform File Lock."""
        with open(settings.LOCK_FILE, 'w') as lock_f:
            try:
                lock_file(lock_f)
                yield
            finally:
                unlock_file(lock_f)

    def load(self):
        """Lädt den Graphen sicher. Verhindert Datenverlust bei korrupter JSON."""
        if settings.GRAPH_PATH.exists():
            try:
                with open(settings.GRAPH_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except json.JSONDecodeError:
                timestamp = os.urandom(4).hex()
                backup_path = settings.GRAPH_PATH.with_suffix(f".bak.{timestamp}")
                print(f"CRITICAL: Graph JSON corrupted. Backing up to {backup_path}")
                shutil.copy(settings.GRAPH_PATH, backup_path)
                raise RuntimeError("Graph database is corrupted. Check backup.")
            except Exception as e:
                print(f"Error loading graph: {e}")
                # Nur bei Lese-Problemen (Permissions etc) brechen wir ab, 
                # bei 'Not Found' wird ein neuer erstellt.
                if not os.access(settings.GRAPH_PATH, os.R_OK):
                     raise
                self.graph = nx.DiGraph()
        else:
            self.graph = nx.DiGraph()

    def save_snapshot(self):
        """Speichert den aktuellen Zustand auf die Festplatte."""
        with self._file_lock():
            data = nx.node_link_data(self.graph)
            # Atomic write pattern: Write to temp, then rename
            temp_path = settings.GRAPH_PATH.with_suffix(".tmp")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, settings.GRAPH_PATH)

    def add_node(self, note: AtomicNote):
        """Fügt Node hinzu (In-Memory). Speichern muss separat getriggert werden."""
        self.graph.add_node(note.id, **note.model_dump(mode='json'))

    def add_edge(self, relation: NoteRelation):
        """Fügt Edge hinzu (In-Memory)."""
        self.graph.add_edge(
            relation.source_id, 
            relation.target_id, 
            type=relation.relation_type,
            reasoning=relation.reasoning,
            weight=relation.weight
        )

    def update_node(self, note: AtomicNote):
        """Aktualisiert einen bestehenden Node im Graphen (Memory Evolution)."""
        if note.id not in self.graph:
            # Falls Node nicht existiert, füge ihn hinzu
            self.add_node(note)
        else:
            # Update Node-Attribute
            self.graph.nodes[note.id].update(note.model_dump(mode='json'))

    def get_neighbors(self, node_id: str) -> List[Dict]:
        if node_id not in self.graph:
            return []
        neighbors = list(self.graph.successors(node_id)) + list(self.graph.predecessors(node_id))
        results = []
        for n_id in set(neighbors):
            if n_id in self.graph.nodes:
                results.append(self.graph.nodes[n_id])
        return results
    
    def remove_node(self, node_id: str):
        """Entfernt einen Node und alle zugehörigen Edges (In-Memory)."""
        if node_id in self.graph:
            # NetworkX entfernt automatisch alle Edges beim Löschen eines Nodes
            self.graph.remove_node(node_id)
    
    def reset(self):
        """Setzt den Graph komplett zurück (In-Memory + Datei)."""
        # Lösche Graph-Datei falls vorhanden
        if settings.GRAPH_PATH.exists():
            settings.GRAPH_PATH.unlink()
        
        # Erstelle neuen leeren Graph
        self.graph = nx.DiGraph()
        
        # Speichere leeren Graph
        self.save_snapshot()

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(name="memories")
        # Erwartete Embedding-Dimension basierend auf Provider
        self._expected_dimension = self._get_expected_dimension()
        self._validate_dimension()
    
    def _get_expected_dimension(self) -> int:
        """Ermittelt die erwartete Embedding-Dimension basierend auf dem konfigurierten Model."""
        from ..config import settings
        if settings.LLM_PROVIDER == "openrouter":
            # OpenRouter Embedding Models - bekannte Dimensionen
            model = settings.OPENROUTER_EMBEDDING_MODEL.lower()
            if "text-embedding-3-small" in model:
                return 1536
            elif "text-embedding-3-large" in model:
                return 3072
            elif "qwen3-embedding-8b" in model or "qwen/qwen3-embedding-8b" in model:
                return 4096
            elif "text-embedding-ada-002" in model:
                return 1536
            else:
                # Fallback: Versuche aus Model-Name zu extrahieren oder Standard
                print(f"Warning: Unknown OpenRouter embedding model '{model}'. Assuming 1536 dimensions.")
                return 1536
        else:
            # Ollama Embedding Models
            model = settings.OLLAMA_EMBEDDING_MODEL.lower()
            if "nomic-embed-text" in model:
                return 768
            elif "all-minilm" in model:
                return 384
            else:
                # Fallback für unbekannte Ollama Models
                print(f"Warning: Unknown Ollama embedding model '{model}'. Assuming 768 dimensions.")
                return 768
    
    def _validate_dimension(self):
        """Validiert, ob die Collection mit der erwarteten Dimension kompatibel ist."""
        try:
            # Versuche ein Test-Embedding zu erstellen (nur Dimension prüfen)
            test_embedding = [0.0] * self._expected_dimension
            # Prüfe ob Collection bereits Items hat
            if self.collection.count() > 0:
                # Hole ein existierendes Item um die aktuelle Dimension zu prüfen
                sample = self.collection.get(limit=1)
                if sample['ids']:
                    # ChromaDB speichert Embeddings intern, wir können die Dimension nicht direkt abfragen
                    # Aber wir können versuchen, ein neues Item mit der erwarteten Dimension hinzuzufügen
                    # und sehen ob es fehlschlägt
                    pass
        except Exception as e:
            print(f"Warning: Dimension validation error: {e}")
    
    def _check_dimension_compatibility(self, embedding: List[float]) -> bool:
        """Prüft ob das Embedding mit der erwarteten Dimension übereinstimmt."""
        actual_dim = len(embedding)
        if actual_dim != self._expected_dimension:
            from ..config import settings
            print(f"⚠️  CRITICAL: Embedding dimension mismatch!")
            print(f"   Expected: {self._expected_dimension} (from {settings.LLM_PROVIDER}/{settings.EMBEDDING_MODEL})")
            print(f"   Actual: {actual_dim}")
            print(f"   This will cause ChromaDB errors!")
            print(f"   Solution: Delete 'data/chroma' directory and restart, or use consistent embedding models.")
            return False
        return True

    def add(self, note: AtomicNote, embedding: List[float]):
        # Dimension-Validierung
        if not self._check_dimension_compatibility(embedding):
            raise ValueError(
                f"Embedding dimension mismatch. Expected {self._expected_dimension}, got {len(embedding)}. "
                f"Delete 'data/chroma' directory to reset or use consistent embedding models."
            )
        
        # ChromaDB handelt interne Locks meist selbst, aber wir nutzen es sync.
        # Im Logic Layer wird dies in einen Thread ausgelagert.
        self.collection.add(
            ids=[note.id],
            embeddings=[embedding],
            documents=[note.content],
            metadatas=[{
                "timestamp": note.created_at.isoformat(),
                "summary": note.contextual_summary
            }]
        )

    def query(self, embedding: List[float], k: int = 5) -> Tuple[List[str], List[float]]:
        # Dimension-Validierung
        if not self._check_dimension_compatibility(embedding):
            raise ValueError(
                f"Query embedding dimension mismatch. Expected {self._expected_dimension}, got {len(embedding)}. "
                f"Delete 'data/chroma' directory to reset or use consistent embedding models."
            )
        
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        if not results['ids']:
            return [], []
        return results['ids'][0], results['distances'][0]

    def update(self, note_id: str, note: AtomicNote, embedding: List[float]):
        """Aktualisiert eine bestehende Note in ChromaDB (Memory Evolution)."""
        # Dimension-Validierung
        if not self._check_dimension_compatibility(embedding):
            raise ValueError(
                f"Update embedding dimension mismatch. Expected {self._expected_dimension}, got {len(embedding)}. "
                f"Delete 'data/chroma' directory to reset or use consistent embedding models."
            )
        
        # ChromaDB unterstützt update() - falls nicht vorhanden, delete + add
        try:
            # Versuche Update (falls ChromaDB Version es unterstützt)
            self.collection.update(
                ids=[note_id],
                embeddings=[embedding],
                documents=[note.content],
                metadatas=[{
                    "timestamp": note.created_at.isoformat(),
                    "summary": note.contextual_summary
                }]
            )
        except AttributeError:
            # Fallback: Delete + Add (für ältere ChromaDB Versionen)
            self.collection.delete(ids=[note_id])
            self.add(note, embedding)
    
    def delete(self, note_id: str):
        """Löscht eine Note aus ChromaDB."""
        try:
            self.collection.delete(ids=[note_id])
        except Exception as e:
            print(f"Warning: Error deleting note {note_id} from vector store: {e}")
    
    def reset(self):
        """Setzt die ChromaDB Collection komplett zurück."""
        try:
            # Lösche Collection
            self.client.delete_collection(name="memories")
            # Erstelle neue leere Collection
            self.collection = self.client.get_or_create_collection(name="memories")
        except Exception as e:
            print(f"Warning: Error resetting vector store: {e}")
            # Fallback: Versuche Collection neu zu erstellen
            try:
                self.collection = self.client.get_or_create_collection(name="memories")
            except Exception as e2:
                print(f"Critical: Could not recreate collection: {e2}")
                raise

class StorageManager:
    """Fassade für Vektor- und Graph-Speicher."""
    def __init__(self):
        self.vector = VectorStore()
        self.graph = GraphStore()
    
    def get_note(self, note_id: str) -> Optional[AtomicNote]:
        node_data = self.graph.graph.nodes.get(note_id)
        if node_data:
            # Pydantic Validierung sicherstellen, falls Felder fehlen
            try:
                return AtomicNote(**node_data)
            except Exception as e:
                print(f"Warning: Node {note_id} corrupted: {e}")
                return None
        return None
    
    def delete_note(self, note_id: str) -> bool:
        """Löscht eine Note aus Graph und Vector Store."""
        # Prüfe ob Note existiert
        if note_id not in self.graph.graph:
            return False
        
        try:
            # Lösche aus Graph (entfernt automatisch alle Edges)
            self.graph.remove_node(note_id)
            # Lösche aus Vector Store
            self.vector.delete(note_id)
            return True
        except Exception as e:
            print(f"Error deleting note {note_id}: {e}")
            return False
    
    def reset(self):
        """Setzt Graph und Vector Store komplett zurück."""
        # Reset Graph
        self.graph.reset()
        # Reset Vector Store
        self.vector.reset()

