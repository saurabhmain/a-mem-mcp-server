# Migration-Plan: NetworkX → FalkorDBLite

## 🎯 Ziel
Ersetze NetworkX durch FalkorDBLite für:
- ✅ Persistente Graph-Datenbank auf Platte
- ✅ Bessere Performance (GraphBLAS, sparse matrices)
- ✅ Native Disk-Persistenz (kein JSON-Load/Save mehr)
- ✅ LLM-optimiert für Knowledge Graphs

---

## 📊 Aktuelle Architektur

### GraphStore Interface (NetworkX)
```python
class GraphStore:
    def __init__(self)                    # Lädt Graph von JSON
    def load(self)                        # Lädt von Disk (JSON)
    def save_snapshot(self)               # Speichert auf Disk (JSON)
    def add_node(self, note: AtomicNote)   # Fügt Node hinzu (In-Memory)
    def add_edge(self, relation: NoteRelation)  # Fügt Edge hinzu (In-Memory)
    def update_node(self, note: AtomicNote)      # Aktualisiert Node
    def get_neighbors(self, node_id: str) -> List[Dict]  # Holt Nachbarn
    def remove_node(self, node_id: str)    # Entfernt Node
    def reset(self)                        # Resettet Graph
```

### Direkte Zugriffe auf `graph.graph` (NetworkX DiGraph)
- `enzymes.py`: Direkte Graph-Operationen für Memory Enzymes
- `logic.py`: Graph-Traversal für Relation-Suche
- `engine.py`: StorageManager nutzt `graph.graph.nodes.get()`

---

## 🔄 Migrations-Strategie

### Phase 1: Abstraktionsebene (Backward Compatible)
**Ziel:** GraphStore-Interface erweitern, direkte Zugriffe abstrahieren

1. **GraphStore Interface erweitern:**
   - `get_node(node_id: str) -> Optional[Dict]` - Ersetzt `graph.graph.nodes.get()`
   - `get_all_nodes() -> List[Dict]` - Für Enzyme-Operationen
   - `get_all_edges() -> List[Dict]` - Für Enzyme-Operationen
   - `has_node(node_id: str) -> bool` - Ersetzt `node_id in graph.graph`
   - `get_edge_data(source, target) -> Optional[Dict]` - Für Edge-Properties

2. **Adapter-Pattern:**
   - `GraphStore` wird zur abstrakten Basis-Klasse
   - `NetworkXGraphStore` (aktuell) und `FalkorDBGraphStore` (neu) implementieren Interface
   - Factory-Pattern für Backend-Auswahl

### Phase 2: FalkorDBLite Adapter (Proof-of-Concept)
**Ziel:** Vollständiger Adapter mit gleichem Interface

1. **FalkorDBLite Integration:**
   - Cypher-Queries für alle Operationen
   - Property-Mapping (AtomicNote → Cypher Properties)
   - Edge-Properties (relation_type, reasoning, weight, created_at)

2. **Persistenz:**
   - FalkorDBLite speichert automatisch auf Platte
   - Kein `save_snapshot()` mehr nötig (oder als No-Op)
   - `load()` wird zu DB-Initialisierung

### Phase 3: Code-Migration
**Ziel:** Alle direkten `graph.graph` Zugriffe ersetzen

1. **enzymes.py:**
   - `graph.graph.remove_node()` → `graph.remove_node()`
   - `graph.graph.add_edge()` → `graph.add_edge()`
   - `graph.graph.nodes` → `graph.get_all_nodes()`
   - `graph.graph.edges` → `graph.get_all_edges()`

2. **logic.py:**
   - `graph.graph.nodes.get()` → `graph.get_node()`
   - Graph-Traversal via Cypher-Queries

3. **engine.py:**
   - `graph.graph.nodes.get()` → `graph.get_node()`

### Phase 4: Testing & Validation
**Ziel:** Vollständige Funktionalität sicherstellen

1. **Unit Tests:**
   - Alle GraphStore-Methoden testen
   - Edge-Cases (leere Graphen, große Graphen, etc.)

2. **Integration Tests:**
   - Memory Enzymes mit FalkorDBLite
   - Researcher Agent Integration
   - MCP Tools Funktionalität

3. **Performance Tests:**
   - Vergleich NetworkX vs FalkorDBLite
   - Load/Save Performance
   - Query Performance

### Phase 5: Production Rollout
**Ziel:** FalkorDBLite als Standard

1. **Feature Flag:**
   - `.env` Variable: `GRAPH_BACKEND=networkx|falkordb`
   - Standard: `falkordb` (neue Installationen)
   - Migration-Tool für bestehende Daten

2. **Data Migration:**
   - Tool zum Exportieren von NetworkX JSON → FalkorDBLite
   - Validierung der migrierten Daten

---

## 🛠️ Implementierungs-Details

### FalkorDBLite Adapter Interface

```python
class FalkorDBGraphStore:
    def __init__(self):
        self.db = FalkorDB(path=str(settings.GRAPH_PATH.parent / "falkordb"))
        self.graph = self.db.select_graph("KnowledgeGraph")
        # Kein load() nötig - DB lädt automatisch
    
    def add_node(self, note: AtomicNote):
        # Cypher: CREATE (n:Note {properties})
        props = self._note_to_properties(note)
        query = f"CREATE (n:Note {self._props_to_cypher(props)})"
        self.graph.query(query)
    
    def add_edge(self, relation: NoteRelation):
        # Cypher: MATCH (a), (b) CREATE (a)-[r:REL_TYPE]->(b)
        query = f"""
        MATCH (a:Note {{id: '{relation.source_id}'}}),
              (b:Note {{id: '{relation.target_id}'}})
        CREATE (a)-[r:{relation.relation_type} {{
            reasoning: '{relation.reasoning}',
            weight: {relation.weight},
            created_at: '{relation.created_at.isoformat()}'
        }}]->(b)
        """
        self.graph.query(query)
    
    def get_neighbors(self, node_id: str) -> List[Dict]:
        query = f"""
        MATCH (n:Note {{id: '{node_id'}})-[r]->(m:Note)
        RETURN m
        """
        result = self.graph.query(query)
        return [self._cypher_node_to_dict(row[0]) for row in result.result_set]
```

### Property Mapping

```python
def _note_to_properties(self, note: AtomicNote) -> Dict:
    """Konvertiert AtomicNote zu Cypher Properties."""
    return {
        "id": note.id,
        "content": note.content,
        "contextual_summary": note.contextual_summary,
        "keywords": json.dumps(note.keywords),  # Array als JSON-String
        "tags": json.dumps(note.tags),
        "created_at": note.created_at.isoformat(),
        "type": note.type or "",
        "metadata": json.dumps(note.metadata)
    }
```

### Edge Properties

```python
def _relation_to_edge_properties(self, relation: NoteRelation) -> Dict:
    """Konvertiert NoteRelation zu Edge Properties."""
    return {
        "type": relation.relation_type,
        "reasoning": relation.reasoning or "",
        "weight": relation.weight,
        "created_at": relation.created_at.isoformat()
    }
```

---

## 📋 Migration-Checkliste

### Phase 1: Abstraktion
- [ ] GraphStore Interface erweitern (get_node, get_all_nodes, etc.)
- [ ] NetworkXGraphStore refactoren (neue Methoden hinzufügen)
- [ ] Alle direkten `graph.graph` Zugriffe in enzymes.py ersetzen
- [ ] Alle direkten `graph.graph` Zugriffe in logic.py ersetzen
- [ ] Tests für neue Interface-Methoden

### Phase 2: FalkorDBLite Adapter
- [ ] FalkorDBLite installieren (`pip install falkordblite`)
- [ ] FalkorDBGraphStore Klasse implementieren
- [ ] Alle GraphStore-Methoden implementieren
- [ ] Property-Mapping (AtomicNote → Cypher)
- [ ] Edge-Properties Mapping
- [ ] Unit Tests für FalkorDBGraphStore

### Phase 3: Code-Migration
- [ ] enzymes.py: Alle Graph-Operationen über Interface
- [ ] logic.py: Alle Graph-Operationen über Interface
- [ ] engine.py: StorageManager über Interface
- [ ] Integration Tests

### Phase 4: Testing
- [ ] Unit Tests (alle Methoden)
- [ ] Integration Tests (Memory Enzymes, Researcher Agent)
- [ ] Performance Tests (NetworkX vs FalkorDBLite)
- [ ] Edge-Case Tests (leere Graphen, große Graphen)

### Phase 5: Production
- [ ] Feature Flag (GRAPH_BACKEND)
- [ ] Migration-Tool (NetworkX → FalkorDBLite)
- [ ] Dokumentation aktualisieren
- [ ] README aktualisieren

---

## ⚠️ Risiken & Mitigation

### Risiko 0: Python-Version
**Problem:** FalkorDBLite benötigt Python 3.12+
**Mitigation:** 
- Python-Upgrade auf 3.12+ erforderlich
- Oder: Alternative Graph-DB verwenden (CogDB, SQLite Graph Extension)
- Oder: Bei Python < 3.12: NetworkX beibehalten

### Risiko 1: Performance-Einbußen
**Mitigation:** Performance-Tests vor Rollout, Fallback auf NetworkX möglich

### Risiko 2: Datenverlust bei Migration
**Mitigation:** Backup vor Migration, Validierung der migrierten Daten

### Risiko 3: Cypher-Query-Fehler
**Mitigation:** Umfassende Tests, Error-Handling, Fallback-Mechanismen

### Risiko 4: Kompatibilität mit bestehenden Daten
**Mitigation:** Migration-Tool mit Validierung, Rollback-Mechanismus

---

## 📈 Erwartete Vorteile

1. **Performance:**
   - Schnellere Queries (GraphBLAS, sparse matrices)
   - Kein JSON-Load/Save Overhead
   - Native Disk-Persistenz

2. **Skalierbarkeit:**
   - Bessere Performance bei großen Graphen
   - Optimiert für analytische Workloads

3. **LLM-Optimierung:**
   - Speziell für Knowledge Graphs entwickelt
   - Cypher-Query-Sprache für komplexe Queries

---

## 🔗 Referenzen

- [FalkorDBLite PyPI](https://pypi.org/project/falkordblite/)
- [FalkorDB Documentation](https://docs.falkordb.com/)
- [Cypher Query Language](https://opencypher.org/)

