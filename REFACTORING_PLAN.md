# Refactoring Plan: A-MEM in modulare Struktur

## Aktueller Zustand
- ❌ Alles in `src/main.py` (610 Zeilen)
- ❌ Kommentare beschreiben modulare Struktur, die nicht existiert
- ❌ Imports würden fehlschlagen (`from .core.logic import ...`)

## Ziel-Struktur

```
src/
├── a_mem/
│   ├── __init__.py
│   ├── config.py              # Config-Klasse
│   ├── models/
│   │   ├── __init__.py
│   │   └── note.py            # AtomicNote, NoteInput, NoteRelation, SearchResult
│   ├── storage/
│   │   ├── __init__.py
│   │   └── engine.py          # GraphStore, VectorStore, StorageManager
│   ├── utils/
│   │   ├── __init__.py
│   │   └── llm.py             # LLMService
│   ├── core/
│   │   ├── __init__.py
│   │   └── logic.py           # MemoryController
│   └── main.py                # MCP Server Entry Point
└── main.py                    # Legacy (kann entfernt werden)
```

## Refactoring-Schritte

1. ✅ Verzeichnisstruktur erstellen
2. ✅ Code aus main.py in Module aufteilen
3. ✅ Imports korrigieren
4. ✅ Tests anpassen
5. ✅ Dokumentation aktualisieren

## Vorteile

- ✅ Wartbarkeit: Jedes Modul hat eine klare Verantwortung
- ✅ Testbarkeit: Module können einzeln getestet werden
- ✅ Wiederverwendbarkeit: Module können in anderen Projekten genutzt werden
- ✅ Klarheit: Struktur entspricht der Dokumentation



