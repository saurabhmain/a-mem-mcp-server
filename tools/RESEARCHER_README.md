# Researcher Agent

**Status:** ✅ **INTEGRIERT** - Vollständig in A-MEM System integriert

## Übersicht

Der Researcher Agent implementiert das **JIT (Just-in-Time) Research** Konzept aus dem GAM Framework:
- Bei niedriger Retrieval-Confidence wird automatisch Web-Recherche durchgeführt
- Findet relevante Informationen aus dem Web
- Erstellt neue AtomicNotes aus den Ergebnissen
- Erweitert den Knowledge Graph dynamisch

## Architektur

```
Query (low confidence)
    ↓
ResearcherAgent.research()
    ↓
1. Web Search (felo-search) → URLs + Snippets
    ↓
2. Content Extraction (jina-reader) → Full Content
    ↓
3. LLM Summarization → AtomicNotes
    ↓
4. Return Notes (ready to store)
```

## Verwendung

### Automatische Integration

Der Researcher wird **automatisch** in `MemoryController.retrieve()` ausgelöst, wenn:
- `RESEARCHER_ENABLED=true` in `.env`
- Retrieval Confidence < `RESEARCHER_CONFIDENCE_THRESHOLD` (default: 0.5)

```python
# Automatisch in retrieve():
if top_score < settings.RESEARCHER_CONFIDENCE_THRESHOLD:
    # Trigger researcher asynchronously
    asyncio.create_task(self._trigger_researcher(query, context))
```

### Manuelle Nutzung via MCP Tool

```bash
# Via MCP Tool: research_and_store
# Query: "knowledge graph systems comparison"
# Context: "Manual research request"
# Max Sources: 5 (default)
```

### Standalone Test

```bash
# Test mit echten Daten
python tools/test_research_and_store.py

# Test Researcher direkt
python tools/test_researcher_full.py "Python async web scraping"
```

## Web Search & Content Extraction

Der Researcher nutzt eine **hybride Strategie**:

### Web Search (in Prioritätsreihenfolge):
1. **MCP Tools** (wenn Callback verfügbar):
   - `felo-search`: Technische Recherche (breite Suche)
   - `duckduckgo-search`: Fallback für allgemeine Suche
2. **HTTP-basierte Tools** (Fallback):
   - `Google Search API`: Hochwertige Suchergebnisse (wenn konfiguriert)
   - `DuckDuckGo HTTP`: Allgemeine Suche (immer verfügbar)

### Content Extraction (in Prioritätsreihenfolge):
1. **MCP Tools** (wenn Callback verfügbar):
   - `jina-reader`: Content-Extraktion (hohe Qualität)
2. **HTTP-basierte Tools** (Fallback):
   - `Jina Reader HTTP`: Lokal (Docker) oder Cloud API
   - `Unstructured`: Für PDF-Extraktion (Library oder API)
   - `Readability`: Fallback für HTML-zu-Text

## Konfiguration

Alle Parameter sind in `.env` konfigurierbar:

```env
# Researcher Agent
RESEARCHER_ENABLED=true
RESEARCHER_CONFIDENCE_THRESHOLD=0.5
RESEARCHER_MAX_SOURCES=5
RESEARCHER_MAX_CONTENT_LENGTH=10000

# Google Search API (optional)
GOOGLE_SEARCH_ENABLED=true
GOOGLE_API_KEY=your_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Jina Reader (optional)
JINA_READER_ENABLED=true
JINA_READER_HOST=localhost
JINA_READER_PORT=2222

# Unstructured (optional, für PDFs)
UNSTRUCTURED_ENABLED=true
UNSTRUCTURED_USE_LIBRARY=true
# ODER
UNSTRUCTURED_API_URL=http://localhost:8000
UNSTRUCTURED_API_KEY=your_api_key
```

## Status

✅ **Fertig:**
- ResearcherAgent Klasse
- Integration in MemoryController (automatisch bei niedriger Confidence)
- MCP Tool `research_and_store` für manuelle Recherche
- HTTP-basierte Tools (Google Search API, DuckDuckGo, Jina Reader, Unstructured)
- Hybrid-Ansatz: MCP Tools (wenn verfügbar) oder HTTP-Fallbacks
- LLM-Integration für Note-Erstellung
- Metadata-Extraktion (type, keywords, tags)
- Config-Parameter in `.env`
- Event Logging (RESEARCHER_MANUAL_RUN_START, RESEARCHER_AUTO_RUN_START)
- PDF-Extraktion mit Unstructured
- Lokale Jina Reader Integration (Docker)

📋 **Geplant:**
- Caching (gleiche Query → kein erneuter Research)
- Performance-Metriken
- Rate Limiting für API Calls

## Architektur-Details

### Hybrid-Ansatz

Der Researcher Agent unterstützt zwei Modi:

1. **MCP Tool Callback** (wenn verfügbar):
   - Nutzt MCP Tools (felo-search, duckduckgo-search, jina-reader)
   - Ideal für Integration in MCP-basierte Umgebungen

2. **HTTP-Fallbacks** (Standard):
   - Google Search API (wenn konfiguriert)
   - DuckDuckGo HTTP Search
   - Jina Reader HTTP (lokal Docker oder Cloud)
   - Unstructured (Library oder API)

### Workflow

```
Query (low confidence)
    ↓
ResearcherAgent.research()
    ↓
1. Web Search (MCP Tools → HTTP Fallbacks) → URLs + Snippets
    ↓
2. Content Extraction (MCP Tools → HTTP Fallbacks) → Full Content
    ↓
3. LLM Summarization → AtomicNotes (mit Metadata)
    ↓
4. Store Notes via MemoryController.create_note()
    ↓
5. Return Notes (ready for retrieval)
```

### Integration Points

- **Automatic**: `MemoryController.retrieve()` → `_trigger_researcher()`
- **Manual**: MCP Tool `research_and_store`

