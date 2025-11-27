# MCP Server Setup für A-MEM

## 📋 Übersicht

Der A-MEM MCP Server stellt Tools für das Agentic Memory System bereit.

## 🛠️ Verfügbare Tools

### 1. `create_atomic_note`
Speichert eine neue Information im Memory System.

**Parameter:**
- `content` (string, required): Der Text der Notiz/Erinnerung
- `source` (string, optional): Quelle der Information (Standard: "user_input")

**Beispiel:**
```json
{
  "content": "Python async/await ermöglicht nicht-blockierende I/O Operationen",
  "source": "user_input"
}
```

### 2. `retrieve_memories`
Sucht nach relevanten Erinnerungen basierend auf semantischer Ähnlichkeit.

**Parameter:**
- `query` (string, required): Die Suchanfrage
- `max_results` (integer, optional): Maximale Anzahl Ergebnisse (Standard: 5, Max: 20)

**Beispiel:**
```json
{
  "query": "Python async programming",
  "max_results": 5
}
```

### 3. `get_memory_stats`
Gibt Statistiken über das Memory System zurück.

**Parameter:** Keine

**Beispiel:**
```json
{}
```

## 🚀 Installation & Start

### 1. Dependencies installieren

```bash
pip install mcp
```

### 2. MCP Server starten

```bash
python mcp_server.py
```

Oder direkt:

```bash
python -m src.a_mem.main
```

## 📝 Cursor/IDE Konfiguration

Füge folgende Konfiguration zu deiner `mcp.json` hinzu:

```json
{
  "mcpServers": {
    "a-mem": {
      "command": "python",
      "args": [
        "C:\\Users\\tobs\\Downloads\\a-mem_-agentic-memory-system\\a-mem_-agentic-memory-system\\mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

**Wichtig:** Passe den Pfad zu deinem System an!

## 🔧 Konfiguration

Der Server nutzt die Konfiguration aus `src/a_mem/config.py`:
- **LLM:** `qwen3:4b` (Ollama)
- **Embedding:** `nomic-embed-text:latest` (Ollama)
- **Ollama URL:** `http://localhost:11434`

Stelle sicher, dass Ollama läuft und beide Modelle installiert sind:
```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text:latest
```

## 📊 Beispiel-Nutzung

### Memory erstellen:
```python
# Via MCP Tool
create_atomic_note(
    content="Python async/await Patterns",
    source="user_input"
)
```

### Memory suchen:
```python
# Via MCP Tool
retrieve_memories(
    query="Python concurrency",
    max_results=5
)
```

### Statistiken abrufen:
```python
# Via MCP Tool
get_memory_stats()
```

## ✅ Status

Der MCP Server ist vollständig implementiert und nutzt:
- ✅ Lokales Ollama (qwen3:4b für LLM, nomic-embed-text für Embeddings)
- ✅ Async I/O für Performance
- ✅ Memory Evolution im Hintergrund
- ✅ Graph-basierte Verknüpfungen



