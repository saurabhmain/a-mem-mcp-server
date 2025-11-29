# FalkorDB auf Windows - Setup-Anleitung

## Problem

FalkorDBLite (`falkordblite`) unterstützt Windows nicht, da es `redislite` verwendet, welches Redis mit `gcc`/`make` kompilieren muss (nur Linux/macOS).

## Lösung: Windows-Adapter mit externem Redis

A-MEM nutzt automatisch einen **Windows-Adapter**, der `falkordb-py` direkt mit einem externen Redis-Server verbindet.

## Voraussetzungen

### 1. Redis-Server mit FalkorDB-Modul

Du hast **3 Optionen**:

#### Option A: Memurai (Empfohlen für Windows)

**Memurai** ist ein nativer Windows Redis-Server, der vollständig kompatibel ist.

1. **Download**: https://www.memurai.com/get-memurai
2. **Installation**: `.msi`-Installer ausführen
3. **FalkorDB-Modul laden**: Memurai muss mit dem FalkorDB-Modul konfiguriert werden

**Konfiguration** (Memurai `memurai.conf`):
```conf
loadmodule C:\path\to\falkordb.so
```

#### Option B: Docker Redis + FalkorDB

```bash
docker run -d -p 6379:6379 --name falkordb falkordb/falkordb
```

**Vorteil**: Funktioniert sofort, keine Konfiguration nötig!

#### Option C: Normaler Redis + FalkorDB-Modul

1. Redis für Windows installieren (z.B. via WSL oder Docker)
2. FalkorDB-Modul kompilieren/laden

### 2. Python-Pakete installieren

```bash
pip install falkordb redis
```

**Wichtig**: `falkordb` (nicht `falkordblite`)!

## Konfiguration

### Environment-Variablen (optional)

Falls dein Redis-Server nicht auf `localhost:6379` läuft:

```bash
# .env oder Environment
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional, falls Redis Passwort benötigt
```

### Graph Backend aktivieren

```bash
# .env
GRAPH_BACKEND=falkordb
```

## Automatische Erkennung

A-MEM erkennt automatisch:
- ✅ **Windows** → Nutzt `FalkorDBGraphStoreWindows` (externer Redis)
- ✅ **Linux/macOS** → Nutzt `FalkorDBGraphStore` (FalkorDBLite, embedded)

## Testen

```python
from a_mem.storage.engine import create_graph_store

# Sollte automatisch Windows-Adapter verwenden
graph = create_graph_store()
print(type(graph))  # <class 'FalkorDBGraphStoreWindows'>
```

## Troubleshooting

### Fehler: "Connection refused"

**Problem**: Redis-Server läuft nicht oder ist nicht erreichbar.

**Lösung**:
```bash
# Prüfe, ob Redis läuft
redis-cli ping  # Sollte "PONG" zurückgeben

# Oder für Memurai
memurai-cli ping
```

### Fehler: "FalkorDB module not loaded"

**Problem**: Redis-Server hat das FalkorDB-Modul nicht geladen.

**Lösung**:
- **Docker**: Nutze `falkordb/falkordb` Image (hat Modul bereits geladen)
- **Memurai**: Lade Modul in `memurai.conf`: `loadmodule C:\path\to\falkordb.so`
- **Normaler Redis**: Kompiliere und lade FalkorDB-Modul

### Fehler: "falkordb module not found"

**Problem**: Python-Paket nicht installiert.

**Lösung**:
```bash
pip install falkordb redis
```

## Zusammenfassung

✅ **Windows**: `falkordb` + externer Redis (Memurai/Docker)
✅ **Linux/macOS**: `falkordblite` (embedded)

Der Adapter wechselt automatisch basierend auf der Plattform!


