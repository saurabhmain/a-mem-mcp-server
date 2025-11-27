# Embedding Dimensions - Wichtige Hinweise

## ⚠️ KRITISCH: Dimension-Kompatibilität

ChromaDB **fixiert die Embedding-Dimension** beim ersten `add()` Call. Wenn du zwischen verschiedenen Embedding-Modellen wechselst, die unterschiedliche Dimensionen haben, führt das zu **Inkompatibilitäts-Fehlern**.

## Bekannte Embedding-Dimensionen

### Ollama Models
- `nomic-embed-text:latest`: **768 Dimensionen**
- `all-minilm`: **384 Dimensionen**

### OpenRouter Models
- `openai/text-embedding-3-small`: **1536 Dimensionen**
- `openai/text-embedding-3-large`: **3072 Dimensionen**
- `qwen/qwen3-embedding-8b`: **4096 Dimensionen**
- `openai/text-embedding-ada-002`: **1536 Dimensionen**

## Problem: Dimension-Mismatch

**Szenario:**
1. Du startest mit Ollama (`nomic-embed-text` → 768 Dimensionen)
2. ChromaDB Collection wird mit 768 Dimensionen initialisiert
3. Du wechselst zu OpenRouter (`qwen3-embedding-8b` → 4096 Dimensionen)
4. ❌ **FEHLER**: ChromaDB akzeptiert keine 4096-dimensionalen Embeddings in einer 768-dimensionalen Collection

## Lösung: Collection zurücksetzen

Wenn du zwischen Embedding-Modellen wechseln willst:

```bash
# Lösche die ChromaDB Collection
rm -rf data/chroma

# Oder auf Windows:
Remove-Item -Recurse -Force data\chroma
```

**WICHTIG:** Beim Löschen von `data/chroma` gehen **alle gespeicherten Embeddings verloren**. Der Graph (`data/graph/`) bleibt erhalten, aber die Vector-Suche muss neu aufgebaut werden.

## Automatische Validierung

Das System prüft jetzt automatisch:
- ✅ Erwartete Dimension wird aus dem konfigurierten Model abgeleitet
- ✅ Bei `add()`, `query()` und `update()` wird die Dimension validiert
- ✅ Klare Fehlermeldungen mit Lösungsvorschlägen

## Best Practice

1. **Entscheide dich früh** für ein Embedding-Model
2. **Wechsel nur bei Bedarf** und lösche dann `data/chroma`
3. **Dokumentiere** welche Dimension deine Collection verwendet
4. **Backup** des Graph-Stores vor dem Wechsel (falls nötig)

## Migration zwischen Modellen

Wenn du wirklich migrieren musst:

1. **Graph exportieren** (optional, falls du die Struktur behalten willst)
2. **ChromaDB löschen**: `rm -rf data/chroma`
3. **Provider in `.env` ändern**
4. **System neu starten** - alle Notes werden neu eingebettet (Evolution läuft automatisch)



