Hier ist die detaillierte `ARCHITECTURE.md` für das Projekt **A-MEM (Agentic Memory System)**.

Diese Architektur wurde entwickelt, um die Lücke zwischen statischem RAG und dynamischem Lernen zu schließen, indem sie asynchrone Verarbeitung (FastAPI Background Tasks) für die kognitiv anspruchsvollen Aufgaben der "Memory Evolution" nutzt, während die Interaktion mit dem User (MCP) schnell bleibt.

***

# ARCHITECTURE.md - A-MEM: Agentic Memory System

## 1. Projektübersicht & Design-Philosophie

A-MEM implementiert das **Zettelkasten-Prinzip für LLMs**. Es ist ein MCP-Server, der nicht nur Daten speichert, sondern diese aktiv organisiert. Das System basiert auf der Annahme, dass Wissen nicht statisch ist: Es wächst, vernetzt sich und verändert sich durch neue Informationen.

**Kern-Design-Entscheidungen:**
*   **Atomarität:** Wissen wird in kleinstmöglichen, sinnvollen Einheiten (Nodes) gespeichert.
*   **Agentic Evolution:** Das System entscheidet autonom (im Hintergrund), wie neue Informationen verknüpft oder fusioniert werden.
*   **Hybrid Retrieval:** Die Suche kombiniert Vektor-Ähnlichkeit (semantisch) mit Graph-Topologie (kontextuell).
*   **Asynchronität:** Speicheroperationen sind schnell (Fire-and-Forget), die Wissenspflege ist asynchron (Background Workers).

---

## 2. High-Level Design (Komponenten)

Das System ist in vier Schichten (Layers) unterteilt:

### Layer 1: Interface Layer (MCP Server)
*   **Technologie:** `mcp[cli]`, `FastAPI`, `SSE (Server-Sent Events)`
*   **Funktion:** Stellt die Endpunkte für den MCP-Client (z.B. Claude Desktop, IDE) bereit.
*   **Komponenten:**
    *   **MCP Router:** Definiert die Tools `create_atomic_note`, `retrieve_memories`.
    *   **Request Validator:** Pydantic Models zur Validierung eingehender Tool-Calls.

### Layer 2: Core Logic Layer (The "Brain")
*   **Technologie:** Python 3.12+, `BackgroundTasks`
*   **Funktion:** Die Geschäftslogik für die Verarbeitung und das Retrieval.
*   **Komponenten:**
    *   **Memory Controller:** Koordiniert den Schreibprozess. Nimmt die Notiz entgegen und delegiert die Hintergrundarbeit.
    *   **Evolution Worker (Async):** Ein Hintergrundprozess, der nach dem Speichern aktiv wird. Er führt `Dynamic Linking` (Kanten erstellen) und `Refinement` (Updates alter Notizen) durch.
    *   **GraphRAG Engine:** Implementiert die Suchstrategie (Vector Search -> Graph Expansion -> Reranking).

### Layer 3: Semantic Layer (LLM Integration)
*   **Technologie:** OpenAI API / Anthropic API (via Abstraktion), `instructor` oder `pydantic` für Structured Outputs.
*   **Funktion:** Wandelt unstrukturierten Text in strukturierte Daten um.
*   **Aufgaben:**
    *   Extraktion von Keywords/Tags.
    *   Entscheidung über Verknüpfungen (Link Prediction).
    *   Zusammenfassung für Kontext-Beschreibungen.

### Layer 4: Storage Layer (Hybrid Persistence)
*   **Technologie:** `ChromaDB` (Vektoren/Inhalt), `NetworkX` (Graph-Struktur), Dateisystem (Persistence).
*   **Funktion:** Persistente Speicherung des Wissensgraphen.
*   **Komponenten:**
    *   **VectorStore:** Speichert `Content`, `Embedding` und flache Metadaten (`Timestamp`, `ID`).
    *   **GraphStore:** Speichert `Node IDs` und `Edges` (Typ der Beziehung, Gewichtung).
    *   **Persistence Manager:** Sorgt dafür, dass der NetworkX-Graph regelmäßig (z.B. als `.gpickle` oder Adjacency List JSON) auf die Disk geschrieben wird.

---

## 3. Datenfluss (Data Flow)

### A. Schreib-Prozess (The "Note Taking" Loop)
Dieser Prozess ist zweigeteilt, um die Latenz für den User gering zu halten.

**Phase 1: Synchron (User wartet)**
1.  **Input:** User sendet Text via `create_atomic_note`.
2.  **Extraction:** LLM extrahiert `Keywords`, `Tags` und generiert eine `Short Description`.
3.  **Embedding:** `Sentence-Transformers` berechnet den Vektor für den Inhalt.
4.  **Persist:** Notiz wird in ChromaDB und als isolierter Knoten in NetworkX gespeichert.
5.  **Response:** User erhält Bestätigung ("Notiz ID: 123 gespeichert").

**Phase 2: Asynchron (Hintergrund - "Memory Evolution")**
1.  **Trigger:** FastAPI `BackgroundTasks` startet den `EvolutionWorker`.
2.  **Candidate Search:** Worker sucht via Vektor-DB die Top-5 ähnlichsten existierenden Notizen.
3.  **Linking Decision:** LLM vergleicht *Neue Notiz* vs. *Kandidat*:
    *   *Frage:* "Hängen diese Notizen zusammen?"
    *   *Action:* Erstelle Kante in NetworkX (z.B. `type="supports"`, `weight=0.8`).
4.  **Refinement Decision:** LLM prüft auf Redundanz:
    *   *Frage:* "Ist die neue Info ein Update der alten?"
    *   *Action:* Falls ja, markiere alte Notiz als "deprecated" oder fusioniere Inhalte (Update ChromaDB).
5.  **Graph Save:** Aktualisierter Graph wird auf Disk persistiert.

### B. Lese-Prozess (The "Retrieval" Loop)
1.  **Input:** User fragt `retrieve_memories(query="...")`.
2.  **Vector Scan:** Suche Top-K (z.B. 5) semantisch ähnliche Knoten in ChromaDB.
3.  **Graph Traversal:** Für jeden Treffer: Lade direkte Nachbarn (1-Hop) aus NetworkX, um Kontext zu erhalten.
4.  **Context Construction:** Baue einen Kontext-String aus den Treffern + Nachbarn.
5.  **Reranking (Optional):** Ein LLM sortiert die Ergebnisse nach Relevanz zur Query.
6.  **Output:** Rückgabe der strukturierten Memories an den MCP-Client.

---

## 4. Dateistruktur (File Tree)

```text
a-mem/
├── pyproject.toml              # Dependencies (mcp, fastapi, chromadb, networkx, etc.)
├── README.md
├── ARCHITECTURE.md             # Dieses Dokument
├── data/                       # Persistenter Speicher (lokal)
│   ├── chroma/                 # ChromaDB Dateien
│   └── graph/                  # Serialisierter NetworkX Graph (graph.json/gpickle)
└── src/
    └── a_mem/
        ├── __init__.py
        ├── main.py             # Entry Point (FastAPI App & MCP Server Instanz)
        ├── config.py           # Env Vars, Pfade, Konstanten
        ├── models/             # Pydantic Schemas
        │   ├── __init__.py
        │   ├── note.py         # AtomicNote Model
        │   └── api.py          # Request/Response Models für Tools
        ├── core/               # Geschäftslogik
        │   ├── __init__.py
        │   ├── memory.py       # NoteManager (CRUD)
        │   ├── evolution.py    # Background Worker (Linking logic)
        │   └── retrieval.py    # GraphRAG Suche
        ├── storage/            # Datenbank Adapter
        │   ├── __init__.py
        │   ├── vector.py       # Wrapper um ChromaDB
        │   └── graph.py        # Wrapper um NetworkX
        └── utils/
            ├── llm.py          # Interface zum LLM (OpenAI/Anthropic)
            └── text.py         # Embedding Helper
```

---

## 5. Wichtige Schnittstellen (API Definitions)

### Pydantic Models (`src/a_mem/models/note.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class AtomicNote(BaseModel):
    id: str
    content: str
    contextual_summary: str
    keywords: List[str]
    tags: List[str]
    created_at: datetime
    # Embeddings werden intern gehandhabt, nicht im API-Modell exponiert

class NoteRelation(BaseModel):
    source_id: str
    target_id: str
    relation_type: str  # z.B. "extends", "contradicts", "relates_to"
    reasoning: str      # Warum wurde dieser Link erstellt?
```

### MCP Tools Interface (`src/a_mem/main.py`)

Das System stellt folgende Tools via MCP bereit:

1.  **`create_atomic_note`**
    *   **Arguments:** `content` (str), `source` (str, optional)
    *   **Returns:** `NoteCreationResponse` (ID, Status)
    *   **Behavior:** Startet `EvolutionWorker` im Hintergrund.

2.  **`retrieve_memories`**
    *   **Arguments:** `query` (str), `max_results` (int, default=5)
    *   **Returns:** JSON Liste von Notizen inkl. verknüpfter Nachbarn.

3.  **`get_knowledge_graph_structure`** (Debugging/Visualisierung)
    *   **Arguments:** `center_node_id` (str, optional), `depth` (int, default=1)
    *   **Returns:** JSON Node-Link-Data (kompatibel mit D3.js oder ähnlichen Visualisierern).

---

## 6. Skalierbarkeit & Edge Cases

### A. Concurrency (Gleichzeitigkeit)
*   **Problem:** Da `NetworkX` in-memory arbeitet, könnten parallele `create_atomic_note` Aufrufe zu Race Conditions beim Speichern des Graphen führen.
*   **Lösung:** Implementierung eines `FileLock` Mechanismus in `src/a_mem/storage/graph.py` beim Schreiben auf die Festplatte. Für höhere Last müsste NetworkX durch eine echte Graph-DB (Neo4j) oder SQLite ersetzt werden.

### B. Token Limits & Kosten
*   **Problem:** Die "Memory Evolution" (Vergleich jeder neuen Notiz mit 5 Kandidaten) verursacht viele LLM-Calls.
*   **Lösung:**
    1.  **Optimistic Filtering:** Nur Kandidaten mit Vektor-Score > 0.7 werden für das Linking betrachtet.
    2.  **Batching:** Der Worker könnte eine Queue abarbeiten, statt sofort zu starten (in Version 2.0).
    3.  **Small Models:** Nutzung von kleineren, schnelleren Modellen (z.B. gpt-4o-mini oder lokale LLMs) für den Linking-Schritt, da dies eine einfachere Klassifizierungsaufgabe ist.

### C. Graphen-Wachstum
*   **Problem:** Wenn der Graph zu dicht wird (Supernodes), leidet die Retrieval-Qualität ("alles ist mit allem verbunden").
*   **Lösung:** Pruning-Logik im `EvolutionWorker`. Wenn eine Kante ein zu geringes Gewicht hat oder zu alt ist, wird sie entfernt.

### D. Session Persistenz
*   Da IDE-Sessions (z.B. Cursor/Windsurf) enden, muss beim Start des MCP-Servers (`main.py` Startup Event) der Graph und die ChromaDB-Verbindung neu geladen werden. Ein "Graceful Shutdown" Hook stellt sicher, dass der In-Memory Graph beim Beenden gespeichert wird.