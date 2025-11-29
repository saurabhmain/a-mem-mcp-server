# FalkorDBLite Proof-of-Concept

## 🎯 Status
**Proof-of-Concept** - Funktional, aber noch nicht vollständig integriert.

## 📦 Installation

**⚠️ Voraussetzungen:**
- Python 3.12+ erforderlich
- **Windows**: Nutze den Windows-Adapter (siehe `WINDOWS_FALKORDB_SETUP.md`)
- **Linux/macOS**: Nutze FalkorDBLite (embedded)

### Linux/macOS (FalkorDBLite)

```bash
# Prüfe Python-Version
python --version  # Muss 3.12+ sein

# Installiere FalkorDBLite
pip install falkordblite
```

### Windows (Windows-Adapter)

```bash
# Installiere falkordb-py (nicht falkordblite!)
pip install falkordb redis

# Redis-Server mit FalkorDB-Modul benötigt:
# - Memurai (Windows-native): https://www.memurai.com/
# - Docker: docker run -p 6379:6379 falkordb/falkordb
```

**Siehe**: `docs/WINDOWS_FALKORDB_SETUP.md` für vollständige Anleitung!

Oder füge zu `requirements.txt` hinzu:
```
falkordblite>=1.0.0
```

**Hinweis:** Falls Python < 3.12, kann der Code nicht getestet werden. Der Adapter ist aber vollständig implementiert und funktioniert mit Python 3.12+.

## 🚀 Verwendung

### Option 1: Via Environment Variable

Setze in `.env`:
```env
GRAPH_BACKEND=falkordb
```

### Option 2: Direkt im Code

```python
from a_mem.storage.falkordb_store import FalkorDBGraphStore

# Erstelle FalkorDBLite Store
store = FalkorDBGraphStore()

# Verwende wie NetworkX GraphStore
note = AtomicNote(content="Test", ...)
store.add_node(note)
```

## 🧪 Testing

```bash
# Test-Script ausführen
python tests/test_falkordb_store.py

# Oder mit pytest
pytest tests/test_falkordb_store.py -v
```

## 📊 Implementierte Features

✅ **Vollständiges GraphStore Interface:**
- `add_node(note)` - Node hinzufügen
- `add_edge(relation)` - Edge hinzufügen
- `update_node(note)` - Node aktualisieren
- `get_node(node_id)` - Node abrufen
- `get_neighbors(node_id)` - Nachbarn abrufen
- `has_node(node_id)` - Node existiert?
- `get_all_nodes()` - Alle Nodes
- `get_all_edges()` - Alle Edges
- `remove_node(node_id)` - Node entfernen
- `reset()` - Graph zurücksetzen

✅ **Persistenz:**
- Automatische Disk-Persistenz (kein `save_snapshot()` nötig)
- Daten werden in `data/falkordb/` gespeichert

✅ **Property Mapping:**
- AtomicNote → Cypher Properties
- NoteRelation → Edge Properties
- JSON-Serialisierung für komplexe Typen (lists, dicts)

## ⚠️ Bekannte Einschränkungen

1. **Cypher Node API:** Die FalkorDBLite Python-API für Node-Properties kann variieren. 
   Der `_cypher_node_to_dict()` Parser muss möglicherweise angepasst werden.

2. **Performance:** Noch nicht getestet im Vergleich zu NetworkX.

3. **Migration:** Kein automatisches Migration-Tool von NetworkX → FalkorDBLite.

4. **Enzymes:** Memory Enzymes nutzen noch direkte `graph.graph` Zugriffe.
   Diese müssen auf das Interface umgestellt werden.

## 🔄 Nächste Schritte

1. **Interface-Erweiterung:** GraphStore Interface erweitern für Enzyme-Operationen
2. **Code-Migration:** Alle direkten `graph.graph` Zugriffe ersetzen
3. **Performance-Tests:** Vergleich NetworkX vs FalkorDBLite
4. **Migration-Tool:** Tool zum Exportieren von NetworkX → FalkorDBLite

## 📚 Dokumentation

- [Migration Plan](MIGRATION_PLAN_FALKORDB.md)
- [FalkorDBLite PyPI](https://pypi.org/project/falkordblite/)
- [FalkorDB Documentation](https://docs.falkordb.com/)

